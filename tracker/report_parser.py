"""Dated facts from an identified scheme page, independent of PDF rendering order.

No URL-derived dates, inferred TER, OCR guesses, or average/month-end substitution.
All extracted values are saved with the original document's content hash by caller.
"""
from __future__ import annotations
import re
from datetime import date, datetime

NUMBER = r'([0-9][0-9,]*(?:\.[0-9]+)?)'
DATE = r'(?:\d{1,2}(?:st|nd|rd|th)?[\s./-]+(?:[A-Za-z]+|\d{1,2})[\s,./-]+(?:\d{4}|\d{2})\b|[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})'


def normalize(text):
    text=text.replace('\u00a0',' ').replace('\u00ad','').replace('\u2011','-')
    text=re.sub(r'(?<=\d)\s+([.,])',r'\1',text)
    text=re.sub(r'\bA\s+ugust\b','August',text)
    text=re.sub(r'\bA\s+A\s+UM\b','AAUM',text)
    text=re.sub(r'\bA\s+UM\b','AUM',text)
    return text


def dated(value):
    value=re.sub(r'(?<=\d)(st|nd|rd|th)\b','',value,flags=re.I)
    value=re.sub(r'\s+([,./-])',r'\1',value)
    value=re.sub(r'\s+',' ',value.strip()).replace('Sept','Sep')
    for fmt in ('%d.%m.%Y','%d.%m.%y','%d/%m/%Y','%d-%m-%Y','%d-%b-%Y','%d-%b-%y','%d-%B-%Y',
                '%d %B %Y','%d %b %Y','%d %B, %Y','%d %b, %Y',
                '%B %d, %Y','%b %d, %Y','%B %d %Y','%b %d %Y'):
        try:
            d=datetime.strptime(value,fmt).date()
            return d.isoformat() if date(1990,1,1)<=d<=date.today() else None
        except ValueError:pass
    return None


def owns_page(text,family):
    """An exact scheme heading must be followed closely by its scheme description."""
    if family=='Mirae Asset Small Cap Fund' and re.search(r'Equity Snapshot',text,re.I):return False
    compact=lambda s:re.sub('[^a-z0-9]','',s.lower())
    lines=normalize(text).splitlines()
    if family=='Abakkus Small Cap Fund':
        # Abakkus puts the mandate on the preceding page; this is an exact,
        # dedicated scheme-details heading with a verified labelled layout.
        heading=any(compact(line)==compact(family+' Details') for line in lines)
        if heading and all(label in text for label in ('Month End AUM','Plans & Options','Base Expense Ratio','Source: Internal. Data as on')):return True
    for i,line in enumerate(lines):
        # Up to three lines accommodate titles split over lines (Union, SBI).
        for span in (1,2,3):
            title=' '.join(lines[i:i+span]).split('(')[0].strip()
            if compact(title)!=compact(family):continue
            nearby=' '.join(lines[i:i+span+7])
            if re.search(r'An open[\s-]*ended[\s\S]{0,110}?equity[\s\S]{0,110}?small[\s-]*cap',nearby,re.I):return True
    return False


def page_facts(text,family):
    text=normalize(text)
    if not owns_page(text,family):return []
    flat=re.sub(r'\s+',' ',text)
    # AUM's own explicit date has priority over a nearby NAV business-day date.
    report=None
    if family=='Motilal Oswal Small Cap Fund':
        m=re.search(r'\bLatest AUM\s*\(\s*('+DATE+r')\s*\)',flat,re.I)
        if m:
            report=dated(m.group(1))
            if not report:return []
    for label in (r'(?:month end )?(?:aum|assets under management\s*\(aum\))',r'Details',r'Data',r'Portfolio',r'Report',r'Factsheet',r'NAV'):
        if report:break
        m=re.search(r'\b'+label+r'\s*(?:#|\((?!as )[^)]*\))?\s*\(?(?:as (?:on|of|at))\s*[:(]?\s*('+DATE+r')',flat,re.I)
        if m:
            report=dated(m.group(1))
            # A future explicit report must not fall back to an older NAV date.
            if not report:return []
            break
    if not report and family=='Quant Small Cap Fund':
        m=re.search(r'\bAUM\s*\(('+DATE+r')\)',flat,re.I)
        if m:report=dated(m.group(1))
    if not report:return []
    out=[]
    def add(key,value,plan='All',day=report,unit='INR crore'):
        out.append(dict(metric=key,value=value,plan=plan,as_of=day,unit=unit))
    currency=r'(?:INR|Rs\.?|₹|`)?\s*'
    unit=r'(?:Cr(?:ore)?s?\.?)\b'
    # Patterns stop at the number and require crore units in the same label/value.
    patterns=[
        r'\b(?:Month\s*End(?:\s+AUM)?|Closing\s*AUM|Total\s*AUM)\s*(?:\(₹\))?\s*[:#-]?\s*'+currency+NUMBER+r'\s*'+unit,
        r'\bMonth end Assets Under Management\s*\(AUM\)\s*#?\s*'+currency+NUMBER+r'\s*'+unit,
        r'\bAUM\s*\(?as\s+(?:on|of)\s*('+DATE+r')\s*\)?\s*[:#-]?\s*'+currency+NUMBER+r'\s*'+unit,
        r'\bAUM\s+as\s+(?:on|of)\s*'+DATE+r'\s*\(in\s*(?:₹|Rs\.?)?\s*Crores?\)\s*Month End AUM\s*'+NUMBER,
        r'\bNet AUM\s*\(Cr\.\)\s*'+NUMBER,
    ]
    for index,pattern in enumerate(patterns):
        m=re.search(pattern,flat,re.I)
        if m:
            value=float(m.group(2 if index==2 else 1).replace(',',''))
            if 0<value<10_000_000:add('aum',value)
            break
    avg=re.search(r'\bMonthly (?:(?:Average|AVG) (?:AUM|Assets Under Management\s*\(AAUM\))|AAUM)\s*[:#-]?\s*'+currency+NUMBER+r'\s*'+unit,flat,re.I)
    if avg:add('average_aum',float(avg.group(1).replace(',','')))
    if family=='Abakkus Small Cap Fund':
        m=re.search(currency+NUMBER+r'\s*'+unit+r'\s+Month End AUM',flat,re.I)
        if m:add('aum',float(m.group(1).replace(',','')))
        m=re.search(r'Regular:\s*(\d+(?:\.\d+)?)%\s+Direct:\s*(\d+(?:\.\d+)?)%\s+Base Expense Ratio',flat,re.I)
        if m:
            for plan,v in zip(('Regular','Direct'),m.groups()):
                if 0<=float(v)<=5:add('base_expense_ratio',float(v),plan,unit='% p.a.')
    if family=='Bank Of India Small Cap Fund':
        for label,key in [('LATEST AUM','aum'),('AVERAGE AUM','average_aum')]:
            m=re.search(label+r'\s*'+currency+NUMBER+r'\s*'+unit,flat,re.I)
            if m:add(key,float(m.group(1).replace(',','')))
    if family=='Motilal Oswal Small Cap Fund':
        for label,key in [('Latest AUM','aum'),('Monthly AAUM','average_aum')]:
            m=re.search(r'\b'+label+r'\s*\(\s*('+DATE+r')\s*\)\s*\(in Rs Crs\.\)\s*'+NUMBER,flat,re.I)
            if m and dated(m.group(1))==report:add(key,float(m.group(2).replace(',','')))
    if family=='SBI Small Cap Fund' and re.search(r'Fund Size\s*`\s*in Cr\.\s*\$\s*in Mn\.',flat,re.I):
        # The first column is INR crore; the second column is USD millions.
        for label,key in [('Month end AUM','aum'),(r'Monthly Avg\. AUM','average_aum')]:
            m=re.search(label+r'\s*'+NUMBER+r'\s+'+NUMBER,flat,re.I)
            if m:add(key,float(m.group(1).replace(',','')))
        m=re.search(r'Expense Ratio Plan Regular Direct TER\s+'+NUMBER+r'\s+'+NUMBER+r'\s+BER\s+'+NUMBER+r'\s+'+NUMBER,flat,re.I)
        if m:
            for (key,plan),v in zip([('ter','Regular'),('ter','Direct'),('base_expense_ratio','Regular'),('base_expense_ratio','Direct')],m.groups()):
                if 0<=float(v)<=5:add(key,float(v),plan,unit='% p.a.')
    if family=='Quant Small Cap Fund':
        for label,key in [('AUM','aum'),('AAUM','average_aum')]:
            m=re.search(r'\b'+label+r'\s*\('+DATE+r'\)\s*:\s*Rs\.\s*'+NUMBER+r'\s*Cr',flat,re.I)
            if m:add(key,float(m.group(1).replace(',','')))
    if family=='Samco Small Cap Fund':
        m=re.search(r'\bAUM as on '+DATE+r'\s+AAUM for Month of [A-Za-z]+-\d{4}\s+'+NUMBER+r'\s+Crs\s+'+NUMBER+r'\s+Crs',flat,re.I)
        if m:
            add('aum',float(m.group(1).replace(',','')))
            add('average_aum',float(m.group(2).replace(',','')))
    if family=='Bajaj Finserv Small Cap Fund':
        m=re.search(r'AUM \(IN CR\):\s*Month end AUM - INR '+NUMBER,flat,re.I)
        if m:add('aum',float(m.group(1).replace(',','')))
    if family=='Quantum Small Cap Fund' and re.search(r'AUM\s*₹\s*\(In Crores\)',flat,re.I):
        for label,key in [('Absolute AUM','aum'),(r'Average AUM\*?','average_aum')]:
            m=re.search(label+r'\s*:\s*'+NUMBER,flat,re.I)
            if m:add(key,float(m.group(1).replace(',','')))
        for m in re.finditer(r'(Direct|Regular) Plan\s*[–-]\s*Total TER\s*(\d+(?:\.\d+)?)%',flat,re.I):
            key='ter_excluding_transaction_cost' if re.search(r'Total Expense ratio inclusive of transaction cost',flat,re.I) else 'ter'
            if 0<=float(m.group(2))<=5:add(key,float(m.group(2)),m.group(1).title(),unit='% p.a.')
    # Never call an ambiguous "expense ratio" TER, especially after BER changes.
    if family=='UTI Small Cap Fund':
        m=re.search(r'Month-end Total Expense Ratio\s*\(%\)\*?[\s\S]{0,1000}?Regular\s*:\s*(\d+(?:\.\d+)?)\s+Direct\s*:\s*(\d+(?:\.\d+)?)',flat,re.I)
        if m:
            for plan,v in zip(('Regular','Direct'),m.groups()):
                if 0<=float(v)<=5:add('ter',float(v),plan,unit='% p.a.')
    for heading,key in [(r'Base Expense Ratio(?:\s*\(BER\))?','base_expense_ratio'),(r'Total Expense Ratio(?:\s*\(TER\))?','ter')]:
        for block in re.finditer(heading+r'\s*[:*^-]?\s*([^\n]*(?:\n[^\n]*){0,5})',text,re.I):
            s=block.group(1)
            for plan in ('Regular','Direct'):
                m=re.search(r'\b'+plan+r'(?:/Other than Direct)?(?:\s+Plan)?\s*(?:\(%\))?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?',s,re.I)
                if m and 0<=float(m.group(1))<=5:add(key,float(m.group(1)),plan,unit='% p.a.')
    for m in re.finditer(r'BER / TER \((Regular|Direct) Plan\)\s*:\s*(\d+(?:\.\d+)?)%\s*/\s*(\d+(?:\.\d+)?)%',flat,re.I):
        for key,v in zip(('base_expense_ratio','ter'),m.groups()[1:]):
            if 0<=float(v)<=5:add(key,float(v),m.group(1).title(),unit='% p.a.')
    # DSP's footnote explicitly says the month-end expense ratio is BER.
    if family=='DSP Small Cap Fund' and re.search(r'\*\*Base Expense Ratio',text,re.I):
        m=re.search(r'Month End Expense\s+Ratio\*\*\s+Regular Plan\s*:\s*(\d+\.\d+)%\s+Direct Plan\s*:\s*(\d+\.\d+)%',text,re.I)
        if m:
            for plan,v in zip(('Regular','Direct'),m.groups()):add('base_expense_ratio',float(v),plan,unit='% p.a.')
    for pattern,key in [
        (r'(?:^|\n)\s*(?:#\s*)?(?:(?:AMFI\s+Tier\s*1|Primary|Scheme|First\s+Tier)\s+)?Benchmark(?:\s+Index|\s+Name)?\s*[:#\-\n ]\s*([^\n]+)','benchmark'),
        (r'(?:^|\n)(?:Date of Allotment|Inception Date)\s*[:\n]\s*([^\n]+)','fund_launch'),
    ]:
        m=re.search(pattern,text,re.I)
        if m:
            v=m.group(1).strip()
            if key=='benchmark':
                # Keep only the explicitly labelled index name. Factsheets often
                # append riskometer/footnote text on the same extracted line.
                recognized=[
                    r'(?:Nifty|NIFTY)\s+Smallcap\s+250(?:\s+Index)?(?:\s*\(TRI\)|\s+TRI)?',
                    r'(?:S&P\s+)?BSE\s+250\s+Small\s*Cap(?:\s+Index)?(?:\s*\(TRI\)|\s+TRI)?',
                    r'(?:S&P\s+)?BSE\s+Small\s*Cap\s+250(?:\s+Index)?(?:\s*\(TRI\)|\s+TRI)?',
                    r'CRISIL[^\n:;|]{1,100}?(?:TRI|Index)',
                ]
                index=next((x.group(0).strip() for pattern in recognized if (x:=re.search(pattern,v,re.I))),None)
                if index:add(key,index,unit='Reported')
            elif key=='fund_launch' and dated(v):add(key,dated(v),unit='Reported')
    if family=='SBI Small Cap Fund' and re.search(r'Benchmark BSE 250 Small Cap\s+Index TRI',text):
        for fact in out:
            if fact['metric']=='benchmark':fact['value']='BSE 250 Small Cap Index TRI'
    # Overlapping verified labels may identify the same fact.
    return list({tuple(sorted(f.items())): f for f in out}.values())



def bajaj_complete_portfolio(text):
    """Fully reconcile Bajaj Finserv Small Cap's published monthly portfolio."""
    normalized=normalize(text)
    if not re.search(r'(?:^|\n)\s*Bajaj\s+Finserv\s+Small\s+Cap\s+Fund\s*(?:\n|$)',normalized,re.I):return None
    if not re.search(r'An\s+open\s+ended\s+equity\s+scheme\s+predominantly\s+investing\s+in\s+small\s+cap\s+stocks',normalized,re.I):return None
    if not re.search(r'Scheme\s+Category\s*:\s*Small\s+Cap\s+Fund',normalized,re.I):return None
    heading=re.search(r'PORTFOLIO\s*\(\s*as\s+on\s*('+DATE+r')\s*\)',normalized,re.I)
    day=dated(heading.group(1)) if heading else None
    if not day:return None

    lines=[normalize(x).strip() for x in text.splitlines()]
    total_index=None;equity_total=None;repo=None;cash=None;grand=None
    for i,line in enumerate(lines):
        m=re.fullmatch(r'Equities\s+(-?\d+(?:\.\d+)?)\s*%',line,re.I)
        if not m:continue
        window='\n'.join(lines[i:min(len(lines),i+7)])
        rm=re.search(r'(?:^|\n)Reverse\s+Repo\s*/\s*TREPS\s+(-?\d+(?:\.\d+)?)\s*%',window,re.I)
        cm=re.search(r'(?:^|\n)Cash\s*(?:&|and)\s*Cash\s+Equivalent(?:s)?\s+(-?\d+(?:\.\d+)?)\s*%',window,re.I)
        gm=re.search(r'(?:^|\n)Grand\s+Total\s+(-?\d+(?:\.\d+)?)\s*%',window,re.I)
        if rm and cm and gm:
            total_index=i;equity_total=float(m.group(1));repo=float(rm.group(1));cash=float(cm.group(1));grand=float(gm.group(1))
            break
    if total_index is None or abs(grand-100)>.03:return None
    if not all(-100<=x<=100 for x in (equity_total,repo,cash)):return None
    if abs((equity_total+repo+cash)-grand)>.03:return None

    positions=[]
    for line in reversed(lines[:total_index]):
        m=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)\s*%',line)
        if not m:
            if positions:break
            continue
        label=m.group(1).strip();weight=float(m.group(2))
        if not 0<=weight<=100:return None
        company=re.match(r'(.+?\b(?:Ltd\.?|Limited))(?=\s|$)',label,re.I)
        name=(company.group(1) if company else label).strip()
        if not name:return None
        positions.append({'name':name,'isin':None,'sector':None,'weight':weight,'asset_type':'Equity'})
    positions.reverse()
    if not positions:return None
    tolerance=max(.08,.011*len(positions))
    if abs(sum(x['weight'] for x in positions)-equity_total)>tolerance:return None
    if len({x['name'].lower() for x in positions})!=len(positions):return None
    positions.append({'name':'Reverse Repo / TREPS','isin':None,'sector':None,'weight':repo,'asset_type':'Money market'})
    positions.append({'name':'Cash & Cash Equivalent','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    return {'day':day,'positions':positions}

def equity_positions(text,family):
    """Partial equity-only tables; exclude sector totals and all aggregate positions."""
    if not owns_page(text,family):return []
    text=normalize(text)
    # Explicitly supported layouts. Never treat arbitrary performance rows as holdings.
    if family not in ('Canara Robeco Small Cap Fund','DSP Small Cap Fund','Invesco India Small Cap Fund','Quantum Small Cap Fund','Mirae Asset Small Cap Fund','SBI Small Cap Fund'):return []
    start=re.search(r'Name of (?:the )?Instrument',text,re.I)
    if family=='Invesco India Small Cap Fund':start=re.search(r'Company % of Net\s+Assets',text,re.I)
    if family=='Mirae Asset Small Cap Fund':start=re.search(r'Portfolio Top 10 Holdings',text,re.I)
    if family=='SBI Small Cap Fund' and re.search(r'Net% To\s+AUM',text):start=re.search(r'EQUITY SHARES',text)
    if not start:return []
    section=re.split(r'TOP 10 INDUSTRIES|RISKOMETER|SIP Performance|Lumpsum Performance|Allocation - Top 10 Sectors|TREASURY BILLS',text[start.end():],flags=re.I)[0]
    positions=[];pending='';sector=None
    for line in section.splitlines():
        line=line.strip().lstrip('\uf03d\uf0fc• ').strip()
        ending=r'%?' if family in ('Invesco India Small Cap Fund','SBI Small Cap Fund') else '%'
        m=re.fullmatch(r'(.+?)\s+(?:[LMS]\s+)?(-?\d+(?:\.\d+)?)'+ending,line)
        if not m:
            if family=='SBI Small Cap Fund':
                if line.isupper():sector=line;pending=''
                elif re.search('Company/|AUM|Issuer Rating',line):pending=''
                else:pending=line
                continue
            pending=line if re.search(r'Company|Services|Industries|Limited|Bank|Corporation',line,re.I) else ''
            continue
        name=m.group(1);weight=float(m.group(2))
        if family=='SBI Small Cap Fund' and pending:name=pending+' '+name
        if name in ('Ltd','Ltd.','Limited') and pending:name=pending+' '+name
        pending=''
        if not re.search(r'\b(?:Ltd\.?|Limited)\b',name,re.I):
            sector=name if not re.search(r'Equit|Total|Market|Cash|TREPS',name,re.I) else None
            continue
        name=re.sub(r'\s+[LMS]$','',name).strip()
        if 0<=weight<=20:positions.append({'name':name,'weight':weight,'sector':sector,'asset_type':'Equity'})
    # Duplicate rows indicate ambiguous extraction, rather than a second holding.
    if len({x['name'] for x in positions})!=len(positions) or sum(x['weight'] for x in positions)>100.5:return []
    return positions




def hsbc_complete_portfolio(text):
    """Fully reconcile HSBC Small Cap's monthly factsheet table."""
    normalized=normalize(text)
    if not owns_page(normalized,'HSBC Small Cap Fund'):return None
    total_match=re.search(r'Total Net Assets as on\s+('+DATE+r')\s+(-?\d+(?:\.\d+)?)%',normalized,re.I)
    if not total_match:return None
    day=dated(total_match.group(1));grand=float(total_match.group(2))
    if not day or abs(grand-100)>.03:return None
    start=re.search(r'Issuer\s+Market Cap/\s*\n?\s*Ratings\s+%\s*to\s*Net\s*Assets',normalized,re.I)
    if not start:return None
    section=normalized[start.end():total_match.start()]
    lines=[re.sub(r'\s+',' ',x).strip() for x in section.splitlines() if x.strip()]
    positions=[];sector=None;sector_total=None;sector_positions=[]
    def finish_sector():
        nonlocal sector,sector_total,sector_positions
        if sector is None:return True
        if not sector_positions:return False
        tolerance=max(.04,.006*len(sector_positions))
        if abs(sum(x['weight'] for x in sector_positions)-sector_total)>tolerance:return False
        positions.extend(sector_positions)
        sector=None;sector_total=None;sector_positions=[]
        return True
    cash_total=None
    for line in lines:
        if re.fullmatch(r'Issuer Market Cap/\s*Ratings % to Net Assets',line,re.I):continue
        m=re.fullmatch(r'(.+?)\s+(Small Cap|Mid Cap|Large Cap)\s+(-?\d+(?:\.\d+)?)%',line,re.I)
        if m:
            if sector is None:return None
            weight=float(m.group(3))
            if not 0<=weight<=20:return None
            sector_positions.append({'name':m.group(1).strip(),'isin':None,'sector':sector,'weight':weight,'asset_type':'Equity'})
            continue
        m=re.fullmatch(r'Cash Equivalent\s+(-?\d+(?:\.\d+)?)%',line,re.I)
        if m:
            if not finish_sector():return None
            cash_total=float(m.group(1));break
        m=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)%',line)
        if m:
            if not finish_sector():return None
            sector=m.group(1).strip();sector_total=float(m.group(2));sector_positions=[]
    if cash_total is None or not positions:return None
    tail=normalized[normalized.find('Cash Equivalent',start.end()):total_match.start()]
    repo=re.search(r'TREPS\*?\s+(-?\d+(?:\.\d+)?)%',tail,re.I)
    cash=re.search(r'Net Current Assets:\s*(-?\d+(?:\.\d+)?)%',tail,re.I)
    if not repo or not cash:return None
    repo_weight=float(repo.group(1));cash_weight=float(cash.group(1))
    if abs((repo_weight+cash_weight)-cash_total)>.03:return None
    equity=sum(x['weight'] for x in positions)
    if abs((equity+cash_total)-grand)>max(.08,.006*len(positions)):return None
    if len({x['name'].lower() for x in positions})!=len(positions):return None
    positions.append({'name':'TREPS','isin':None,'sector':None,'weight':repo_weight,'asset_type':'Money market'})
    positions.append({'name':'Net Current Assets','isin':None,'sector':None,'weight':cash_weight,'asset_type':'Cash and net current assets'})
    return {'day':day,'positions':positions}

def lic_complete_portfolio(text):
    """Fully reconcile LIC MF Small Cap's portfolio page from the monthly factsheet."""
    normalized=normalize(text)
    scheme_ok=bool(re.search(
        r'Scheme\s+Type\s*:\s*Small\s+Cap\s+Fund\s*-\s*An\s+open[\s-]*ended\s+equity\s+scheme\s+predominantly\s+investing\s+in\s+small\s+cap\s+stocks',
        normalized,re.I))
    benchmark_ok=bool(re.search(r'First\s+Tier\s+Benchmark\s*:\s*Nifty\s+Smallcap\s+250\s*-?\s*TRI',normalized,re.I))
    inception_ok=bool(re.search(r'Inception/Allotment\s+Date\s*:\s*June\s+21,?\s+2017',normalized,re.I))
    if not (scheme_ok and benchmark_ok and inception_ok):return None
    m=re.search(r'PORTFOLIO\s+as\s+on\s+(\d{1,2}/\d{1,2}/\d{4})',normalized,re.I)
    day=dated(m.group(1)) if m else None
    if not day:return None
    lines=[normalize(x).strip() for x in text.splitlines()]
    start=next((i for i,x in enumerate(lines)
                if re.fullmatch(r'Company\s+%\s+of\s+NAV',x,re.I)
                and any(re.fullmatch(r'Equity\s+Holdings',y,re.I) for y in lines[i+1:i+4])),None)
    if start is None:return None
    positions=[];sector=None;equity_total=None;cash=None;grand=None;pending=[]
    ignore=re.compile(r'^(?:Company\s+%\s+of\s+NAV|Equity\s+Holdings|Top\s+10\s+holdings)$',re.I)
    for line in lines[start+1:]:
        if not line:continue
        if ignore.fullmatch(line):
            pending=[];continue
        if re.search(r'Please\s+refer\s+Notice-cum-Addendum|SCHEME\s+PERFORMANCE',line,re.I):break
        numeric_only=re.fullmatch(r'(-?\d+(?:\.\d+)?)\s*%',line)
        row=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)\s*%',line)
        if numeric_only:
            if not pending:continue
            label=' '.join(pending).strip();value=float(numeric_only.group(1));pending=[]
        elif row:
            label=' '.join(pending+[row.group(1).strip()]).strip();value=float(row.group(2));pending=[]
        else:
            pending.append(line)
            if len(pending)>4:pending=pending[-4:]
            continue
        label=re.sub(r'^Top\s+10\s+holdings\s*','',label,flags=re.I).strip()
        key=re.sub(r'[^a-z]','',label.lower())
        if key=='equityholdingstotal':equity_total=value;sector=None;continue
        if key in ('cashotherreceivablestotal','cashandotherreceivablestotal'):cash=value;sector=None;continue
        if key=='grandtotal':grand=value;break
        if re.search(r'\b(?:Ltd\.?|Limited)\b',label,re.I):
            if not 0<=value<=20:return None
            positions.append({'name':label,'isin':None,'sector':sector,'weight':value,'asset_type':'Equity'})
        else:
            sector=label
    if None in (equity_total,cash,grand) or abs(grand-100)>.02:return None
    if len(positions)<20:return None
    if abs(sum(x['weight'] for x in positions)-equity_total)>max(.08,.011*len(positions)):return None
    if abs((equity_total+cash)-grand)>.03:return None
    positions.append({'name':'Cash & Other Receivables','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    if len({(x['name'],x['asset_type']) for x in positions})!=len(positions):return None
    return {'day':day,'positions':positions}


def pgim_complete_portfolio(text):
    """Fully reconcile PGIM India Small Cap's monthly factsheet portfolio page."""
    normalized=normalize(text)
    compact=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    title_ok=('pgimindiasmallcapfund' in compact(normalized) or
              'smallcapfundpgimindia' in compact(normalized))
    mandate_ok=bool(re.search(r'Small\s+Cap\s+Fund\s*-\s*An\s+open[\s-]*ended\s+equity\s+scheme\s+predominantly\s+investing\s+in\s+small\s+cap\s+stocks',normalized,re.I))
    if not title_ok or not mandate_ok:return None
    m=re.search(r'Details\s+as\s+on\s+('+DATE+r')',normalized,re.I)
    day=dated(m.group(1)) if m else None
    if not day:return None
    lines=[normalize(x).strip() for x in text.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.search(r'Issuer\s+%\s+to\s+Net',x,re.I)),None)
    if start is None:return None
    positions=[];sector=None;equity_total=None;debt_total=None;cash=None;grand=None
    for line in lines[start+1:]:
        if re.search(r'^SMALL CAP FUND$',line,re.I):break
        row=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)\s*(?:SOVEREIGN)?',line,re.I)
        if not row:continue
        label=row.group(1).strip();value=float(row.group(2))
        key=re.sub(r'[^a-z]','',label.lower())
        if key=='equityholdingstotal':equity_total=value;sector=None;continue
        if key=='governmentbondandtreasurybill':debt_total=value;sector='Government Bond And Treasury Bill';continue
        if key=='treasurybill':sector='Treasury Bill';continue
        if key=='cashcurrentassets':cash=value;sector=None;continue
        if key=='total':grand=value;break
        if re.search(r'portfolio classification|large cap|mid cap|small cap|cash and tbill|debt|invts|etf|reits',label,re.I):continue
        if re.search(r'^\d+\s+Days\s+Tbill\b',label,re.I):
            positions.append({'name':label,'isin':None,'sector':'Treasury Bill','weight':value,'asset_type':'Debt'});continue
        if re.search(r'\b(?:Ltd\.?|Limited)\b',label,re.I):
            positions.append({'name':label,'isin':None,'sector':sector,'weight':value,'asset_type':'Equity'})
        else:
            sector=label
    equity_positions=[x for x in positions if x['asset_type']=='Equity']
    debt_positions=[x for x in positions if x['asset_type']=='Debt']
    if None in (equity_total,debt_total,cash,grand) or abs(grand-100)>.02:return None
    if len(equity_positions)<20:return None
    if abs(sum(x['weight'] for x in equity_positions)-equity_total)>max(.08,.011*len(equity_positions)):return None
    if abs(sum(x['weight'] for x in debt_positions)-debt_total)>.02:return None
    if abs((equity_total+debt_total+cash)-grand)>.03:return None
    positions.append({'name':'Cash & Current Assets','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    if len({(x['name'],x['asset_type']) for x in positions})!=len(positions):return None
    return {'day':day,'positions':positions}




def absl_complete_portfolio(text):
    """Reconcile ABSL Small Cap's factsheet portfolio page to 100%."""
    normalized=normalize(text)
    family='Aditya Birla Sun Life Small Cap Fund'
    if not owns_page(normalized,family):return None
    m=re.search(r'Portfolio\s+Holdings\s+as\s+on\s+('+DATE+r')',normalized,re.I)
    day=dated(m.group(1)) if m else None
    if not day:return None

    lines=[re.sub(r'\s+',' ',x).strip() for x in normalized.splitlines()]
    start=next((i for i,x in enumerate(lines)
                if re.search(r'Sector/Issuer\s+Name',x,re.I)),None)
    if start is None:return None

    positions=[];sectors=[];cash=None;grand=None
    for line in lines[start+1:]:
        if not line:continue
        gm=re.fullmatch(r'Grand\s+Total\s+(-?\d+(?:\.\d+)?)\s*%',line,re.I)
        if gm:
            grand=float(gm.group(1));break
        cm=re.fullmatch(r'Net\s+Cash\s+and\s+Cash\s+Equivalent\s+(-?\d+(?:\.\d+)?)\s*%',line,re.I)
        if cm:
            cash=float(cm.group(1));continue
        row=re.fullmatch(r'(?:[●•]\s*)?(.+?)\s+(-?\d+(?:\.\d+)?)\s*%',line)
        if not row:continue
        label=row.group(1).strip();value=float(row.group(2))
        if re.search(r'^(?:% of|Total AUM|Derivatives|Net AUM|Equity\s*&\s*Equity Related)    """Parse Edelweiss Small Cap's published Top 30 list as a partial snapshot.

    The factsheet also publishes an independent Top-10 aggregate. Reconcile the
    first ten extracted holdings to that total before retaining any rows.
    """
    normalized=normalize(text)
    family='Edelweiss Small Cap Fund'
    if not owns_page(normalized,family):return None

    m=(re.search(r'Data\s+as\s+on\s+('+DATE+r')',normalized,re.I)
       or re.search(r'Top\s+(?:30\s+)?Holdings\s+as\s+on\s+('+DATE+r')',normalized,re.I)
       or re.search(r'\(\s*As\s+on\s+('+DATE+r')\s*\)',normalized,re.I))
    day=dated(m.group(1)) if m else None
    if not day:return None

    t=re.search(r'Top\s*10\s*(?:stocks|holdings)[^0-9]{0,12}'+NUMBER+r'\s*%',normalized,re.I)
    if not t:return None
    top10=float(t.group(1).replace(',',''))
    if not 5<=top10<=60:return None

    lines=[re.sub(r'\s+',' ',x).strip() for x in normalized.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.fullmatch(r'Company\s+Name\s+Allocation',x,re.I)),None)
    if start is None:return None
    positions=[]
    for line in lines[start+1:]:
        if re.fullmatch(r'Company\s+Name\s+Allocation',line,re.I):continue
        m=re.fullmatch(r'(.+?)\s+(\d+(?:\.\d+)?)\s*%',line)
        if not m:
            if len(positions)>=30:break
            continue
        name=m.group(1).strip();weight=float(m.group(2))
        if re.search(r'Benchmark|Fund|Large\s+Cap|Mid\s+Cap|Small\s+Cap|Net\s+Equity',name,re.I):continue
        if not 0<weight<10:return None
        positions.append({'name':name,'isin':None,'sector':None,'weight':weight,'asset_type':'Equity'})
        if len(positions)==30:break

    if len(positions)!=30:return None
    if len({x['name'].lower() for x in positions})!=30:return None
    if abs(sum(x['weight'] for x in positions[:10])-top10)>.04:return None
    total=sum(x['weight'] for x in positions)
    if not 35<=total<=85:return None
    return {'day':day,'positions':positions}


def boi_complete_portfolio(text):
    """Reconcile Bank of India Small Cap's published monthly portfolio."""
    normalized=normalize(text)
    family='Bank Of India Small Cap Fund'
    if not owns_page(normalized,family):return None
    m=re.search(r'All\s+data\s+as\s+on\s+('+DATE+r')',normalized,re.I)
    day=dated(m.group(1)) if m else None
    if not day:return None

    lines=[re.sub(r'\s+',' ',x).strip() for x in normalized.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.search(r'Portfolio\s+Holdings',x,re.I)),None)
    end=next((i for i,x in enumerate(lines) if start is not None and i>start and re.fullmatch(r'INVESTMENT\s+OBJECTIVE',x,re.I)),None)
    if start is None or end is None:return None
    rows=lines[start:end]

    def numeric(line):
        q=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)\s*%?',line)
        if not q:return None
        return q.group(1).strip(),float(q.group(2))

    reserved=re.compile(
        r'^(?:Portfolio Holdings|Industry/ Rating|Assets|EQUITY HOLDINGS|CASH\s*&\s*CASH EQUIVALENT|'
        r'GOVERNMENT BOND AND|TREASURY BILL|MONEY MARKET INSTRUMENTS|MCAP Categorization|Mcap Category|'
        r'PORTFOLIO DETAILS|GRAND TOTAL|Total|Indicates Top 10 Equity Holdings)',re.I)

    def sectorish(label):
        letters=re.sub(r'[^A-Za-z]','',label)
        return bool(letters) and label==label.upper() and not re.search(r'\b(?:LTD|LIMITED)\b',label,re.I)

    positions=[];sector_totals=[]
    cash_positions=[];debt_positions=[];money_positions=[]
    debt_subtotals=[];money_subtotals=[]
    equity_total=None;cash_total=None;grand=None
    mode='equity';subsection=None;i=0

    while i<len(rows):
        line=rows[i].strip();i+=1
        if not line:continue
        if re.fullmatch(r'EQUITY HOLDINGS',line,re.I):
            mode='equity';subsection=None;continue
        if re.fullmatch(r'CASH\s*&\s*CASH EQUIVALENT',line,re.I):
            mode='cash';subsection=None;continue
        if re.fullmatch(r'GOVERNMENT BOND AND',line,re.I):
            mode='debt';subsection=None;continue
        if re.fullmatch(r'TREASURY BILL',line,re.I) and mode=='debt':
            subsection='Treasury Bill';continue
        if re.fullmatch(r'MONEY MARKET INSTRUMENTS',line,re.I):
            mode='money';subsection=None;continue
        if re.match(r'MCAP Categorization|Mcap Category',line,re.I):
            mode='ignore';subsection=None;continue
        if re.fullmatch(r'PORTFOLIO DETAILS',line,re.I):continue

        gm=re.fullmatch(r'GRAND TOTAL\s+(-?\d+(?:\.\d+)?)',line,re.I)
        if gm:
            grand=float(gm.group(1));continue

        parsed=numeric(line)
        if parsed:
            label,value=parsed
            label=re.sub(r'^[4✓✔]\s*','',label).strip()
            if label.lower()=='total':
                if mode=='equity':equity_total=value
                elif mode=='cash':cash_total=value
                elif mode=='debt':debt_subtotals.append((subsection,value))
                elif mode=='money':money_subtotals.append((subsection,value))
                continue

            continuation=[]
            while i<len(rows) and not numeric(rows[i]) and not reserved.match(rows[i]):
                continuation.append(rows[i]);i+=1

            if mode=='equity':
                if sectorish(label):
                    if continuation and all(x==x.upper() for x in continuation):
                        label=' '.join([label,*continuation]);continuation=[]
                    sector_totals.append({'sector':label,'total':value,'start':len(positions)})
                else:
                    name=' '.join([label,*continuation]).strip()
                    if not sector_totals:return None
                    positions.append({'name':name,'isin':None,'sector':sector_totals[-1]['sector'],
                                      'weight':value,'asset_type':'Equity'})
            elif mode=='cash':
                name=' '.join([label,*continuation]).strip()
                if value>0:
                    cash_positions.append({'name':name,'isin':None,'sector':None,'weight':value,
                                           'asset_type':'Cash and net current assets'})
            elif mode=='debt':
                name=' '.join([label,*continuation]).strip()
                if value>0:
                    debt_positions.append({'name':name,'isin':None,'sector':subsection,'weight':value,
                                           'asset_type':'Debt'})
            elif mode=='money':
                name=' '.join([label,*continuation]).strip()
                name=re.sub(r'\s+\([^)]*(?:A1\+?|SOVEREIGN)[^)]*\)\s*$','',name,flags=re.I)
                if value>0:
                    money_positions.append({'name':name,'isin':None,'sector':subsection,'weight':value,
                                            'asset_type':'Money market'})
            continue

        if mode=='money' and not reserved.match(line):
            subsection=line;continue
        if mode=='debt' and not reserved.match(line):
            subsection=line;continue

    if equity_total is None or cash_total is None or grand is None:return None
    if abs(grand-100)>.03 or len(sector_totals)<2 or not positions:return None

    for j,s in enumerate(sector_totals):
        stop=sector_totals[j+1]['start'] if j+1<len(sector_totals) else len(positions)
        group=positions[s['start']:stop]
        if not group:return None
        if abs(sum(x['weight'] for x in group)-s['total'])>max(.03,.011*len(group)):return None
    if abs(sum(s['total'] for s in sector_totals)-equity_total)>.08:return None

    def validate_subtotals(items,subtotals):
        for section,total in subtotals:
            if abs(sum(x['weight'] for x in items if x['sector']==section)-total)>.03:return False
        return True

    if not validate_subtotals(debt_positions,debt_subtotals):return None
    if not validate_subtotals(money_positions,money_subtotals):return None
    if abs(sum(x['weight'] for x in cash_positions)-cash_total)>.03:return None

    debt_total=sum(x['weight'] for x in debt_positions)
    money_total=sum(x['weight'] for x in money_positions)
    if abs((equity_total+debt_total+money_total+cash_total)-grand)>.04:return None

    all_positions=positions+debt_positions+money_positions+cash_positions
    if any(not 0<=x['weight']<=100 for x in all_positions):return None
    if len({(x['name'],x['asset_type']) for x in all_positions})!=len(all_positions):return None
    return {'day':day,'positions':all_positions}


def layout_aum(text,family,day):
    """Values directly beneath BOI's labels in a visually aligned PDF column.

    Caller must first identify the exact scheme page and its reporting date.
    PDF text order otherwise places both values before both labels.
    """
    if not day or day>date.today().isoformat():return []
    if family=='UTI Small Cap Fund':
        out=[]
        for label,key in [('Fund Size Monthly Average','average_aum'),('Closing AUM','aum')]:
            m=re.search(label+r'\s*:\s*(?:`|₹)\s*Crore\s*'+NUMBER,text,re.I)
            if m:
                v=float(m.group(1).replace(',',''))
                if 0<v<10_000_000:out.append(dict(metric=key,value=v,plan='All',as_of=day,unit='INR crore'))
        return out
    if family!='Bank Of India Small Cap Fund':return []
    out=[];lines=text.splitlines()
    for i,line in enumerate(lines):
        for label,key in [('AVERAGE AUM','average_aum'),('LATEST AUM','aum')]:
            x=line.find(label)
            if x<0:continue
            for following in lines[i+1:i+4]:
                m=re.match(r'\s*(?:`|₹|Rs\.?)\s*'+NUMBER+r'\s*Cr(?:ore)?s?\.?',following[x:x+70],re.I)
                if m:
                    v=float(m.group(1).replace(',',''))
                    if 0<v<10_000_000:out.append(dict(metric=key,value=v,plan='All',as_of=day,unit='INR crore'))
                    break
    return out
,label,re.I):continue
        if not 0<value<=100:return None
        if re.search(r'\b(?:Ltd\.?|Limited)\b',label,re.I):
            if not sectors:return None
            positions.append({'name':label,'isin':None,'sector':sectors[-1]['sector'],
                              'weight':value,'asset_type':'Equity'})
        else:
            sectors.append({'sector':label,'total':value,'start':len(positions)})

    if cash is None or grand is None or abs(grand-100)>.02:return None
    if not 0<=cash<=30 or len(sectors)<5 or len(positions)<40:return None
    for i,s in enumerate(sectors):
        stop=sectors[i+1]['start'] if i+1<len(sectors) else len(positions)
        group=positions[s['start']:stop]
        if not group:return None
        if abs(sum(x['weight'] for x in group)-s['total'])>max(.03,.011*len(group)):return None
    equity_total=sum(s['total'] for s in sectors)
    if abs((equity_total+cash)-grand)>.04:return None
    if abs(sum(x['weight'] for x in positions)-equity_total)>max(.08,.011*len(positions)):return None
    if len({x['name'].lower() for x in positions})!=len(positions):return None
    positions.append({'name':'Net Cash and Cash Equivalent','isin':None,'sector':None,
                      'weight':cash,'asset_type':'Cash and net current assets'})
    return {'day':day,'positions':positions}


def edelweiss_top30_portfolio(text):
    """Parse Edelweiss Small Cap's published Top 30 list as a partial snapshot.

    The factsheet also publishes an independent Top-10 aggregate. Reconcile the
    first ten extracted holdings to that total before retaining any rows.
    """
    normalized=normalize(text)
    family='Edelweiss Small Cap Fund'
    if not owns_page(normalized,family):return None

    m=(re.search(r'Data\s+as\s+on\s+('+DATE+r')',normalized,re.I)
       or re.search(r'Top\s+(?:30\s+)?Holdings\s+as\s+on\s+('+DATE+r')',normalized,re.I)
       or re.search(r'\(\s*As\s+on\s+('+DATE+r')\s*\)',normalized,re.I))
    day=dated(m.group(1)) if m else None
    if not day:return None

    t=re.search(r'Top\s*10\s*(?:stocks|holdings)[^0-9]{0,12}'+NUMBER+r'\s*%',normalized,re.I)
    if not t:return None
    top10=float(t.group(1).replace(',',''))
    if not 5<=top10<=60:return None

    lines=[re.sub(r'\s+',' ',x).strip() for x in normalized.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.fullmatch(r'Company\s+Name\s+Allocation',x,re.I)),None)
    if start is None:return None
    positions=[]
    for line in lines[start+1:]:
        if re.fullmatch(r'Company\s+Name\s+Allocation',line,re.I):continue
        m=re.fullmatch(r'(.+?)\s+(\d+(?:\.\d+)?)\s*%',line)
        if not m:
            if len(positions)>=30:break
            continue
        name=m.group(1).strip();weight=float(m.group(2))
        if re.search(r'Benchmark|Fund|Large\s+Cap|Mid\s+Cap|Small\s+Cap|Net\s+Equity',name,re.I):continue
        if not 0<weight<10:return None
        positions.append({'name':name,'isin':None,'sector':None,'weight':weight,'asset_type':'Equity'})
        if len(positions)==30:break

    if len(positions)!=30:return None
    if len({x['name'].lower() for x in positions})!=30:return None
    if abs(sum(x['weight'] for x in positions[:10])-top10)>.04:return None
    total=sum(x['weight'] for x in positions)
    if not 35<=total<=85:return None
    return {'day':day,'positions':positions}


def boi_complete_portfolio(text):
    """Reconcile Bank of India Small Cap's published monthly portfolio."""
    normalized=normalize(text)
    family='Bank Of India Small Cap Fund'
    if not owns_page(normalized,family):return None
    m=re.search(r'All\s+data\s+as\s+on\s+('+DATE+r')',normalized,re.I)
    day=dated(m.group(1)) if m else None
    if not day:return None

    lines=[re.sub(r'\s+',' ',x).strip() for x in normalized.splitlines()]
    start=next((i for i,x in enumerate(lines) if re.search(r'Portfolio\s+Holdings',x,re.I)),None)
    end=next((i for i,x in enumerate(lines) if start is not None and i>start and re.fullmatch(r'INVESTMENT\s+OBJECTIVE',x,re.I)),None)
    if start is None or end is None:return None
    rows=lines[start:end]

    def numeric(line):
        q=re.fullmatch(r'(.+?)\s+(-?\d+(?:\.\d+)?)\s*%?',line)
        if not q:return None
        return q.group(1).strip(),float(q.group(2))

    reserved=re.compile(
        r'^(?:Portfolio Holdings|Industry/ Rating|Assets|EQUITY HOLDINGS|CASH\s*&\s*CASH EQUIVALENT|'
        r'GOVERNMENT BOND AND|TREASURY BILL|MONEY MARKET INSTRUMENTS|MCAP Categorization|Mcap Category|'
        r'PORTFOLIO DETAILS|GRAND TOTAL|Total|Indicates Top 10 Equity Holdings)',re.I)

    def sectorish(label):
        letters=re.sub(r'[^A-Za-z]','',label)
        return bool(letters) and label==label.upper() and not re.search(r'\b(?:LTD|LIMITED)\b',label,re.I)

    positions=[];sector_totals=[]
    cash_positions=[];debt_positions=[];money_positions=[]
    debt_subtotals=[];money_subtotals=[]
    equity_total=None;cash_total=None;grand=None
    mode='equity';subsection=None;i=0

    while i<len(rows):
        line=rows[i].strip();i+=1
        if not line:continue
        if re.fullmatch(r'EQUITY HOLDINGS',line,re.I):
            mode='equity';subsection=None;continue
        if re.fullmatch(r'CASH\s*&\s*CASH EQUIVALENT',line,re.I):
            mode='cash';subsection=None;continue
        if re.fullmatch(r'GOVERNMENT BOND AND',line,re.I):
            mode='debt';subsection=None;continue
        if re.fullmatch(r'TREASURY BILL',line,re.I) and mode=='debt':
            subsection='Treasury Bill';continue
        if re.fullmatch(r'MONEY MARKET INSTRUMENTS',line,re.I):
            mode='money';subsection=None;continue
        if re.match(r'MCAP Categorization|Mcap Category',line,re.I):
            mode='ignore';subsection=None;continue
        if re.fullmatch(r'PORTFOLIO DETAILS',line,re.I):continue

        gm=re.fullmatch(r'GRAND TOTAL\s+(-?\d+(?:\.\d+)?)',line,re.I)
        if gm:
            grand=float(gm.group(1));continue

        parsed=numeric(line)
        if parsed:
            label,value=parsed
            label=re.sub(r'^[4✓✔]\s*','',label).strip()
            if label.lower()=='total':
                if mode=='equity':equity_total=value
                elif mode=='cash':cash_total=value
                elif mode=='debt':debt_subtotals.append((subsection,value))
                elif mode=='money':money_subtotals.append((subsection,value))
                continue

            continuation=[]
            while i<len(rows) and not numeric(rows[i]) and not reserved.match(rows[i]):
                continuation.append(rows[i]);i+=1

            if mode=='equity':
                if sectorish(label):
                    if continuation and all(x==x.upper() for x in continuation):
                        label=' '.join([label,*continuation]);continuation=[]
                    sector_totals.append({'sector':label,'total':value,'start':len(positions)})
                else:
                    name=' '.join([label,*continuation]).strip()
                    if not sector_totals:return None
                    positions.append({'name':name,'isin':None,'sector':sector_totals[-1]['sector'],
                                      'weight':value,'asset_type':'Equity'})
            elif mode=='cash':
                name=' '.join([label,*continuation]).strip()
                if value>0:
                    cash_positions.append({'name':name,'isin':None,'sector':None,'weight':value,
                                           'asset_type':'Cash and net current assets'})
            elif mode=='debt':
                name=' '.join([label,*continuation]).strip()
                if value>0:
                    debt_positions.append({'name':name,'isin':None,'sector':subsection,'weight':value,
                                           'asset_type':'Debt'})
            elif mode=='money':
                name=' '.join([label,*continuation]).strip()
                name=re.sub(r'\s+\([^)]*(?:A1\+?|SOVEREIGN)[^)]*\)\s*$','',name,flags=re.I)
                if value>0:
                    money_positions.append({'name':name,'isin':None,'sector':subsection,'weight':value,
                                            'asset_type':'Money market'})
            continue

        if mode=='money' and not reserved.match(line):
            subsection=line;continue
        if mode=='debt' and not reserved.match(line):
            subsection=line;continue

    if equity_total is None or cash_total is None or grand is None:return None
    if abs(grand-100)>.03 or len(sector_totals)<2 or not positions:return None

    for j,s in enumerate(sector_totals):
        stop=sector_totals[j+1]['start'] if j+1<len(sector_totals) else len(positions)
        group=positions[s['start']:stop]
        if not group:return None
        if abs(sum(x['weight'] for x in group)-s['total'])>max(.03,.011*len(group)):return None
    if abs(sum(s['total'] for s in sector_totals)-equity_total)>.08:return None

    def validate_subtotals(items,subtotals):
        for section,total in subtotals:
            if abs(sum(x['weight'] for x in items if x['sector']==section)-total)>.03:return False
        return True

    if not validate_subtotals(debt_positions,debt_subtotals):return None
    if not validate_subtotals(money_positions,money_subtotals):return None
    if abs(sum(x['weight'] for x in cash_positions)-cash_total)>.03:return None

    debt_total=sum(x['weight'] for x in debt_positions)
    money_total=sum(x['weight'] for x in money_positions)
    if abs((equity_total+debt_total+money_total+cash_total)-grand)>.04:return None

    all_positions=positions+debt_positions+money_positions+cash_positions
    if any(not 0<=x['weight']<=100 for x in all_positions):return None
    if len({(x['name'],x['asset_type']) for x in all_positions})!=len(all_positions):return None
    return {'day':day,'positions':all_positions}


def layout_aum(text,family,day):
    """Values directly beneath BOI's labels in a visually aligned PDF column.

    Caller must first identify the exact scheme page and its reporting date.
    PDF text order otherwise places both values before both labels.
    """
    if not day or day>date.today().isoformat():return []
    if family=='UTI Small Cap Fund':
        out=[]
        for label,key in [('Fund Size Monthly Average','average_aum'),('Closing AUM','aum')]:
            m=re.search(label+r'\s*:\s*(?:`|₹)\s*Crore\s*'+NUMBER,text,re.I)
            if m:
                v=float(m.group(1).replace(',',''))
                if 0<v<10_000_000:out.append(dict(metric=key,value=v,plan='All',as_of=day,unit='INR crore'))
        return out
    if family!='Bank Of India Small Cap Fund':return []
    out=[];lines=text.splitlines()
    for i,line in enumerate(lines):
        for label,key in [('AVERAGE AUM','average_aum'),('LATEST AUM','aum')]:
            x=line.find(label)
            if x<0:continue
            for following in lines[i+1:i+4]:
                m=re.match(r'\s*(?:`|₹|Rs\.?)\s*'+NUMBER+r'\s*Cr(?:ore)?s?\.?',following[x:x+70],re.I)
                if m:
                    v=float(m.group(1).replace(',',''))
                    if 0<v<10_000_000:out.append(dict(metric=key,value=v,plan='All',as_of=day,unit='INR crore'))
                    break
    return out
