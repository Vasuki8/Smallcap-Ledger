"""Discover official reports from the same public endpoints as AMC websites."""
import calendar
import json
import re
from datetime import date,datetime
from urllib.parse import urljoin,quote,unquote
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from . import db,providers,disclosures,amc_reports


def read(url,body=None):
    providers.can_crawl(url)
    return providers.fetch(url,body=body,max_bytes=60*1024*1024)


def months(today=None,count=3):
    today=today or date.today()
    for offset in range(count):
        y,m=divmod(today.year*12+today.month-1-offset,12)
        yield y,m+1,calendar.month_name[m+1]


def store_report(amc,family,url,title='Official report'):
    url=quote(url,safe=':/?&=%#+')
    if not disclosures.official_publication_url(url,amc):raise ValueError('Unregistered AMC report host')
    body,h,typ=read(url)
    if amc=='Samco':
        print('Samco portfolio response: '+str(typ)+' · '+str(len(body))+' bytes · '+repr(body[:24]),flush=True)
        if not body.startswith((b'PK',b'\\xd0\\xcf',b'%PDF')):
            print('Samco portfolio response preview: '+body[:400].decode('utf-8',errors='replace').replace('\\n',' ')[:400],flush=True)
    kind=providers.classify(title,url)
    did=providers.save_document(family,title,url,kind,'Fund',origin='AMC');providers.doc_version(did,h)
    return amc_reports.extract(body,family,url,h)


def discover(amc):
    """Yield (family, URL, label); parsers independently verify scheme ownership."""
    if amc=='Bank of India':
        body={'pagno':0,'category':None,'fromDate':None,'toDate':None,'LibraryName':'InvestorCorner','folderName':'FACTSHEETS','CategoryValue':'no'}
        raw,_,_=read('https://www.boimf.in/AjaxService.asmx/GetDocuments',body)
        rows=json.loads(json.loads(raw)['d'])['Documents']
        for row in rows[:3]:yield 'Bank Of India Small Cap Fund',row['FolderUrl'],row['DocName']
    elif amc=='UTI':
        for year,month,name in months():
            raw,_,_=read(f'https://www.utimf.com/api/get-fact-sheet?year={year}&month={name}')
            rows=json.loads(raw).get('rows',[])
            active=[r for r in rows if 'active' in r.get('name','').lower() and 'passive' not in r['name'].lower() and 'hindi' not in r['name'].lower()]
            if active:yield 'UTI Small Cap Fund',active[0]['url'],active[0]['name']
            raw,_,_=read(f'https://www.utimf.com/api/get-consolidate-portfolio-disclosure?year={year}&month={name}')
            for row in json.loads(raw).get('rows',[])[:1]:
                if row.get('type','').lower()=='zip':yield 'UTI Small Cap Fund',row['url'],row['name']
    elif amc=='Bandhan':
        family='Bandhan Small Cap Fund'
        root='https://cmsnew.bandhanmutual.com'
        pages=[
            root+'/monthly-factsheets-2026/',
            root+'/bandhan-small-cap-fund/',
            root+'/monthly-and-half-yearly-bandhan-small-cap-fund-31-august-2026/',
        ]
        seen=set()
        for page in pages:
            raw,_,_=read(page)
            soup=BeautifulSoup(raw,'html.parser')
            for url,title in providers.candidate_links(soup,page).items():
                if url in seen or not re.search(r'\.(?:pdf|xlsx?|xml)(?:[?#]|$)',url,re.I):continue
                if not disclosures.official_publication_url(url,amc):continue
                seen.add(url)
                yield family,url,title or 'Bandhan official report'
    elif amc=='Samco':
        family='Samco Small Cap Fund'
        page='https://www.samcomf.com/StatutoryDisclosure'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        candidates={}
        # Preserve nearby table/list context because Samco labels the action links
        # simply XML / Excel / PDF while the row heading carries the scheme name.
        for a in soup.select('a[href]'):
            url=urljoin(page,a.get('href',''))
            container=a.find_parent(['tr','li']) or a.parent
            context=(container.get_text(' ',strip=True) if container else a.get_text(' ',strip=True))[:1200]
            candidates[url]=context or a.get_text(' ',strip=True) or url.rsplit('/',1)[-1]
        for url,title in providers.candidate_links(soup,page).items():
            candidates.setdefault(url,title)
        rows=[]
        for url,title in candidates.items():
            combined=unquote(url+' '+title)
            if not disclosures.official_publication_url(url,amc):continue
            if not re.search(r'samco[\s_%-]*small[\s_%-]*cap[\s_%-]*fund|small[\s_%-]*cap[\s_%-]*fund',combined,re.I):continue
            if not re.search(r'monthly[\s_%-]*portfolio|portfolio',combined,re.I):continue
            ext=re.search(r'\.(xlsx?|xml|pdf)(?:[?#]|$)',url,re.I)
            if not ext:continue
            years=[int(x) for x in re.findall(r'20[12]\d',combined)]
            year=max(years,default=0)
            month=max((i for i in range(1,13) if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
            kind=ext.group(1).lower();priority=3 if kind in ('xls','xlsx') else 2 if kind=='xml' else 1
            rows.append((year,month,priority,url,title))
        if not rows:raise ValueError('No official Samco Small Cap monthly portfolio file was exposed by the statutory disclosure page')
        newest=max((y,m) for y,m,_,_,_ in rows)
        newest_rows=[r for r in rows if (r[0],r[1])==newest]
        # Prefer the structured Excel copy. If absent, keep one official fallback.
        chosen=max(newest_rows,key=lambda r:r[2])
        print('Samco selected monthly portfolio: '+chosen[3],flush=True)
        yield family,chosen[3],chosen[4] or 'Samco Small Cap monthly portfolio'

    elif amc=='TRUST':
        url='https://www.trustmf.com/api/api/Trust/GetData'
        body={'systemQueryFileName':'productsweb.xml','tagName':'GetOneProductWeb','searchField':'p.slug','searchValue':'trustmf-small-cap-fund','sortField':'','sortDirection':''}
        raw,h,_=read(url,body)
        rows=json.loads(raw).get('resultSetArray',[])
        row=next((r for r in rows if r.get('slug')=='trustmf-small-cap-fund' and disclosures.same_fund_title(r.get('title',''),'Trustmf Small Cap Fund')),None)
        if row:
            # US-format timestamp is the field format used by this public API.
            day=datetime.strptime(row['aumasondate'],'%m/%d/%Y %I:%M:%S %p').date()
            value=providers.number(row['monthendaum'])
            if day<=date.today() and 0<value<10_000_000:
                page='https://www.trustmf.com/our-products/trustmf-small-cap-fund'
                db.metric('Trustmf Small Cap Fund','All','aum',day.isoformat(),value,'INR crore',page,h)
                did=providers.save_document('Trustmf Small Cap Fund','Official fund page data',page,'source page','Fund',origin='AMC');providers.doc_version(did,h)
        body['tagName']='GetDownloadsForProductWeb';raw,_,_=read(url,body)
        for row in json.loads(raw).get('resultSetArray',[]):
            if row.get('slug')=='trustmf-small-cap-fund' and re.search('leaflet|factsheet',row.get('title',''),re.I):yield 'Trustmf Small Cap Fund',row['fileurl'],row['title']
    elif amc=='Sundaram':
        raw,h,_=read('https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json')
        from .structured_reports import extract
        extract(raw,'Sundaram Small Cap Fund','https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json',h)
        for row in json.loads(raw):
            if row.get('FUNDGROUP_ID')=='SC' and disclosures.same_fund_title(row.get('GROUP_NAME',''),'Sundaram Small Cap Fund'):
                yield 'Sundaram Small Cap Fund',urljoin('https://www.sundarammutual.com',row['PORTFOLIO_PATH']),'Monthly portfolio'
    elif amc in ('Abakkus','The Wealth'):
        family='Abakkus Small Cap Fund' if amc=='Abakkus' else 'The Wealth Company Small Cap Fund'
        page='https://www.abakkusmf.com/statutory-disclosures.html' if amc=='Abakkus' else 'https://www.wealthcompanyamc.in/literature-forms/portfolio-documents/monthly/'
        raw,_,_=read(page);links=providers.candidate_links(BeautifulSoup(raw,'html.parser'),page)
        rows=[]
        for url,title in links.items():
            text=url+' '+title
            if amc=='Abakkus':match=re.search(r'fund.spectrum|monthly.portfolio|mutual.fund.31',text,re.I)
            else:match=re.search(r'small[ _-]*cap',text,re.I) and re.search(r'monthly|portfolio',text,re.I)
            if match and re.search(r'\.(?:pdf|xlsx?)(?:\?|$)',url,re.I):rows.append((family,url,title))
        # Newest publisher-dated titles first, with a bounded archive backfill.
        def rank(row):
            text=row[1]+' '+row[2]
            years=re.findall(r'20[12]\d',text);y=max(map(int,years),default=0)
            m=max((i for i in range(1,13) if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],text,re.I)),default=0)
            return y,m
        yield from sorted(rows,key=rank,reverse=True)[:8]


def update(progress=lambda _:None):
    results=[]
    def collect(amc):
        count=0;fail=[]
        progress('Official reports · '+amc)
        try:
            for family,url,title in discover(amc):
                try:count+=store_report(amc,family,url,title)
                except Exception as e:fail.append((str(e) or type(e).__name__).splitlines()[0][:180])
        except Exception as e:fail.append((str(e) or type(e).__name__).splitlines()[0][:180])
        detail=f'{count} dated facts/holdings'+('; '+ '; '.join(fail) if fail else '')
        # A separate audit survives even when the numeric fund API has no PDF.
        with db.connect() as c:c.execute('INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)',('amc-reports',db.now(),db.now(),'partial' if fail else 'ok',amc+': '+detail))
        progress(amc+': '+detail)
        return amc+': '+detail
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(collect,['Abakkus','Bank of India','UTI','Bandhan','Samco','TRUST','Sundaram','The Wealth']))
    return '; '.join(results)
