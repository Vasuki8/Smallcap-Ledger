from __future__ import annotations
import calendar
import csv
import io
import ipaddress
import json
import os
import re
import socket
import threading
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse, urljoin, urlencode, unquote
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup
from . import db

AMFI_NAV = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI = "https://api.mfapi.in/mf"
NIFTY_PAGE = "https://www.niftyindices.com/reports/historical-data"
NIFTY_API = "https://www.niftyindices.com/BackPage/getTotalReturnIndexString"
BENCHMARK = "Nifty Smallcap 250 TRI"
USER_AGENT = "SmallcapLedger/1.0 (local personal research)"
_robots = {}
_proxy_public_hosts = set()


def iso(value):
    value=str(value).strip().strip("()")
    value=re.sub(r"^(?:As (?:on|of)|NAV as on)\s*", "", value, flags=re.I)
    for fmt in ("%Y-%m-%d","%d-%b-%Y","%d-%m-%Y","%d %b %Y","%d/%m/%Y","%d/%m/%y","%d %B %Y","%B %d, %Y","%B %d %Y","%b %d %Y","%d-%b-%y"):
        try: return datetime.strptime(value,fmt).date().isoformat()
        except ValueError: pass
    raise ValueError(f"Unrecognized date: {value[:60]}")


def number(value):
    v=float(str(value).replace(",", "").replace("%", "").strip())
    if not (-1e15<v<1e15): raise ValueError("Non-finite or out-of-range number")
    return v


def public_url(url):
    p=urlparse(url)
    if p.scheme not in ("http","https") or not p.hostname or p.username or p.password or p.port not in (None,80,443):
        raise ValueError("Use a public HTTP(S) source URL without credentials")
    if p.hostname in _proxy_public_hosts:return url
    # Some managed networks resolve approved public hosts at the HTTP/SOCKS proxy.
    # Only the bundled public-source domains may use that path if local DNS is unavailable.
    try:
        addresses=socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except socket.gaierror:
        trusted={'mfapi.in','amfiindia.com','niftyindices.com'}
        trusted.update(urlparse(x[1]).hostname.removeprefix('www.') for x in json.loads((db.ROOT/'tracker'/'sources.json').read_text()))
        trusted.update(h for hosts in json.loads((db.ROOT/'tracker'/'document_hosts.json').read_text()).values() for h in hosts)
        proxy=any(os.environ.get(k) for k in ('HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy'))
        if proxy and any(p.hostname==d or p.hostname.endswith('.'+d) for d in trusted):
            _proxy_public_hosts.add(p.hostname)
            return url
        raise
    for entry in addresses:
        if not ipaddress.ip_address(entry[4][0]).is_global:
            raise ValueError("Private network addresses cannot be used as data sources")
    return url


def fetch(url, *, body=None, archive=True, max_bytes=25*1024*1024):
    original=url
    try:
        with httpx.Client(timeout=httpx.Timeout(30,connect=15),headers={"User-Agent":USER_AGENT,"Accept":"*/*"}, follow_redirects=False) as client:
            for _ in range(6):
                public_url(url)
                with client.stream("POST" if body is not None else "GET",url,json=body,
                                   headers={"Referer":NIFTY_PAGE} if "niftyindices.com" in url else {}) as r:
                    if r.is_redirect:
                        url=urljoin(url,r.headers.get("location",""))
                        continue
                    r.raise_for_status()
                    content=bytearray()
                    for chunk in r.iter_bytes():
                        content.extend(chunk)
                        if len(content)>max_bytes: raise ValueError("Source is larger than the 25 MB archive limit; use its original link")
                    content=bytes(content)
                    typ=r.headers.get("content-type", "application/octet-stream")
                    h=db.archive(content,typ) if archive else None
                    if archive:
                        with db.connect() as c: c.execute("INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",(original,db.now(),"ok",h))
                    return content,h,typ
            raise ValueError("Too many redirects")
    except Exception as e:
        if archive:
            with db.connect() as c: c.execute("INSERT INTO fetches(url,fetched_at,status,detail) VALUES(?,?,?,?)",(original,db.now(),"error",str(e)[:400]))
        raise


def can_crawl(url):
    origin=f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if origin in _robots and (datetime.now(timezone.utc)-_robots[origin][1]).total_seconds()>86400:
        del _robots[origin]
    if origin not in _robots:
        try:
            content,_,_=fetch(origin+"/robots.txt",archive=False,max_bytes=1024*1024)
            rp=RobotFileParser();rp.parse(content.decode(errors="replace").splitlines())
            _robots[origin]=(rp,datetime.now(timezone.utc))
        except httpx.HTTPStatusError as e:
            # RFC 9309 section 2.3.1.3: a 4xx robots resource is unavailable.
            # Rate limits and server/network errors still stop automatic access.
            if 400<=e.response.status_code<500 and e.response.status_code!=429: _robots[origin]=(None,datetime.now(timezone.utc))
            else: raise ValueError("Robots policy could not be checked") from e
    rp=_robots[origin][0]
    if rp is not None and not rp.can_fetch(USER_AGENT,url):
        raise ValueError("Automatic access is disallowed by this site's robots policy; open the source or import a downloaded file")
    return True


def family_name(name):
    name=re.split(r"\s*[-–(]?\s*\b(?:Direct|Regular|Growth|IDCW|Dividend|Bonus|Retail|Institutional)\b",name,1,flags=re.I)[0]
    return re.sub(r"\s+"," ",name).strip(" -–()").title().replace("Hdfc","HDFC").replace("Sbi","SBI").replace("Hsbc","HSBC").replace("Icici","ICICI").replace("Dsp","DSP").replace("Uti","UTI").replace("Lic","LIC")


def is_small_category(value):
    return bool(re.search(r"(?:^|[-(])\s*(?:Equity Scheme\s*-\s*)?Small\s*Cap\s*Fund\s*\)?$",value,re.I))


def option_type(raw,name=''):
    text=(raw or name).strip().lower()
    if 'bonus' in text:return 'Bonus'
    if re.search(r'idcw|dividend|income distribution|reinvest|payout',text):return 'IDCW'
    if 'growth' in text:return 'Growth'
    return 'Other'


def plan_type(raw,name=''):
    text=(raw or name).strip().lower()
    for word in ('direct','institutional','retail','regular'):
        if re.search(r'\b'+word+r'\b',text):return word.title()
    return 'Unspecified'


def parse_amfi(text):
    header=[];category="";amc="";result=[]
    for line in text.lstrip("\ufeff").splitlines():
        line=line.strip()
        if not line: continue
        if line.startswith("Scheme Code;"):
            header=[x.strip() for x in line.split(";")];continue
        if ";" not in line:
            if "Schemes(" in line: category=line
            elif not line.startswith(("Scheme", "Note")): amc=line
            continue
        fields=line.split(";")
        if not fields[0].isdigit() or not is_small_category(category): continue
        row=dict(zip(header,fields))
        name=row.get("Scheme Name","")
        raw_plan=row.get('Plan','').strip();raw_option=row.get('Option','').strip()
        plan=plan_type(raw_plan,name)
        option=option_type(raw_option,name)
        try:
            nav=number(row.get("Net Asset Value",row.get("NAV","")));day=iso(row["Date"])
            if nav<=0 or day>date.today().isoformat(): continue
        except (ValueError,KeyError): continue
        isin=row.get("ISIN Div Payout/ ISIN Growth")
        reinvest=row.get("ISIN Div Reinvestment")
        full=name if not row.get("Plan") else f"{name} · {plan} · {raw_option}"
        result.append({"code":int(fields[0]),"name":full,"family":family_name(name),"amc":amc,"plan":plan,
                       "option":option,"raw_plan":raw_plan,"raw_option":raw_option,"isin":None if isin in ("-","") else isin,
                       "reinvestment_isin":None if reinvest in ("-","") else reinvest,"nav":nav,"date":day})
    return result


def latest_nav():
    content,_,_=fetch(AMFI_NAV)
    records=parse_amfi(content.decode("utf-8-sig",errors="replace"))
    if len(records)<20: raise ValueError("AMFI response did not contain a plausible small-cap category; existing archive was retained")
    with db.connect() as c:
        known={r['code']:dict(r) for r in c.execute('SELECT code,family,metadata_json FROM schemes')}
        # Keep archive grouping stable across a rename. Existing code matches also
        # carry newly introduced plan codes into the same historical fund group.
        families={s['family']:known[s['code']]['family'] for s in records if s['code'] in known}
        for s in records:
            s['family']=families.get(s['family'],s['family'])
            meta=json.loads(known.get(s['code'],{}).get('metadata_json','{}'))
            meta.update({'amfi_plan':s['raw_plan'],'amfi_option':s['raw_option']})
            if s['plan']=='Unspecified':s['plan']=plan_type('',meta.get('scheme_name',''))
            if s['option']=='Other':s['option']=option_type('',meta.get('scheme_name',''))
            c.execute('''INSERT INTO schemes(code,name,family,amc,plan,option,isin,reinvestment_isin,category_source,last_seen)
              VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,
              family=excluded.family,amc=excluded.amc,plan=excluded.plan,option=excluded.option,
              isin=excluded.isin,reinvestment_isin=excluded.reinvestment_isin,category_source=excluded.category_source,last_seen=excluded.last_seen''',
              tuple(s[k] for k in ("code","name","family","amc","plan","option","isin","reinvestment_isin"))+(AMFI_NAV,s["date"]))
            c.execute('UPDATE schemes SET metadata_json=? WHERE code=?',(json.dumps(meta),s['code']))
    for s in records: db.save_nav(s["code"],[(s["date"],s["nav"])],AMFI_NAV)
    return f"{len(records)} AMFI scheme codes across {len(set(x['family'] for x in records))} small-cap funds; latest NAV {max(x['date'] for x in records)}"


def backfill(code):
    url=f"{MFAPI}/{code}"
    try:
        content,_,_=fetch(url)
        data=json.loads(content)
        if int(data.get("meta",{}).get("scheme_code",0))!=code: raise ValueError("Provider returned a different scheme code")
        points=[]
        for x in data.get("data",[]):
            d=iso(x["date"]);v=number(x["nav"])
            if v>0 and d<=date.today().isoformat(): points.append((d,v))
        if not points: raise ValueError("No historical NAV returned")
        db.save_nav(code,points,url)
        with db.connect() as c:
            current=c.execute('SELECT metadata_json,plan,option FROM schemes WHERE code=?',(code,)).fetchone()
            meta={**json.loads(current['metadata_json']),**data['meta']}
            plan=current['plan'] if current['plan']!='Unspecified' else plan_type('',data['meta'].get('scheme_name',''))
            option=current['option'] if current['option']!='Other' else option_type('',data['meta'].get('scheme_name',''))
            c.execute("UPDATE schemes SET history_checked=?,history_status=?,metadata_json=? WHERE code=?",
                      (db.now(),f"{len(points)} NAV observations",json.dumps(meta),code))
            c.execute('UPDATE schemes SET plan=?,option=? WHERE code=?',(plan,option,code))
        return len(points)
    except Exception as e:
        with db.connect() as c: c.execute("UPDATE schemes SET history_checked=?,history_status=? WHERE code=?",(db.now(),"Error: "+str(e)[:200],code))
        raise


def fetch_benchmark(progress=lambda _:None):
    latest=db.one("SELECT MIN(date) first,MAX(date) last FROM benchmark WHERE name=?",(BENCHMARK,))
    # Recover an interrupted backfill using per-year checkpoints, then refresh the current year.
    start_year=2005
    total=0
    for year in range(start_year,date.today().year+1):
        key=f"nifty_year_{year}"
        if year<date.today().year and db.setting(key,False): continue
        start=date(year,1,1);end=min(date(year,12,31),date.today())
        progress(f"Archiving benchmark history: {year}")
        payload={"cinfo":json.dumps({"name":"NIFTY SMALLCAP 250","indexName":"NIFTY SMALLCAP 250",
                                     "startDate":start.strftime("%d-%b-%Y"),"endDate":end.strftime("%d-%b-%Y")})}
        content,_,_=fetch(NIFTY_API,body=payload)
        data=json.loads(content)
        if isinstance(data,dict) and 'd' in data: data=data['d']
        if isinstance(data,str): data=json.loads(data)
        if not isinstance(data,list): raise ValueError("NSE changed its TRI response format")
        points=[]
        for row in data:
            if re.sub(r"\s","",row.get("Index Name","").lower())!="niftysmallcap250": raise ValueError("Different benchmark returned")
            d=iso(row["Date"]);v=number(row["TotalReturnsIndex"])
            if start.isoformat()<=d<=end.isoformat() and v>0: points.append((d,v))
        if not points and year>=2006: raise ValueError(f"No TRI observations for {year}")
        db.save_benchmark(BENCHMARK,points,NIFTY_PAGE)
        total+=len(points)
        with db.connect() as c: c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(key,"true"))
    return f"{total} benchmark observations updated"


def document_title(title,url):
    title=re.sub('[\u200b-\u200d\ufeff]','',title).strip()
    generic_report=title.lower() in ('factsheet','factsheets','official factsheet','monthly factsheet',
        'small cap monthly factsheet','portfolio','portfolios','official portfolio','latest monthly portfolio','official report archive')
    if title.lower() in ('download','click here','read more','view','pdf','excel','download pdf','download excel') or (generic_report and re.search(r'\.(?:pdf|xlsx?|xml)$',urlparse(url).path,re.I)):
        title=unquote(urlparse(url).path.rsplit('/',1)[-1])
        title=re.sub(r'\.(pdf|xlsx?|xml)$','',title,flags=re.I).replace('_',' ').replace('-',' ')
        if title: title=title[0].upper()+title[1:]
        title=re.sub(r'\bsbi\b','SBI',title,flags=re.I)
    return title


def save_document(family,title,url,kind="disclosure",scope="Fund",published=None,origin="AMC"):
    from .publications import exclusion_reason
    reason=exclusion_reason(family,url,title)
    if reason:raise ValueError(reason)
    title=document_title(title,url)
    with db.connect() as c:
        c.execute('''INSERT INTO documents(family,title,kind,scope,url,published_at,first_seen,last_seen,origin)
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(family,url) DO UPDATE SET title=excluded.title,last_seen=excluded.last_seen,
          published_at=COALESCE(excluded.published_at,documents.published_at)''',
          (family,title[:500],kind,scope,url,published,db.now(),db.now(),origin))
        return c.execute("SELECT id FROM documents WHERE family=? AND url=?",(family,url)).fetchone()[0]


def doc_version(doc_id, content_hash):
    with db.connect() as c: c.execute("INSERT OR IGNORE INTO document_versions(document_id,hash,observed_at) VALUES(?,?,?)",(doc_id,content_hash,db.now()))


def classify(title,url):
    s=(title+" "+url).lower()
    if re.search(r"portfolio|holdings",s): return "portfolio"
    if re.search(r"factsheet|fact.sheet|fund.facts",s): return "factsheet"
    if re.search(r"newsletter|market.*(?:view|outlook|update)|equity.outlook|investment.view|cio.*(?:view|letter)|product.?note|presentation",s): return "market view"
    if re.search(r'letter.*unitholder|unitholder.*letter',s):return 'unitholder letter'
    if re.search(r"(?:^|[ /_-])(?:sid|kim|ssd)(?:[ /_.-]|$)|scheme.summary|scheme information document|key information memorandum",s): return "scheme document"
    return "disclosure"


def candidate_links(soup,base):
    found={}
    for a in soup.select("a[href]"):
        href=a.get("href","")
        if href.startswith(("#","javascript:","mailto:","tel:")): continue
        url=urljoin(base,href)
        title=a.get_text(" ",strip=True) or a.get("title","") or urlparse(url).path.rsplit("/",1)[-1]
        found[url]=title
    # Motilal's public HTML also exposes download fields as definition lists.
    if ((urlparse(base).hostname or '').removeprefix('www.')=='motilaloswalmf.com'
            and urlparse(base).path.rstrip('/')=='/mutual-funds/motilal-oswal-small-cap-fund'):
        fields={'portfoliourl':'Latest monthly portfolio','latestfactsheetpdf':'Latest factsheet',
                'brochurepdf':'Fund brochure','presentationpdf':'Fund presentation',
                'siddocumentpdf':'Scheme information document'}
        for tag in soup.select('strong'):
            label=tag.get_text(strip=True);key=label.rstrip(':').lower()
            if key not in fields:continue
            value=tag.parent.get_text(' ',strip=True).removeprefix(label).lstrip(': ')
            if value.startswith('/content/dam/motilal-mf/') and re.search(r'\.(?:pdf|xlsx?)(?:\?|$)',value,re.I):
                found[urljoin(base,value)]=fields[key]
    # Many AMC pages publish their download data as embedded JSON.
    def walk(node,inherited=''):
        if isinstance(node,dict):
            own=node.get('description') or node.get('filename') or node.get('title') or node.get('name') or inherited
            if not isinstance(own,str) or len(own)>600:own=inherited
            for k,v in node.items():
                if k.lower() in ("url","uri","xls","xlsx","xml","pdf","fileurl","downloadurl") and isinstance(v,str) and v.startswith(("https://","/")):
                    u=urljoin(base,v)
                    title=own or u.rsplit("/",1)[-1]
                    if isinstance(title,str): found[u]=BeautifulSoup(title,"html.parser").get_text(" ",strip=True)
                elif isinstance(v,(dict,list)): walk(v,own)
        elif isinstance(node,list):
            for v in node: walk(v,inherited)
    for script in soup.select('script[type="application/json"],script[id="__NEXT_DATA__"]'):
        try: walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError): pass
    return found
