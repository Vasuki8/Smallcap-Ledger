from __future__ import annotations
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import date,datetime
from urllib.parse import urlparse,unquote,parse_qs
from bs4 import BeautifulSoup
from . import db
from .publications import exclusion_reason
from .providers import fetch,can_crawl,iso,number,candidate_links,classify,save_document,doc_version


def clean(v):
    return BeautifulSoup(str(v),"html.parser").get_text(" ",strip=True)


def official_publication_url(url,amc_match):
    """Registered AMC domains, excluding known sections for another AMC's schemes."""
    if exclusion_reason(amc_match,url):return False
    parsed=urlparse(url);host=(parsed.hostname or '').lower()
    # Bandhan's public finance API returns disclosure binaries from one fixed
    # Google Cloud Storage bucket. Accept only that exact bucket path.
    if (str(amc_match).lower()=='bandhan' and host=='storage.googleapis.com'
        and parsed.path.startswith('/nonprod-static-assets-121to59kaawfgfi7bol/')):
        return True
    roots={urlparse(u).hostname.lower().removeprefix('www.') for amc,u,_ in json.loads((db.ROOT/'tracker'/'sources.json').read_text()) if amc.lower()==amc_match.lower()}
    # Custom source pages are explicit owner-provided AMC sources.
    roots.update((urlparse(r['url']).hostname or '').lower().removeprefix('www.') for r in db.rows('SELECT url FROM source_pages WHERE lower(amc_match)=lower(?)',(amc_match,)))
    hosts=json.loads((db.ROOT/'tracker'/'document_hosts.json').read_text())
    roots.update(hosts.get(amc_match,[]))
    return any(root and (host==root or host.endswith('.'+root)) for root in roots)


def resolve_registered_amc(value,source_rows):
    """Resolve a reviewed catalog AMC name to one unique registered source key."""
    generic={'mutual','fund','asset','management','amc','private','pvt','limited','ltd','company'}
    def words(text):
        return ' '.join(re.findall(r'[a-z0-9]+',str(text).lower()))
    def tokens(text):
        return frozenset(x for x in re.findall(r'[a-z0-9]+',str(text).lower()) if x not in generic)
    keys=list(dict.fromkeys(row[0] for row in source_rows))
    normalized=words(value)
    # Two real AMC names contain another registered source key as a later word.
    # Keep this narrow instead of making arbitrary multi-brand names resolve by
    # first-token order; genuinely ambiguous names must continue to return None.
    aliases={
        'kotak mahindra mutual fund':'Kotak',
        'mahindra manulife mutual fund':'Mahindra',
    }
    alias=aliases.get(normalized)
    if alias and any(str(key).lower()==alias.lower() for key in keys):
        return next(key for key in keys if str(key).lower()==alias.lower())
    target=tokens(value)
    if not target:return None
    exact=[key for key in keys if tokens(key)==target]
    if len(exact)==1:return exact[0]
    subsets=[]
    for key in keys:
        current=tokens(key)
        if current and (current<target or target<current):subsets.append(key)
    return subsets[0] if len(subsets)==1 else None


def registered_source_rows():
    rows=json.loads((db.ROOT/'tracker'/'sources.json').read_text())
    rows.extend((r['amc_match'],r['url'],r['label'])
                for r in db.rows('SELECT amc_match,url,label FROM source_pages'))
    return rows


def source_families(amc_match):
    """Return only schemes whose AMC resolves to this registered source key."""
    rows=registered_source_rows()
    key=str(amc_match or '').lower()
    return [
        {'family':r['family']}
        for r in db.rows('SELECT DISTINCT family,amc FROM schemes ORDER BY family')
        if str(resolve_registered_amc(r['amc'],rows) or '').lower()==key
    ]


def dated_communication_source_kind(title,url):
    """Classify a dated communication page, never a generic directory."""
    parsed=urlparse(url);path=unquote(parsed.path)
    host=(parsed.hostname or '').lower()
    if (host in ('www.sbimf.com','sbimf.com')
        and path.rstrip('/').lower()=='/learn-about-mutual-funds/2026-outlook'
        and str(title or '').strip().lower()=='2026 outlook'):
        return 'market view'
    kind=classify(title,url)
    if kind not in ('market view','unitholder letter'):return None
    if re.fullmatch(r'/.*digital-?factsheet/[A-Za-z]+-?\d{4}/[^/]+\.html',path,re.I):
        return kind
    if (host=='insights.abakkusinvest.com'
        and re.fullmatch(r'/market-outlook-[A-Za-z]+-20\d{2}/?',path,re.I)):
        return kind
    if (host=='cmsnew.bandhanmutual.com'
        and re.fullmatch(r'/market_outlook/market-outlook-(?:equity|debt)-[A-Za-z]+-20\d{2}/?',path,re.I)):
        return kind
    if (host in ('www.edelweissmf.com','edelweissmf.com')
        and path in (
            '/investor-insights/fund-market/curve',
            '/investor-insights/fund-market/factor-investing-2026-outlook',
        )):
        return kind
    if (host in ('www.icicipruamc.com','icicipruamc.com')
        and path.startswith('/blob/sebi-repo/Advertisements/')
        and re.search(r'/Release\s+date\s+\d{2}-\d{2}-20\d{2}/',path,re.I)
        and re.search(r'Monthly\s+Market\s+Outlook\.html$',path,re.I)):
        return kind
    return None


def source_context_communication_kind(source,target,title):
    """Use an explicit first-party communication category without broad inference."""
    kind=classify(title,target)
    if kind in ('market view','unitholder letter'):return kind
    source_kind=classify(source.get('label',''),source.get('url',''))
    if source_kind!='market view':return None
    base=urlparse(source.get('url',''));dest=urlparse(target)
    if (base.hostname or '').lower()!=(dest.hostname or '').lower():return None
    query=parse_qs(base.query)
    if ((base.hostname or '').lower() in ('www.axismf.com','axismf.com')
        and base.path.rstrip('/')=='/mutual-fund-knowledge-centre/articles'
        and query.get('tag')==['Market-Outlook']
        and dest.path.startswith('/mutual-fund-knowledge-centre/articles/')):
        return 'market view'
    if ((base.hostname or '').lower() in ('www.edelweissmf.com','edelweissmf.com')):
        base_path=base.path.rstrip('/')
        if (base_path=='/investor-insights/fund-market'
            and dest.path.startswith('/investor-insights/fund-market/')):
            return 'market view'
        if (base_path.startswith('/investor-insights/fund-market/')
            and dest.path.lower().startswith('/files/insigths/viewpoint/')
            and dest.path.lower().endswith('.pdf')):
            return 'market view'
    return None


def explicit_publication_date(content,media_type='',url=''):
    """Return only an explicit publication/update date supplied by the AMC."""
    if not content or ('html' not in str(media_type).lower()
                       and not content.lstrip().startswith(b'<')):return None
    try:soup=BeautifulSoup(content,'html.parser')
    except Exception:return None
    candidates=[]
    for attrs in (
        {'property':'article:published_time'},{'name':'article:published_time'},
        {'name':'date'},{'name':'publish-date'},{'name':'publication_date'},
    ):
        tag=soup.find('meta',attrs=attrs)
        if tag and tag.get('content'):candidates.append(tag['content'])
    for tag in soup.find_all('time'):
        if tag.get('datetime'):candidates.append(tag['datetime'])
    for script in soup.select('script[type="application/ld+json"]'):
        try:data=json.loads(script.string or script.get_text())
        except (TypeError,ValueError):continue
        stack=[data]
        while stack:
            node=stack.pop()
            if isinstance(node,dict):
                value=node.get('datePublished')
                if isinstance(value,str):candidates.append(value)
                stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
            elif isinstance(node,list):stack.extend(node)
    text=' '.join(soup.stripped_strings)
    m=re.search(r'Last\s+updated\s+on\s+(\d{1,2}\s+[A-Za-z]+\s+20\d{2})',text,re.I)
    if m:candidates.append(m.group(1))
    # Bandhan's first-party CMS renders the post date in visible copy as
    # "By <author> / September 11, 2026". Accept only that explicit marker.
    m=re.search(r'\bBy\b[^/]{0,120}/\s*([A-Za-z]+\s+\d{1,2},\s*20\d{2})',text,re.I)
    if m:candidates.append(m.group(1))
    parsed_url=urlparse(url) if url else None
    if parsed_url:
        host=(parsed_url.hostname or '').lower()
        path=unquote(parsed_url.path)
        if (host in ('www.sbimf.com','sbimf.com')
            and path.rstrip('/').lower()=='/learn-about-mutual-funds/2026-outlook'):
            m=re.search(r'\bPublished\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b',text,re.I)
            if m:candidates.append(f"{m.group(1)} {m.group(2)} {m.group(3)}")
        if (host in ('www.icicipruamc.com','icicipruamc.com')
            and path.startswith('/blob/sebi-repo/Advertisements/')
            and re.search(r'Monthly\s+Market\s+Outlook\.html$',path,re.I)):
            m=re.search(r'/Release\s+date\s+(\d{2}-\d{2}-20\d{2})/',path,re.I)
            if m:candidates.append(m.group(1))
    for raw in candidates:
        value=str(raw).strip()
        if re.match(r'^20\d{2}-\d{2}-\d{2}T',value):value=value[:10]
        try:day=iso(value)
        except ValueError:continue
        if day<=date.today().isoformat():return day
    return None


def bajaj_outlook_candidates(soup,source):
    """Parse exact first-party outlook cards from Bajaj's dedicated Outlook catalog."""
    if str(source.get('amc_match') or '').lower()!='bajaj':return []
    parsed=urlparse(source.get('url') or '')
    if ((parsed.hostname or '').lower()!='cobranding.bajajamc.com'
        or parsed.path.lower()!='/marketing/cobrandingmarketingmaterial'
        or parse_qs(parsed.query).get('LId')!=['51']):
        return []
    out=[];seen=set()
    for card in soup.select('div.bx-main'):
        heading=card.find('h5')
        link=card.select_one('a.lnk[href]')
        dated=card.select_one('span.dte')
        title=heading.get_text(' ',strip=True) if heading else ''
        target=link.get('href','').strip() if link else ''
        raw_date=dated.get_text(' ',strip=True) if dated else ''
        if not title or not target or not raw_date:continue
        if classify(title,target)!='market view':continue
        if not re.fullmatch(r'(?:EQUITY|DEBT|MARKET)\s+OUTLOOK(?:\s+.*)?',title,re.I):continue
        if not target.startswith(('https://','http://')):continue
        if not official_publication_url(target,'Bajaj'):continue
        try:day=iso(raw_date)
        except ValueError:continue
        if day>date.today().isoformat():continue
        key=(title,target,day)
        if key not in seen:out.append(key);seen.add(key)
    return out


def same_fund_title(value,family):
    # A scheme title, possibly followed by its parenthesized scheme description.
    # A holding mentioning the fund, an index fund, or a generic small-cap phrase
    # must never establish ownership of the containing report.
    normalize=lambda x:re.sub('[^a-z0-9]','',x.lower())
    return normalize(str(value).split('(')[0])==normalize(family)


def report_date(text):
    # Disclosure spreadsheets use period-ended labels and Excel date cells.
    from .report_parser import DATE,dated,normalize
    normalized=re.sub(r'([A-Za-z])(?=\d{4}\b)',r'\1 ',normalize(text))
    for m in re.finditer(r'(?:period ended|month ended|statement as on)\s*:?\s*('+DATE+r'|\d{4}-\d{2}-\d{2})',normalized,re.I):
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


def portfolio(family,day,positions,complete,source,h,*,replace_existing_partial=False):
    if not positions or not day: return None
    if any(not -100<=x["weight"]<=100 for x in positions): raise ValueError("Portfolio weights outside expected percentage units")
    if sum(x["weight"] for x in positions)>110: raise ValueError("Portfolio weight total suggests duplicated rows or wrong units")
    if any(x.get("quantity") is not None and x["quantity"]<0 for x in positions): raise ValueError("Portfolio quantity cannot be negative")
    with db.connect() as c:
        c.execute("INSERT OR IGNORE INTO portfolios(family,as_of,complete,source,hash,observed_at) VALUES(?,?,?,?,?,?)",(family,day,int(complete),source,h,db.now()))
        sid=c.execute("SELECT id FROM portfolios WHERE family=? AND as_of=? AND hash=? AND complete=?",(family,day,h,int(complete))).fetchone()[0]
        existing=c.execute("SELECT id,isin,name,asset_type,quantity FROM holdings WHERE snapshot_id=?",(sid,)).fetchall()
        if replace_existing_partial and not complete and existing:
            # Parser upgrades may recover additional explicit rows from the same
            # archived source hash. Replace only that exact retained partial
            # snapshot; complete snapshots and other source hashes are untouched.
            c.execute("DELETE FROM holdings WHERE snapshot_id=?",(sid,))
            existing=[]
        if not existing:
            c.executemany("INSERT INTO holdings(snapshot_id,isin,name,sector,weight,quantity,asset_type) VALUES(?,?,?,?,?,?,?)",
                          [(sid,x.get("isin"),x["name"],x.get("sector"),x["weight"],x.get("quantity"),x.get("asset_type","Equity")) for x in positions])
        elif any(x.get("quantity") is not None for x in positions):
            # Parser upgrades may discover a published quantity column for a
            # retained snapshot that was originally stored weight-only. Fill
            # only missing quantities; source hash/date/weights stay unchanged.
            for x in positions:
                q=x.get("quantity")
                if q is None:continue
                if x.get("isin"):
                    c.execute("UPDATE holdings SET quantity=? WHERE snapshot_id=? AND isin=? AND quantity IS NULL",
                              (q,sid,x["isin"]))
                else:
                    c.execute("""UPDATE holdings SET quantity=? WHERE snapshot_id=?
                      AND lower(trim(name))=lower(trim(?)) AND asset_type=? AND quantity IS NULL""",
                              (q,sid,x["name"],x.get("asset_type","Equity")))
    db.prune_portfolio_history(family)
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
        from .portfolio_parser import parse_sheet,owns_sheet
        full=parse_sheet(rows,formats,family)
        if full:
            if full['aum'] is not None:db.metric(family,'All','aum',full['day'],full['aum'],'INR crore',url,h)
            if full['complete']:
                portfolio(family,full['day'],full['positions'],True,url,h)
                count+=len(full['positions']);continue
            # Sundaram publishes one written-off illiquid holding with the
            # literal weight marker "#" and defines it as less than 0.01% of NAV.
            # Keep the exact numeric rows from the structured workbook as a
            # richer partial snapshot, but never invent a numeric weight for
            # the censored holding or promote the snapshot to complete.
            if (family=='Sundaram Small Cap Fund'
                and full.get('unknown_rows')==['Hindustan Dorr Oliver Ltd @']
                and full['positions']):
                portfolio(family,full['day'],full['positions'],False,url,h,replace_existing_partial=True)
                count+=len(full['positions']);continue
            if family=='Bandhan Small Cap Fund' and full.get('unknown_rows') and full['positions']:
                # Bandhan marks sub-0.01% holdings with a literal "$". Retain
                # every exact numeric row only when all parser-unknown holdings
                # are proven by the same sheet to be those censored rows.
                header_index=None;header=None
                for j,r in enumerate(rows[:35]):
                    cells=[str(v or '').lower() for v in r]
                    if any('isin' in v for v in cells) and any('%' in v and re.search(r'nav|aum',v) for v in cells):
                        header_index=j;header=cells;break
                censored=set()
                if header is not None:
                    ic=next((j for j,v in enumerate(header) if 'isin' in v),None)
                    nc=next((j for j,v in enumerate(header) if 'name' in v or 'instrument' in v or 'issuer' in v),None)
                    wc=next((j for j,v in enumerate(header) if '%' in v and re.search(r'nav|aum',v)),None)
                    if None not in (ic,nc,wc):
                        for r in rows[header_index+1:]:
                            if max(ic,nc,wc)>=len(r):continue
                            if str(r[wc] or '').strip()!=chr(36):continue
                            if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}',str(r[ic] or '').strip()):continue
                            censored.add(str(r[nc] or '').strip())
                if censored and set(full['unknown_rows'])==censored:
                    portfolio(family,full['day'],full['positions'],False,url,h,replace_existing_partial=True)
                    count+=len(full['positions']);continue
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
        if not owns_sheet(rows,header_index,family):continue
        def col(pred): return next((i for i,v in enumerate(header) if pred(v)),None)
        ic=col(lambda x:'isin' in x)
        nc=col(lambda x:'name' in x or 'instrument' in x or 'issuer' in x)
        if family=='Samco Small Cap Fund' and nc==0 and len(header)>2 and not header[1] and ic==2:nc=1
        wc=col(lambda x:('nav' in x or 'aum' in x or ('net' in x and 'asset' in x)) and ('%' in x or 'percent' in x))
        sc=col(lambda x:'industry' in x or 'sector' in x)
        qc=col(lambda x:'quantity' in x or bool(re.search(r'\bqty\b|no\.?\s*of\s*(?:shares|units)',x,re.I)))
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
            quantity=None
            if qc is not None and qc<len(row) and asset_type in ('Equity','Fund units') and str(row[qc] or '').strip():
                try:
                    candidate=number(row[qc])
                    if 0<=candidate<1e15:quantity=candidate
                except ValueError:pass
            positions.append({"name":str(row[nc]),"isin":isin,"weight":weight,"sector":str(row[sc] or '') if sc is not None else None,
                              'quantity':quantity,'asset_type':asset_type})
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
    for page_index,page in enumerate(reader.pages):
        text=page.extract_text() or ''
        owned=owns_page(text,family)
        full=None;partial=None
        if family=='Aditya Birla Sun Life Small Cap Fund':
            from .report_parser import absl_complete_portfolio
            full=absl_complete_portfolio(text)
        if family=='ICICI Prudential Small Cap Fund' and re.search(r'(?:Date\s+of\s+inception|Inception/Allotment\s+date)\s*:\s*18-Oct-(?:07|2007)',text,re.I):
            from .report_parser import icici_named_portfolio
            if page_index+1<len(reader.pages):
                next_text=reader.pages[page_index+1].extract_text() or ''
                partial=icici_named_portfolio(text,next_text)
        if family=='Jm Small Cap Fund':
            from .report_parser import jm_top25_portfolio
            partial=jm_top25_portfolio(text)
            if not partial:
                layout_text=page.extract_text(extraction_mode='layout') or ''
                if layout_text!=text:partial=jm_top25_portfolio(layout_text)
        if family=='Edelweiss Small Cap Fund':
            from .report_parser import edelweiss_top30_portfolio,edelweiss_top10_portfolio
            partial=edelweiss_top30_portfolio(text)
            if not partial and page_index+2<len(reader.pages):
                next_two='\n'.join((reader.pages[page_index+1].extract_text() or '',
                                     reader.pages[page_index+2].extract_text() or ''))
                partial=edelweiss_top10_portfolio(text,next_two)
        if family=='Pgim India Small Cap Fund':
            from .report_parser import pgim_complete_portfolio
            full=pgim_complete_portfolio(text)
        if family=='LIC Mf Small Cap Fund':
            from .report_parser import lic_complete_portfolio
            full=lic_complete_portfolio(text)
        if family=='HSBC Small Cap Fund':
            from .report_parser import hsbc_complete_portfolio
            full=hsbc_complete_portfolio(text)
        if family=='Groww Small Cap Fund':
            from .report_parser import groww_reconciled_portfolio
            partial=groww_reconciled_portfolio(text)
        if family=='Quant Small Cap Fund':
            from .report_parser import quant_top10_portfolio
            partial=quant_top10_portfolio(text)
            if not partial:
                layout_text=page.extract_text(extraction_mode='layout') or ''
                if layout_text!=text:partial=quant_top10_portfolio(layout_text)
        if family=='Trustmf Small Cap Fund':
            from .report_parser import trustmf_named_portfolio
            partial=trustmf_named_portfolio(text)
            if not partial:
                layout_text=page.extract_text(extraction_mode='layout') or ''
                if layout_text!=text:partial=trustmf_named_portfolio(layout_text)
        if family=='Union Small Cap Fund':
            from .report_parser import union_complete_portfolio
            full=union_complete_portfolio(text)
            if not full:
                layout_text=page.extract_text(extraction_mode='layout') or ''
                if layout_text!=text:full=union_complete_portfolio(layout_text)
        if family=='Bajaj Finserv Small Cap Fund':
            from .report_parser import bajaj_complete_portfolio,bajaj_top10_portfolio
            full=bajaj_complete_portfolio(text)
            if not full and page_index+1<len(reader.pages):
                next_text=reader.pages[page_index+1].extract_text() or ''
                partial=bajaj_top10_portfolio(text,next_text)
        if family=='Bank Of India Small Cap Fund':
            from .report_parser import boi_multicolumn_complete_portfolio,boi_complete_portfolio
            full=boi_multicolumn_complete_portfolio(text) or boi_complete_portfolio(text)
            if not full:
                layout_text=page.extract_text(extraction_mode='layout') or ''
                if layout_text!=text:full=boi_complete_portfolio(layout_text)
        if not owned and not full and not partial:continue
        facts=page_facts(text,family) if owned else []
        if family in ('Bank Of India Small Cap Fund','UTI Small Cap Fund') and not any(f['metric']=='aum' for f in facts):
            from .report_parser import layout_aum
            facts.extend(layout_aum(page.extract_text(extraction_mode='layout'),family,report_date(text)))
        for fact in facts:
            db.metric(family,fact['plan'],fact['metric'],fact['as_of'],fact['value'],fact['unit'],url,h)
        count+=len(facts)
        parsed=full or partial
        if parsed and parsed.get('benchmark') and not any(fact['metric']=='benchmark' for fact in facts):
            db.metric(family,'All','benchmark',parsed['day'],parsed['benchmark'],
                      parsed.get('benchmark_unit','Reported'),url,h)
            count+=1
        if full:
            portfolio(family,full['day'],full['positions'],True,url,h);count+=len(full['positions'])
            continue
        if partial:
            portfolio(family,partial['day'],partial['positions'],False,url,h);count+=len(partial['positions'])
            continue
        positions=equity_positions(text,family)
        if positions and facts:
            portfolio(family,facts[0]['as_of'],positions,False,url,h);count+=len(positions)
            continue
        # Holdings require a supported table layout. A generic trailing-number
        # parser can mix sector totals and performance rows into the portfolio.
    return count


def ingest_source(source):
    url=source["url"]
    reason=exclusion_reason(source['amc_match'],url,source['label'])
    if reason:return 'Excluded: '+reason
    families=source_families(source["amc_match"])
    if not families: return "No matching small-cap fund yet"
    if (str(source.get("amc_match") or "").lower()=="franklin"
        and url=="https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries"):
        from .franklin_communications import ingest as franklin_ingest
        return franklin_ingest()["detail"]
    if (str(source.get("amc_match") or "").lower()=="groww"
        and url=="https://www.growwmf.in/distributor/knowledge-hub/publications"):
        from .groww_communications import ingest as groww_ingest
        return groww_ingest()["detail"]
    if (str(source.get("amc_match") or "").lower()=="hsbc"
        and url.startswith("https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights")
        and "local-market-commentary" in unquote(url).lower()):
        from .hsbc_communications import ingest as hsbc_ingest
        return hsbc_ingest()["detail"]
    if (str(source.get("amc_match") or "").lower()=="kotak"
        and url=="https://www.kotakmf.com/monthly-market-update"):
        from .kotak_communications import ingest as kotak_ingest
        return kotak_ingest()["detail"]
    if (str(source.get("amc_match") or "").lower()=="pgim"
        and url=="https://www.pgimindia.com/mutual-funds"):
        from .pgim_communications import ingest as pgim_ingest
        return pgim_ingest()["detail"]
    if (str(source.get("amc_match") or "").lower()=="quant mutual"
        and url=="https://www.quantmutual.com/downloads/investment_outlook"):
        from .quant_communications import ingest as quant_ingest
        return quant_ingest()["detail"]
    can_crawl(url)
    direct=bool(re.search(r'\.(pdf|xlsx?|xml)(?:\?|$)',url,re.I))
    content,h,media_type=fetch(url,max_bytes=(25 if direct else 8)*1024*1024)
    direct=direct or content.startswith(b'%PDF')
    if direct:
        from .amc_reports import extract
        n=0;kind=classify(source['label'],url)
        for f in families:
            did=save_document(f['family'],source['label'],url,kind,'AMC',origin='AMC')
            doc_version(did,h);n+=extract(content,f['family'],url,h)
        gaps=0 if n or kind in ('scheme document','market view','unitholder letter') else 1
        return f'{n} extracted facts/holdings; 1 document archived; {gaps} download/parser gaps'
    soup=BeautifulSoup(content,"html.parser")
    links=candidate_links(soup,url)
    nlinks=0;narchive=0;errors=0;attempted=0;parsed=0;unrecognized=0
    last_attempt={r['url']:r['last'] for r in db.rows('SELECT url,MAX(fetched_at) last FROM fetches GROUP BY url')}
    for f in families:
        family=f["family"]
        # The source page itself is versioned, so changed facts can always be audited.
        # A dated monthly page explicitly titled Market Outlook/Market Update is
        # itself an AMC communication, not merely a crawl directory. Generic
        # directories (for example /market-update) remain source pages.
        page_kind=dated_communication_source_kind(source["label"],url)
        page_published=explicit_publication_date(content,media_type,url) if page_kind else None
        page_id=save_document(family,source["label"],url,page_kind or "source page","AMC",
                              published=page_published,origin="AMC")
        if page_kind:
            # Repair earlier rows that were saved as source-page/factsheet before
            # explicit communication titles took precedence over URL path words.
            with db.connect() as c:
                c.execute("""UPDATE documents SET kind=?,scope='AMC'
                  WHERE id=? AND origin='AMC'
                    AND kind IN ('source page','factsheet','disclosure')""",
                          (page_kind,page_id))
        doc_version(page_id,h)
        # Bajaj's dedicated Outlook catalog renders the real title/date next to a
        # generic "Download" link. Parse that card structure so the title, exact
        # first-party viewer URL and explicit date stay bound together.
        for title,target,published in bajaj_outlook_candidates(soup,source):
            did=save_document(family,title,target,'market view','AMC',
                              published=published,origin='AMC')
            nlinks+=1
            if attempted>=12:continue
            attempted+=1
            try:
                can_crawl(target)
                body,ch,typ=fetch(target)
                doc_version(did,ch);narchive+=1
            except Exception:
                errors+=1
        if "hdfcfund.com/explore/" in url: hdfc(soup,family,url,h)
        from .amc_metrics import parse_page
        parse_page(content,family,url,h)
        for target,title in sorted(links.items(),key=lambda item:last_attempt.get(item[0],'')):
            if target==url or not target.startswith(("http://","https://")): continue
            if not official_publication_url(target,source['amc_match']):continue
            if exclusion_reason(source['amc_match'],target,title):continue
            combined=unquote(title+' '+target)
            if re.search(r'small[\s_\-]*cap',combined,re.I) and re.search(r'\b(?:ETF|index[\s_\-]*fund)\b',combined,re.I):continue
            specific=bool(re.search(r"small[\s_\-]*cap",combined,re.I)) and not re.search(r"mid[\s_\-]*small",combined,re.I)
            # A scheme-specific page can label a UUID download simply "Latest
            # Monthly Portfolio". Keep it as a candidate; parser verifies ownership.
            if re.search(r'small[\s_\-]*cap',url,re.I) and re.search(r'latest.*(?:portfolio|factsheet)',title,re.I):specific=True
            link_kind=source_context_communication_kind(source,target,title)
            commentary=link_kind in ('market view','unitholder letter')
            download=bool(re.search(r"\.(?:pdf|xlsx?|xml)(?:\?|$)",target,re.I))
            omnibus=download and bool(re.search(r'factsheet|fact.sheet|fund.spectrum|fund.watch|monthly.portfolio|scheme.summary',combined,re.I)) and not re.search(r'large.cap|mid.cap|liquid.fund|debt.fund|flexi.cap|multi.cap',combined,re.I)
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
            did=save_document(family,title,target,link_kind or classify(title,target),
                              "Fund" if specific else "AMC",origin="AMC")
            nlinks+=1
            # Bound each page pass; remaining original links stay available, with archive status visible.
            if attempted>=12: continue
            attempted+=1
            try:
                can_crawl(target)
                body,ch,typ=fetch(target)
                doc_version(did,ch);narchive+=1
                if link_kind in ('market view','unitholder letter'):
                    published=explicit_publication_date(body,typ)
                    if published:
                        with db.connect() as c:
                            c.execute("""UPDATE documents SET published_at=COALESCE(published_at,?)
                              WHERE id=? AND origin='AMC'""",(published,did))
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
        # Retain the old source and archive for audit, but stop following a
        # discovered section that belongs to another AMC's schemes.
        for row in c.execute('SELECT id,amc_match,url,label FROM source_pages WHERE enabled=1').fetchall():
            reason=exclusion_reason(row['amc_match'],row['url'],row['label'])
            if (urlparse(row['url']).hostname or '').removeprefix('www.') in ('abakkusmutualfund.com','pgimindiamf.com','thewealthcompany.com'):
                reason='Superseded AMC domain; current official report pages are registered separately'
            if reason:c.execute("UPDATE source_pages SET enabled=0,status='Excluded',detail=? WHERE id=?",(reason,row['id']))
