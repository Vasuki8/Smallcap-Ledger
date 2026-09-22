"""Discover official reports from the same public endpoints as AMC websites."""
import calendar
import json
import re
import httpx
from datetime import date,datetime
from urllib.parse import urljoin,quote
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
    body,h,_=read(url)
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
        seen=set();candidates={}
        def add(url,title):
            if not isinstance(url,str):return
            url=url.replace('\\/','/').strip()
            if url.startswith('//'):url='https:'+url
            if url.startswith('/'):url=urljoin(root,url)
            if not re.search(r'\.(?:pdf|xlsx?|xml)(?:[?#]|$)',url,re.I):return
            if disclosures.official_publication_url(url,amc):
                candidates[url]=str(title or url.rsplit('/',1)[-1])[:300]
        def walk(node,label='Bandhan official report'):
            if isinstance(node,dict):
                own=next((node.get(k) for k in ('title','name','caption','description') if isinstance(node.get(k),str)),label)
                for v in node.values():walk(v,own)
            elif isinstance(node,list):
                for v in node:walk(v,label)
            elif isinstance(node,str):
                add(node,label)
                if '<' in node and '>' in node:
                    for u,t in providers.candidate_links(BeautifulSoup(node,'html.parser'),root).items():add(u,t)
        for page in pages:
            raw,_,_=read(page)
            soup=BeautifulSoup(raw,'html.parser')
            for url,title in providers.candidate_links(soup,page).items():add(url,title)
        # The investor-facing site is a React app. Inspect a bounded number of
        # same-domain static JS bundles strictly as text for public document/API
        # routes; never execute the scripts or follow arbitrary discovered URLs.
        app='https://bandhanmutual.com/downloads/factsheets'
        bundle_hints=[]
        try:
            raw,_,_=read(app);soup=BeautifulSoup(raw,'html.parser')
            scripts=[]
            for tag in soup.select('script[src]'):
                src=urljoin(app,tag.get('src',''))
                if (src.startswith('https://bandhanmutual.com/') or src.startswith('https://www.bandhanmutual.com/')) and re.search(r'\.js(?:\?|$)',src,re.I):
                    scripts.append(src)
            scripts=sorted(dict.fromkeys(scripts),key=lambda u:(0 if re.search(r'(?:main|app)',u,re.I) else 1,u))[:12]
            if scripts:print('Bandhan app bundles: '+json.dumps(scripts),flush=True)
            for src in scripts:
                try:
                    providers.can_crawl(src)
                    body,_,_=providers.fetch(src,archive=False,max_bytes=6*1024*1024)
                    text=body.decode('utf-8',errors='replace')
                    for m in re.finditer(r'facts?heets?',text,re.I):
                        snippet=text[max(0,m.start()-220):m.end()+320]
                        for value in re.findall(r'https?://[^"'+"'"+r'\\\s]{8,300}|/[A-Za-z0-9_./?=&%-]{4,240}',snippet):
                            if re.search(r'fact|sheet|download|api|asset',value,re.I):
                                bundle_hints.append(value[:300])
                    for value in re.findall(r'https?://[^"'+"'"+r'\\\s]+\.(?:pdf|xlsx?|xml)(?:\?[^"'+"'"+r'\\\s]*)?',text,re.I):
                        add(value,'Bandhan investor-site document')
                except Exception as e:
                    detail=(str(e) or type(e).__name__).splitlines()[0][:180]
                    print('Bandhan bundle inspection failed '+src+': '+detail,flush=True)
                    # One-time-safe fallback for oversized public static bundles:
                    # read at most 32 MiB in 1 MiB HTTP Range chunks. The bundle is
                    # never archived, scripts are never executed, and an ignored
                    # Range request stops immediately.
                    if 'larger than the 25 MB archive limit' in detail and re.search(r'/static/js/(?:main|app)[^/]*\.js(?:\?|$)',src,re.I):
                        try:
                            providers.public_url(src);providers.can_crawl(src)
                            chunk_size=1024*1024;max_scan=32*1024*1024
                            with httpx.Client(timeout=httpx.Timeout(30,connect=15),headers={'User-Agent':providers.USER_AGENT,'Accept':'*/*'},follow_redirects=False) as client:
                                probe=client.get(src,headers={'Range':'bytes=0-0'})
                                previous=''
                                def inspect_piece(piece):
                                    nonlocal previous
                                    text=previous+piece.decode('utf-8',errors='replace')
                                    previous=text[-700:]
                                    for value in re.findall(r'https?://[^"'+"'"+r'\\\s]+\.(?:pdf|xlsx?|xml)(?:\?[^"'+"'"+r'\\\s]*)?',text,re.I):
                                        add(value,'Bandhan investor-site document')
                                    for absolute in re.findall(r'https?://[^"'+"'"+r'\\\s]{8,300}',text):
                                        if re.search(r'bandhan|api|asset',absolute,re.I) and re.search(r'fact|sheet|download|document|api',absolute,re.I):
                                            bundle_hints.append(absolute[:300])
                                    for mm in re.finditer(r'facts?heets?|assets\.bandhanmutual\.com',text,re.I):
                                        snippet=text[max(0,mm.start()-350):mm.end()+500]
                                        for value in re.findall(r'["\']([^"\']{3,320})["\']',snippet):
                                            if re.search(r'fact|sheet|download|api|asset',value,re.I):
                                                bundle_hints.append(value[:300])
                                if probe.status_code==206:
                                    m=re.match(r'bytes\s+\d+-\d+/(\d+)',probe.headers.get('content-range',''),re.I)
                                    if not m:raise ValueError('Static bundle omitted Content-Range total')
                                    total=int(m.group(1))
                                    if total>max_scan:raise ValueError('Static bundle exceeds 32 MiB bounded scan')
                                    for start in range(0,total,chunk_size):
                                        end=min(total-1,start+chunk_size-1)
                                        rr=client.get(src,headers={'Range':f'bytes={start}-{end}'})
                                        if rr.status_code!=206 or len(rr.content)>chunk_size+1024:
                                            raise ValueError('Static bundle range response was not bounded')
                                        inspect_piece(rr.content)
                                elif probe.status_code==200:
                                    # Server ignores Range. Stream once, retain only a small
                                    # overlap, and abort before 32 MiB instead of buffering.
                                    total=0;previous=''
                                    with client.stream('GET',src) as rr:
                                        rr.raise_for_status()
                                        if rr.is_redirect:raise ValueError('Static bundle redirected during bounded scan')
                                        for piece in rr.iter_bytes(chunk_size=64*1024):
                                            total+=len(piece)
                                            if total>max_scan:raise ValueError('Static bundle exceeds 32 MiB bounded stream scan')
                                            inspect_piece(piece)
                                else:
                                    raise ValueError('Static bundle returned '+str(probe.status_code))
                            print('Bandhan bounded bundle scan completed: '+str(total)+' bytes',flush=True)
                        except Exception as range_error:
                            range_detail=(str(range_error) or type(range_error).__name__).splitlines()[0][:220]
                            print('Bandhan bounded bundle scan stopped: '+range_detail,flush=True)
                            bundle_hints.append('range-error:'+type(range_error).__name__)
                    else:
                        bundle_hints.append('bundle-error:'+type(e).__name__)
            if bundle_hints:
                print('Bandhan app route hints: '+json.dumps(list(dict.fromkeys(bundle_hints))[:24]),flush=True)
        except Exception as e:
            print('Bandhan investor-site inspection: '+(str(e) or type(e).__name__).splitlines()[0][:220],flush=True)
        # Bandhan's WordPress templates currently keep document fields outside
        # the rendered post body. Query only the public REST search/media
        # endpoints, inspect returned data as JSON, and keep official document
        # URLs only. No script from the CMS is executed.
        api_queries=[
            root+'/wp-json/wp/v2/search?search=Monthly%20Factsheets%202026&per_page=20',
            root+'/wp-json/wp/v2/media?search=factsheet&per_page=50',
            root+'/wp-json/wp/v2/media?search=small%20cap&per_page=50',
        ]
        api_errors=[]
        for api in api_queries:
            try:
                raw,_,_=read(api)
                data=json.loads(raw)
                walk(data)
                for row in data if isinstance(data,list) else []:
                    links=row.get('_links',{}) if isinstance(row,dict) else {}
                    for item in links.get('self',[]):
                        href=item.get('href') if isinstance(item,dict) else None
                        if not href:continue
                        try:
                            detail,_,_=read(href);walk(json.loads(detail))
                        except Exception as e:api_errors.append((str(e) or type(e).__name__).splitlines()[0][:100])
            except Exception as e:
                api_errors.append((str(e) or type(e).__name__).splitlines()[0][:100])
        for url,title in candidates.items():
            if url in seen:continue
            seen.add(url)
            yield family,url,title
        if not seen:
            detail='; '.join(dict.fromkeys(api_errors))[:350]
            raise ValueError('Bandhan CMS exposed no official document URL through HTML or public WordPress media metadata'+('; '+detail if detail else ''))
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
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(collect,['Abakkus','Bank of India','UTI','Bandhan','TRUST','Sundaram','The Wealth']))
    return '; '.join(results)
