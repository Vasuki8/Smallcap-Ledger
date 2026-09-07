from __future__ import annotations
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import date,datetime
from urllib.parse import urlparse,unquote
from bs4 import BeautifulSoup
from . import db
from .providers import fetch,can_crawl,iso,number,candidate_links,classify,save_document,doc_version


def clean(v):
    return BeautifulSoup(str(v),"html.parser").get_text(" ",strip=True)


def official_publication_url(url,amc_match):
    """Only the fund house's registered source domains and their subdomains."""
    host=(urlparse(url).hostname or '').lower()
    roots={urlparse(u).hostname.lower().removeprefix('www.') for amc,u,_ in json.loads((db.ROOT/'tracker'/'sources.json').read_text()) if amc.lower()==amc_match.lower()}
    # Custom source pages are explicit owner-provided AMC sources.
    roots.update((urlparse(r['url']).hostname or '').lower().removeprefix('www.') for r in db.rows('SELECT url FROM source_pages WHERE lower(amc_match)=lower(?)',(amc_match,)))
    hosts=json.loads((db.ROOT/'tracker'/'document_hosts.json').read_text())
    roots.update(hosts.get(amc_match,[]))
    return any(root and (host==root or host.endswith('.'+root)) for root in roots)


def same_fund_title(value,family):
    # A scheme title, possibly followed by its parenthesized scheme description.
    # A holding mentioning the fund, an index fund, or a generic small-cap phrase
    # must never establish ownership of the containing report.
    normalize=lambda x:re.sub('[^a-z0-9]','',x.lower())
    return normalize(str(value).split('(')[0])==normalize(family)


def report_date(text):
    # Disclosure spreadsheets use period-ended labels and Excel date cells.
    from .report_parser import DATE,dated,normalize
    for m in re.finditer(r'(?:period ended|statement as on)\s*:?\s*('+DATE+r'|\d{4}-\d{2}-\d{2})',normalize(text),re.I):
        value=m.group(1)
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
            if value<=date.today().isoformat():return value
        elif dated(value):return dated(value)
    patterns=[r"(?:as\s*(?:on|of)|portfolio\s*(?:for)?)\s*[:\-]?\s*(\d{1,2}[ /-](?:[A-Za-z]+|\d{1,2})[ /-]\d{2,4})",
              r"(?:as\s*(?:on|of))\s*[:\-]?\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s*,?\s*(\d{4})"]
    for pattern in patterns:
        for m in re.finditer(pattern,text,re.I):
            try: return iso(" ".join(m.groups()))
            except ValueError: pass
    for m in re.finditer(r'(?:as\s*(?:on|of|at))\s*[:\-]?\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})',text,re.I):
        try:return iso(m.group(1).replace(',', ' '))
        except ValueError:pass
    return None


def portfolio(family,day,positions,complete,source,h):
    if not positions or not day: return None
    if any(not -100<=x["weight"]<=100 for x in positions): raise ValueError("Portfolio weights outside expected percentage units")
    if sum(x["weight"] for x in positions)>110: raise ValueError("Portfolio weight total suggests duplicated rows or wrong units")
    with db.connect() as c:
        c.execute("INSERT OR IGNORE INTO portfolios(family,as_of,complete,source,hash,observed_at) VALUES(?,?,?,?,?,?)",(family,day,int(complete),source,h,db.now()))
        sid=c.execute("SELECT id FROM portfolios WHERE family=? AND as_of=? AND hash=?",(family,day,h)).fetchone()[0]
        if not c.execute("SELECT 1 FROM holdings WHERE snapshot_id=? LIMIT 1",(sid,)).fetchone():
            c.executemany("INSERT INTO holdings(snapshot_id,isin,name,sector,weight,asset_type) VALUES(?,?,?,?,?,?)",
                          [(sid,x.get("isin"),x["name"],x.get("sector"),x["weight"],x.get("asset_type","Equity")) for x in positions])
    return sid


def hdfc(soup,family,url,h):
    script=soup.select_one("script#__NEXT_DATA__")
    if not script: return
    try:
        root=json.loads(script.string)["props"]["pageProps"]["singleFundResponse"]["data"]
        if not same_fund_title(root["banner"]["title"],family): return
    except (KeyError,TypeError,ValueError): return
    # Source gives a reported AUM date; undated facts are retained as observations, not backdated.
    observed=date.today().isoformat()
    for block in root["details"]:
        if "Overview" in block:
            overview=block["Overview"];data=overview["data"]
            if data.get("aum") and data.get("aumAsMonth"):
                db.metric(family,"All","aum",iso(data["aumAsMonth"]),number(data["aum"]),"INR crore",url,h)
            for plan,key in [("Direct","terDirecct"),("Regular","terRegular")]:
                if data.get(key): db.metric(family,plan,"ter_observed",observed,number(data[key]),"% p.a. · observed date",url,h)
            for key,name in [("exitLoad","exit_load"),("inceptionDate","plan_launch"),("minimumSip","minimum_sip")]:
                plan=('Regular' if '/regular' in urlparse(url).path else 'Direct') if key=='inceptionDate' else 'All'
                if data.get(key): db.metric(family,plan,name,observed,clean(data[key]),"Observed",url,h)
            if data.get("benchmark"): db.metric(family,"All","benchmark",observed,"; ".join(data["benchmark"]),"Observed",url,h)
            # Keep the complete published strategy in the archived source; display a brief factual objective.
            objective=clean(overview.get("overviewDescription",""))
            m=re.search(r"Investment Objective is to (.*?)(?:Investment Strategy|$)",objective)
            if m: db.metric(family,"All","objective",observed,m.group(1),"Observed",url,h)
        if "managers" in block:
            names=[x["managerName"]+" "+x.get("since","") for x in block["managers"]+block.get("overseasManagers",[])]
            db.metric(family,"All","managers",observed,"; ".join(names),"Observed",url,h)
        if block.get("portfolio") and block.get("top_10_holdings"):
            try:
                day=iso(block["portfolio"])
                positions=[{"name":x["name"],"weight":number(x["persent"])} for x in block["top_10_holdings"]["data"]]
                portfolio(family,day,positions,False,url,h)
            except (ValueError,KeyError): pass


def summary_xml(content,family,url,h):
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper(): raise ValueError("Unsupported XML declarations")
    tree=ET.fromstring(content.lstrip(b'\xef\xbb\xbf'))
    nodes={re.sub('[^a-z0-9]','',x.tag.split('}')[-1].lower()):' '.join(x.itertext()).strip() for x in tree.iter() if len(x)==0}
    fund=next((v for k,v in nodes.items() if k in ("fundname","schemename")),"")
    if not same_fund_title(fund,family): return
    mappings={"benchmarktier1":"benchmark","fundmanagername":"managers","descriptionobjectiveofthescheme":"objective",
              "exitloadifapplicable":"exit_load","allotmentdate":"fund_launch","riskometerasondate":"risk",
              "minimumapplicationamount":"minimum_lumpsum","statedassetallocation":"allocation_mandate",
              "annualexpensestatedmaximum":"stated_expense_maximum"}
    for k,label in mappings.items():
        if nodes.get(k): db.metric(family,"All",label,date.today().isoformat(),nodes[k],"Observed · scheme summary",url,h)


def spreadsheet(content,family,url,h):
    import openpyxl,xlrd
    if content[:2]==b'PK':
        book=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        sheets=[]
        for s in book.worksheets:
            cells=list(s.iter_rows())
            sheets.append((s.title,[[c.value for c in row] for row in cells],[[c.number_format or '' for c in row] for row in cells]))
        book.close()
    else:
        book=xlrd.open_workbook(file_contents=content,formatting_info=True)
        sheets=[(s.name,[s.row_values(i) for i in range(s.nrows)],
                 [[book.format_map[book.xf_list[s.cell_xf_index(i,j)].format_key].format_str for j in range(s.ncols)] for i in range(s.nrows)]) for s in book.sheets()]
    count=0
    for sheet,rows,formats in sheets:
        prefix=" ".join(str(v) for row in rows[:30] for v in row if v is not None)
        if not re.search(r"small\s*cap",sheet+" "+prefix,re.I): continue
        day=report_date(prefix)
        if not day or day>date.today().isoformat(): continue
        header=None;header_index=0
        for i,row in enumerate(rows[:35]):
            cells=[str(v or '').lower() for v in row]
            if any('isin' in v for v in cells) and any('nav' in v or 'aum' in v or ('net' in v and 'asset' in v) for v in cells):
                header=cells;header_index=i;break
        if header is None: continue
        if not any(same_fund_title(v,family) for row in rows[:header_index] for v in row if v):continue
        def col(pred): return next((i for i,v in enumerate(header) if pred(v)),None)
        ic=col(lambda x:'isin' in x)
        nc=col(lambda x:'name' in x or 'instrument' in x or 'issuer' in x)
        wc=col(lambda x:('nav' in x or 'aum' in x or ('net' in x and 'asset' in x)) and ('%' in x or 'percent' in x))
        sc=col(lambda x:'industry' in x or 'sector' in x)
        if nc is None or wc is None: continue
        positions=[];asset_type='Unclassified'
        for ri,row in enumerate(rows[header_index+1:],header_index+1):
            if max(nc,ic,wc)>=len(row): continue
            isin=str(row[ic] or '').strip()
            if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}",isin):
                label=' '.join(str(x or '') for x in row).lower()
                if 'equity' in label:asset_type='Equity'
                elif 'money market' in label:asset_type='Money market'
                elif 'debt' in label:asset_type='Debt'
                elif 'mutual fund' in label or 'exchange traded fund' in label:asset_type='Fund units'
                elif 'derivative' in label:asset_type='Derivative'
                continue
            try: weight=number(row[wc])
            except ValueError: continue
            # Excel stores a formatted 1.89% cell as 0.0189. Use the actual
            # number format, not a guess from the sum or the size of a holding.
            fmt=re.sub(r'"[^"\n]*"|\\.', '',formats[ri][wc])
            if isinstance(row[wc],(int,float)) and '%' in fmt:weight*=100
            positions.append({"name":str(row[nc]),"isin":isin,"weight":weight,"sector":str(row[sc] or '') if sc is not None else None,'asset_type':asset_type})
        # This extractor deliberately stores an ISIN-only view. Cash/derivatives may be omitted.
        if positions:
            portfolio(family,day,positions,False,url,h);count+=len(positions)
    return count


def factsheet_pdf(content,family,url,h):
    """Extract only explicitly labelled, dated facts; never estimate or OCR a number."""
    from pypdf import PdfReader
    reader=PdfReader(io.BytesIO(content))
    if reader.is_encrypted or len(reader.pages)>400:return 0
    from .report_parser import page_facts,owns_page,equity_positions
    count=0
    for page in reader.pages:
        text=page.extract_text() or ''
        if not owns_page(text,family):continue
        facts=page_facts(text,family)
        for fact in facts:
            db.metric(family,fact['plan'],fact['metric'],fact['as_of'],fact['value'],fact['unit'],url,h)
        count+=len(facts)
        positions=equity_positions(text,family)
        if positions and facts:
            portfolio(family,facts[0]['as_of'],positions,False,url,h);count+=len(positions)
            continue
        m=re.search(r'Portfolio as on[^\n]+\n([\s\S]+?)(?:\nSIP\b|\nPerformance\b|\nProduct Label|$)',text,re.I)
        if m:
            positions=[];sector=None
            for line in m.group(1).splitlines():
                line=line.strip()
                if not line or re.search(r'Company\s*/?\s*Issuer|Top 10 Holdings|Grand Total|^Total\b',line,re.I):continue
                match=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)',line)
                if match:
                    name=match.group(1).rstrip('*').strip();weight=number(match.group(2))
                    if not -100<=weight<=100:continue
                    kind='Cash' if re.search(r'cash|receivable',name,re.I) else 'Aggregate' if re.search(r'less than|other equit',name,re.I) else 'Equity'
                    positions.append({'name':name,'weight':weight,'sector':sector if kind=='Equity' else None,'asset_type':kind})
                elif len(line)<70 and not re.search(r'\d|\*',line):sector=line
            if positions:
                portfolio_day=report_date(m.group()[:200])
                if portfolio_day and portfolio_day<=date.today().isoformat():
                    portfolio(family,portfolio_day,positions,False,url,h);count+=len(positions)
    return count


def ingest_source(source):
    url=source["url"]
    families=db.rows("SELECT DISTINCT family FROM schemes WHERE instr(lower(amc),lower(?))>0",(source["amc_match"],))
    if not families: return "No matching small-cap fund yet"
    can_crawl(url)
    direct=bool(re.search(r'\.(pdf|xlsx?|xml)(?:\?|$)',url,re.I))
    content,h,_=fetch(url,max_bytes=(25 if direct else 8)*1024*1024)
    if direct:
        from .amc_reports import extract
        n=0
        for f in families:
            did=save_document(f['family'],source['label'],url,classify(source['label'],url),'AMC',origin='AMC')
            doc_version(did,h);n+=extract(content,f['family'],url,h)
        gaps=0 if n or classify(source['label'],url)=='scheme document' else 1
        return f'{n} extracted facts/holdings; 1 document archived; {gaps} download/parser gaps'
    soup=BeautifulSoup(content,"html.parser")
    links=candidate_links(soup,url)
    nlinks=0;narchive=0;errors=0;attempted=0;parsed=0;unrecognized=0
    last_attempt={r['url']:r['last'] for r in db.rows('SELECT url,MAX(fetched_at) last FROM fetches GROUP BY url')}
    for f in families:
        family=f["family"]
        # The source page itself is versioned, so changed facts can always be audited.
        page_id=save_document(family,source["label"],url,"source page","AMC",origin="AMC")
        doc_version(page_id,h)
        if "hdfcfund.com/explore/" in url: hdfc(soup,family,url,h)
        from .amc_metrics import parse_page
        parse_page(content,family,url,h)
        for target,title in sorted(links.items(),key=lambda item:last_attempt.get(item[0],'')):
            if target==url or not target.startswith(("http://","https://")): continue
            if not official_publication_url(target,source['amc_match']):continue
            combined=unquote(title+' '+target)
            if re.search(r'small[\s_\-]*cap',combined,re.I) and re.search(r'\b(?:ETF|index[\s_\-]*fund)\b',combined,re.I):continue
            specific=bool(re.search(r"small[\s_\-]*cap",combined,re.I)) and not re.search(r"mid[\s_\-]*small",combined,re.I)
            # A scheme-specific page can label a UUID download simply "Latest
            # Monthly Portfolio". Keep it as a candidate; parser verifies ownership.
            if re.search(r'small[\s_\-]*cap',url,re.I) and re.search(r'latest.*(?:portfolio|factsheet)',title,re.I):specific=True
            commentary=bool(re.search(r"newsletter|letter.*unitholder|unitholder.*letter|market[\s_\-]*(?:outlook|update|view)|equity[\s_\-]*outlook|cio[\s_\-]*(?:letter|view)",combined,re.I))
            download=bool(re.search(r"\.(?:pdf|xlsx?|xml)(?:\?|$)",target,re.I))
            omnibus=download and bool(re.search(r'factsheet|fact.sheet|monthly.portfolio|scheme.summary',combined,re.I)) and not re.search(r'large.cap|mid.cap|liquid.fund|debt.fund|flexi.cap|multi.cap',combined,re.I)
            directory=not download and bool(re.search(r'factsheet|fact.sheet|portfolio|disclosure|scheme.summary|newsletter|market.outlook|market.update',combined,re.I))
            if directory and urlparse(target).hostname==urlparse(url).hostname:
                with db.connect() as c:
                    if c.execute("SELECT COUNT(*) FROM source_pages WHERE amc_match=?",(source['amc_match'],)).fetchone()[0]<10:
                        c.execute("INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)",(source['amc_match'],target,title[:150]))
            if not (specific or commentary or omnibus): continue
            if not download and not commentary:
                # Add useful directories for the next scheduled pass; do not crawl recursively.
                if re.search(r"fund|disclosure|portfolio|factsheet",combined,re.I) and urlparse(target).hostname==urlparse(url).hostname:
                    with db.connect() as c:
                        if c.execute("SELECT COUNT(*) FROM source_pages WHERE amc_match=?",(source["amc_match"],)).fetchone()[0]<8:
                            c.execute("INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)",(source["amc_match"],target,title[:150]))
                continue
            if not download and len(title)<16: continue
            did=save_document(family,title,target,classify(title,target),"Fund" if specific else "AMC",origin="AMC")
            nlinks+=1
            # Bound each page pass; remaining original links stay available, with archive status visible.
            if attempted>=12: continue
            attempted+=1
            try:
                can_crawl(target)
                body,ch,typ=fetch(target)
                doc_version(did,ch);narchive+=1
                ext=urlparse(target).path.lower()
                if ext.endswith(('.xml','.xls','.xlsx','.pdf')):
                    from .amc_reports import extract
                    count=extract(body,family,target,ch);parsed+=count
                    if not count:
                        unrecognized+=1
                        if classify(title,target) in ('factsheet','portfolio'):errors+=1
            except Exception:
                errors+=1
    return f"{nlinks} relevant links; {narchive} documents archived; {parsed} facts/holdings; {unrecognized} documents without extracted tables; {errors} download/parser gaps" if nlinks else "Page archived; no automatically readable fund documents found"


def seed_sources():
    entries=json.loads((db.ROOT/'tracker'/'sources.json').read_text())
    from .amc_reports import monthly_sources
    entries.extend(monthly_sources())
    with db.connect() as c:
        c.executemany("INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)",entries)
