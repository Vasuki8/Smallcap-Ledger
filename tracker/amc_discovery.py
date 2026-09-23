"""Discover official reports from the same public endpoints as AMC websites."""
import calendar
import json
import re
from datetime import date,datetime
from urllib.parse import urljoin,quote,unquote,urlparse
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
    if amc=='Baroda':
        family='Baroda Bnp Paribas Small Cap Fund'
        page='https://www.barodabnpparibasmf.in/downloads/monthly-portfolio-scheme'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        candidates={}
        for a in soup.select('a[href]'):
            url=urljoin(page,a.get('href',''))
            container=a.find_parent(['li','tr','div']) or a.parent
            context=(container.get_text(' ',strip=True) if container else a.get_text(' ',strip=True))[:1200]
            candidates[url]=context or a.get_text(' ',strip=True) or url.rsplit('/',1)[-1]
        for url,title in providers.candidate_links(soup,page).items():candidates.setdefault(url,title)
        rows=[]
        for url,title in candidates.items():
            combined=unquote(url+' '+title)
            if not disclosures.official_publication_url(url,amc):continue
            path=urlparse(url).path.rsplit('/',1)[-1]
            all_funds=bool(re.search(r'monthly\s+portfolio\s*-?\s*all\s+funds',combined,re.I)
                           or re.match(r'BOBBNPMF_Monthly_Portfolio_',path,re.I))
            if not all_funds:continue
            if not re.search(r'\.xlsx?(?:[?#]|$)',url,re.I):continue
            day=None
            m=re.search(r'(\d{1,2})[-_/](\d{1,2})[-_/](20\d{2})',combined)
            if m:
                try:day=date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
                except ValueError:pass
            if day is None:
                m=re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})',combined,re.I)
                if m:
                    try:day=datetime.strptime(f'{m.group(1)} {m.group(2)} {m.group(3)}','%d %B %Y').date()
                    except ValueError:pass
            if day and day<=date.today():rows.append((day,url,title))
        if not rows:raise ValueError('No official Baroda BNP Paribas all-funds monthly portfolio workbook was exposed')
        day,url,title=max(rows,key=lambda r:r[0])
        yield family,url,title or f'Monthly Portfolio - all funds as on {day.isoformat()}'
    elif amc=='Aditya Birla':
        family='Aditya Birla Sun Life Small Cap Fund'
        page='https://mutualfund.adityabirlacapital.com/forms-and-downloads/factsheets'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        rows=[]
        for url,title in providers.candidate_links(soup,page).items():
            combined=unquote(url+' '+title)
            if not disclosures.official_publication_url(url,amc):continue
            if not re.search(r'\.pdf(?:[?#]|$)',url,re.I):continue
            if not re.search(r'absl(?:mf)?[^/]{0,80}(?:factsheet|empower)|(?:factsheet|empower)[^/]{0,80}absl',combined,re.I):continue
            years=[int(x) for x in re.findall(r'20[12]\d',combined)]
            year=max(years,default=0)
            month=max((i for i in range(1,13)
                       if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
            if year:rows.append((year,month,url,title))
        if not rows:raise ValueError('No official ABSL factsheet PDF was exposed by the factsheet archive')
        newest=max((y,m) for y,m,_,_ in rows)
        for _,_,url,title in [r for r in rows if (r[0],r[1])==newest][:2]:
            yield family,url,title or 'Latest ABSL factsheet'
    elif amc=='Bank of India':
        body={'pagno':0,'category':None,'fromDate':None,'toDate':None,'LibraryName':'InvestorCorner','folderName':'FACTSHEETS','CategoryValue':'no'}
        raw,_,_=read('https://www.boimf.in/AjaxService.asmx/GetDocuments',body)
        rows=json.loads(json.loads(raw)['d'])['Documents']
        for row in rows[:3]:yield 'Bank Of India Small Cap Fund',row['FolderUrl'],row['DocName']
    elif amc=='Franklin':
        family='Franklin India Small Cap Fund'
        page='https://www.franklintempletonindia.com/fund-details/fund-overview/4373/franklin-india-small-cap-fund-erstwhile-franklin-india-smaller-companies-fund'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        candidates=[]
        for url,title in providers.candidate_links(soup,page).items():
            combined=unquote(url+' '+title)
            if not disclosures.official_publication_url(url,amc):continue
            ext=re.search(r'\.(xlsx?|xls|pdf)(?:[?#]|$)',url,re.I)
            if not ext:continue
            if not re.search(r'portfolio|monthly|as[ _-]*on',combined,re.I):continue
            day=None
            dmy=re.search(r'as[ _-]*on[ _-]*(\d{1,2})[ _-]+([A-Za-z]+)[,_ -]+(20\d{2})',combined,re.I)
            mdy=re.search(r'as[ _-]*on[ _-]*([A-Za-z]+)[ _-]+(\d{1,2})[,_ -]+(20\d{2})',combined,re.I)
            numeric=re.search(r'(\d{1,2})[._/-](\d{1,2})[._/-](20\d{2})',combined)
            try:
                if dmy:day=datetime.strptime(f'{dmy.group(1)} {dmy.group(2)} {dmy.group(3)}','%d %B %Y').date()
                elif mdy:day=datetime.strptime(f'{mdy.group(2)} {mdy.group(1)} {mdy.group(3)}','%d %B %Y').date()
                elif numeric:day=date(int(numeric.group(3)),int(numeric.group(2)),int(numeric.group(1)))
            except ValueError:day=None
            if day and day<=date.today():
                kind=ext.group(1).lower();priority=2 if kind in ('xls','xlsx') else 1
                candidates.append((day,priority,url,title))
        if not candidates:raise ValueError('No official Franklin monthly portfolio download discovered')
        newest=max(x[0] for x in candidates)
        pool=[x for x in candidates if x[0]==newest]
        for _,_,url,title in sorted(pool,key=lambda x:x[1],reverse=True)[:2]:
            yield family,url,title or f'Monthly portfolio as on {newest.isoformat()}'
    elif amc=='Union':
        # The Union fund-house homepage is slow, but the Small Cap factsheet is
        # published at a stable first-party URL. Fetch it directly every run;
        # downstream parsing still has to prove exact scheme ownership/date.
        yield 'Union Small Cap Fund','https://www.unionmf.com/docs/default-source/funddetail-downloads/fund-factsheets/union-small-cap-fund.pdf','Union Small Cap Fund factsheet'
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
        slugs=[
            'monthly-and-half-yearly-bandhan-small-cap-fund-31-august-2026',
            'monthly-and-half-yearly-bandhan-small-cap-fund-31-july-2026',
            'monthly-and-half-yearly-bandhan-small-cap-fund-30-june-2026',
        ]
        candidates={}
        def add_html(html,base,context=''):
            soup=BeautifulSoup(html,'html.parser')
            for url,title in providers.candidate_links(soup,base).items():
                if disclosures.official_publication_url(url,amc):
                    candidates[url]=context or title
        for slug in slugs:
            page=root+'/'+slug+'/'
            try:
                raw,_,_=read(page);add_html(raw,page,slug.replace('-',' '))
            except Exception:
                pass
            # Bandhan's WordPress pages often render no direct attachment link.
            # Resolve the same official post through the read-only WP REST API,
            # then inspect its attached media objects without executing scripts.
            api=root+'/wp-json/wp/v2/posts?slug='+slug
            try:
                raw,_,_=read(api)
                posts=json.loads(raw)
            except Exception:
                posts=[]
            for post in posts if isinstance(posts,list) else []:
                rendered=((post.get('content') or {}).get('rendered') or '')
                if rendered:add_html(rendered,page,slug.replace('-',' '))
                links=post.get('_links') or {}
                for rel in links.get('wp:attachment',[]):
                    href=rel.get('href') if isinstance(rel,dict) else None
                    if not href:continue
                    try:
                        media_raw,_,_=read(href)
                        media=json.loads(media_raw)
                    except Exception:
                        continue
                    for item in media if isinstance(media,list) else []:
                        url=item.get('source_url')
                        if not isinstance(url,str) or not disclosures.official_publication_url(url,amc):continue
                        title=((item.get('title') or {}).get('rendered') or
                               (item.get('caption') or {}).get('rendered') or
                               slug.replace('-',' '))
                        title=BeautifulSoup(str(title),'html.parser').get_text(' ',strip=True)
                        candidates[url]=title
        rows=[]
        for url,title in candidates.items():
            if not re.search(r'\.(?:pdf|xlsx?|xml)(?:[?#]|$)',url,re.I):continue
            combined=unquote(url+' '+title)
            if re.search(r'notice|press\s*release|riskometer|factsheet',combined,re.I):continue
            # The parent post is already the exact dated Small Cap portfolio
            # disclosure; prefer structured files when several attachments exist.
            ext=re.search(r'\.(xlsx?|xml|pdf)(?:[?#]|$)',url,re.I).group(1).lower()
            priority=3 if ext in ('xls','xlsx') else 2 if ext=='xml' else 1
            years=[int(x) for x in re.findall(r'20[12]\d',combined)]
            year=max(years,default=0)
            month=max((i for i in range(1,13)
                       if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
            rows.append((year,month,priority,url,title))
        if not rows:raise ValueError('No downloadable Bandhan Small Cap portfolio attachment was exposed by the official CMS posts')
        dated=[r for r in rows if r[0] and r[1]]
        pool=dated or rows
        newest=max((r[0],r[1]) for r in pool)
        for row in sorted((r for r in pool if (r[0],r[1])==newest),key=lambda r:r[2],reverse=True)[:2]:
            yield family,row[3],row[4] or 'Bandhan Small Cap monthly portfolio'
    elif amc=='Canara':
        family='Canara Robeco Small Cap Fund'
        today=date.today()
        for offset in (1,2):
            year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
            name=calendar.month_name[month].lower()
            yield family,f'https://digitalassets.canararobeco.com/digital-factsheet/{year}/{name}/Scheme/SMALL-CAP.html','Monthly digital factsheet'
    elif amc=='ITI':
        family='Iti Small Cap Fund'
        today=date.today()
        for offset in (1,2):
            year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
            name=calendar.month_name[month]
            yield family,f'https://www.itiamc.com/digitalfactsheet/{name}{year}/innerpages/Small-Cap.html','Monthly digital factsheet'
    elif amc=='Mahindra':
        family='Mahindra Manulife Small Cap Fund'
        today=date.today()
        for offset in (1,2):
            year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
            name=calendar.month_name[month].lower()
            yield family,f'https://www.mahindramanulife.com/digital-factsheet/{name}-{year}/Equity-funds/Small-Cap-Fund.html','Monthly digital factsheet'
    elif amc=='LIC':
        family='LIC Mf Small Cap Fund'
        page='https://www.licmf.com/downloads/factsheet'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        rows=[]
        for url,title in providers.candidate_links(soup,page).items():
            combined=unquote(url+' '+title)
            if not disclosures.official_publication_url(url,amc):continue
            if not re.search(r'\.pdf(?:[?#]|$)',url,re.I):continue
            if not re.search(r'fact[ _-]*sheet|factsheet',combined,re.I):continue
            day=None
            m=re.search(r'(\d{1,2})(?:st|nd|rd|th)?[ _-]+([A-Za-z]+)[ _-]+(20\d{2})',combined,re.I)
            if m:
                try:day=datetime.strptime(f'{m.group(1)} {m.group(2)} {m.group(3)}','%d %B %Y').date()
                except ValueError:pass
            if not day:
                years=[int(x) for x in re.findall(r'20[12]\d',combined)]
                year=max(years,default=0)
                month=max((i for i in range(1,13)
                           if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
                if year and month:day=date(year,month,calendar.monthrange(year,month)[1])
            if day and day<=date.today():rows.append((day,url,title))
        if not rows:raise ValueError('No official LIC MF factsheet PDF was exposed by the factsheet archive')
        newest=max(x[0] for x in rows)
        for _,url,title in [r for r in rows if r[0]==newest][:2]:
            yield family,url,title or f'Factsheet as on {newest.isoformat()}'
    elif amc=='HSBC':
        family='HSBC Small Cap Fund'
        today=date.today()
        # HSBC publishes the consolidated monthly factsheet ("The Asset") at a
        # stable first-party path. Check the two most recent completed months;
        # the downstream complete parser must still prove exact scheme/date/100%.
        for offset in (1,2):
            year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
            name=calendar.month_name[month].lower()
            yield family,f'https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-{name}-{year}.pdf',f'The Asset - {calendar.month_name[month]} {year}'
    elif amc=='PGIM':
        family='Pgim India Small Cap Fund'
        today=date.today()
        # PGIM's factsheet index is JS-driven, but the AMC serves the monthly
        # factsheet itself at a stable official document path. Fetch the two most
        # recent completed months; store_report still enforces registered AMC ownership.
        for offset in (1,2):
            year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
            name=calendar.month_name[month]
            yield family,f'https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet - {name} {year}.pdf',f'Factsheet - {name} {year}'

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
        yield family,chosen[3],chosen[4] or 'Samco Small Cap monthly portfolio'

    elif amc=='quant Mutual':
        family='Quant Small Cap Fund'
        page='https://quantmutual.com/statutory-disclosures'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        candidates={}
        # Quant exposes portfolio archives through a mix of ordinary links,
        # data attributes and JavaScript-backed disclosure rows. Retain nearby
        # row/list context; the downstream spreadsheet/PDF parser still has to
        # prove exact scheme ownership before saving any holdings.
        for tag in soup.find_all(True):
            container=tag.find_parent(['tr','li','div']) or tag.parent
            context=(container.get_text(' ',strip=True) if container else tag.get_text(' ',strip=True))[:1600]
            attrs=' '.join(str(v) for v in tag.attrs.values())
            for raw_value in [attrs,tag.get('href','') if hasattr(tag,'get') else '']:
                for m in re.finditer(r'(?:(?:https?:)?//[^"\'\s<>]+|/[^"\'\s<>]+)\.(?:xlsx?|xml|pdf)(?:\?[^"\'\s<>]*)?',str(raw_value).replace('\\/','/'),re.I):
                    url=urljoin(page,m.group(0))
                    if disclosures.official_publication_url(url,amc):
                        candidates[url]=context or url.rsplit('/',1)[-1]
        for url,title in providers.candidate_links(soup,page).items():
            if disclosures.official_publication_url(url,amc):
                candidates.setdefault(url,title)
        rows=[]
        for url,title in candidates.items():
            combined=unquote(url+' '+title)
            if not re.search(r'\.(?:xlsx?|xml|pdf)(?:[?#]|$)',url,re.I):continue
            specific=bool(re.search(r'quant[\s_\-]*small[\s_\-]*cap|small[\s_\-]*cap[\s_\-]*fund',combined,re.I))
            monthly=bool(re.search(r'monthly[\s_\-]*portfolio|portfolio[\s_\-]*statement',combined,re.I))
            portfolio_path=bool(re.search(r'/portfolio/',urlparse(url).path,re.I))
            all_funds=(monthly or portfolio_path) and bool(re.search(r'all[\s_\-]*(?:funds|schemes)|monthly[\s_\-]*portfolio(?![\s_\-]*fund)',combined,re.I))
            if not (specific and (monthly or portfolio_path) or all_funds):continue
            years=[int(x) for x in re.findall(r'20[12]\d',combined)]
            year=max(years,default=0)
            month=max((i for i in range(1,13) if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
            rows.append((year,month,url,title))
        if not rows:raise ValueError('No downloadable Quant monthly portfolio file was exposed by the statutory disclosure page')
        # A small bounded set covers the latest structured layouts and lets the
        # parser verify whether an all-funds file actually contains Small Cap.
        for _,_,url,title in sorted(rows,reverse=True)[:4]:
            yield family,url,title or 'Quant monthly portfolio'
    elif amc=='Tata':
        family='Tata Small Cap Fund'
        page='https://www.tatamutualfund.com/schemes-related/portfolio'
        raw,_,_=read(page);soup=BeautifulSoup(raw,'html.parser')
        candidates={}
        # Tata's disclosure page can expose downloads through anchors, data-*
        # attributes or embedded JSON. Preserve nearby context, but only accept
        # official downloadable monthly-portfolio files.
        for url,title in providers.candidate_links(soup,page).items():
            if disclosures.official_publication_url(url,amc):
                candidates[url]=title
        for tag in soup.find_all(True):
            container=tag.find_parent(['tr','li','div','section']) or tag.parent
            context=(container.get_text(' ',strip=True) if container else tag.get_text(' ',strip=True))[:1800]
            attrs=' '.join(str(v) for v in tag.attrs.values()).replace('\\/','/')
            for m in re.finditer(r'(?:(?:https?:)?//[^"\'\s<>]+|/[^"\'\s<>]+)\.(?:xlsx?|xml|pdf)(?:\?[^"\'\s<>]*)?',attrs,re.I):
                url=urljoin(page,m.group(0))
                if disclosures.official_publication_url(url,amc):
                    candidates.setdefault(url,context or url.rsplit('/',1)[-1])
        rows=[]
        for url,title in candidates.items():
            combined=unquote(url+' '+title)
            ext=re.search(r'\.(xlsx?|xml|pdf)(?:[?#]|$)',url,re.I)
            if not ext:continue
            # Require an actual monthly portfolio disclosure, not a notice,
            # press release, segregated-portfolio announcement or stale document
            # that merely contains the word "portfolio".
            if not re.search(r'monthly[\s_%-]*portfolio|portfolio[\s_%-]*monthly',combined,re.I):continue
            if re.search(r'press\s*release|notice|circular|segregated|fortnight|weekly|factsheet|sid|kim',combined,re.I):continue
            years=[int(x) for x in re.findall(r'20[12]\d',combined)]
            year=max(years,default=0)
            month=max((i for i in range(1,13)
                       if re.search(calendar.month_name[i]+'|'+calendar.month_abbr[i],combined,re.I)),default=0)
            if not year or not month or year<date.today().year-1:continue
            kind=ext.group(1).lower()
            priority=3 if kind in ('xls','xlsx') else 2 if kind=='xml' else 1
            rows.append((year,month,priority,url,title))
        if not rows:raise ValueError('No official Tata monthly portfolio download was exposed by the portfolio page')
        newest=max((r[0],r[1]) for r in rows)
        chosen=max((r for r in rows if (r[0],r[1])==newest),key=lambda r:r[2])
        yield family,chosen[3],chosen[4] or 'Tata monthly portfolio'
    elif amc=='TRUST':
        family='Trustmf Small Cap Fund'
        url='https://www.trustmf.com/api/api/Trust/GetData'
        body={'systemQueryFileName':'productsweb.xml','tagName':'GetOneProductWeb','searchField':'p.slug','searchValue':'trustmf-small-cap-fund','sortField':'','sortDirection':''}
        raw,h,_=read(url,body)
        rows=json.loads(raw).get('resultSetArray',[])
        row=next((r for r in rows if r.get('slug')=='trustmf-small-cap-fund' and disclosures.same_fund_title(r.get('title',''),family)),None)
        if row:
            # US-format timestamp is the field format used by this public API.
            day=datetime.strptime(row['aumasondate'],'%m/%d/%Y %I:%M:%S %p').date()
            value=providers.number(row['monthendaum'])
            if day<=date.today() and 0<value<10_000_000:
                page='https://www.trustmf.com/our-products/trustmf-small-cap-fund'
                db.metric(family,'All','aum',day.isoformat(),value,'INR crore',page,h)
                did=providers.save_document(family,'Official fund page data',page,'source page','Fund',origin='AMC');providers.doc_version(did,h)
        body['tagName']='GetDownloadsForProductWeb';raw,_,_=read(url,body)
        for row in json.loads(raw).get('resultSetArray',[]):
            if row.get('slug')=='trustmf-small-cap-fund' and re.search('leaflet|factsheet',row.get('title',''),re.I):
                target=urljoin('https://www.trustmf.com/',str(row.get('fileurl') or ''))
                if target and disclosures.official_publication_url(target,amc):
                    yield family,target,row['title']

        # TRUSTMF's SPA publishes monthly portfolio disclosures through the
        # same first-party read-only API, but under disclosuresweb.xml rather
        # than the product-download query above. Prefer the newest structured
        # workbook; downstream parsing still proves exact scheme ownership.
        portfolio_body={
            'systemQueryFileName':'disclosuresweb.xml',
            'tagName':'GetDisclosureByType',
            'searchField':'',
            'searchValue':'',
            'sortField':'uploaddate',
            'sortDirection':'DESC',
            'replaceField':'_slug_',
            'replaceValue':'portfolio-monthly-disclosure',
        }
        raw,_,_=read(url,portfolio_body)
        disclosures_rows=json.loads(raw).get('resultSetArray',[])
        candidates=[]
        for item in disclosures_rows if isinstance(disclosures_rows,list) else []:
            title=str(item.get('title') or '').strip()
            target=urljoin('https://www.trustmf.com/',str(item.get('fileurl') or item.get('slug') or '').strip())
            if not target or not disclosures.official_publication_url(target,amc):continue
            ext=re.search(r'\.(xlsx?|xml|pdf)(?:[?#]|$)',target,re.I)
            if not ext:continue
            m=re.search(r'as\s+on\s+(\d{1,2})[./-](\d{1,2})[./-](20\d{2})',title,re.I)
            day=None
            if m:
                try:day=date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
                except ValueError:pass
            # Prefer structured workbooks over PDFs when the same reporting
            # date is exposed more than once.
            kind=ext.group(1).lower()
            priority=3 if kind in ('xls','xlsx') else 2 if kind=='xml' else 1
            candidates.append((day or date.min,priority,target,title))
        if not candidates:raise ValueError('TRUSTMF official disclosure API exposed no monthly portfolio download')
        newest=max(x[0] for x in candidates)
        pool=[x for x in candidates if x[0]==newest] if newest!=date.min else candidates
        for _,_,target,title in sorted(pool,key=lambda x:x[1],reverse=True)[:2]:
            yield family,target,title or 'TRUSTMF monthly portfolio'
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
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(collect,['Abakkus','Aditya Birla','Bank of India','Baroda','Canara','Franklin','HSBC','LIC','Union','UTI','Bandhan','ITI','Mahindra','PGIM','Samco','quant Mutual','Tata','TRUST','Sundaram','The Wealth']))
    return '; '.join(results)
