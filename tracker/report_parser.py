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
    avg=re.search(r'\bMonthly (?:Average|AVG) (?:AUM|Assets Under Management\s*\(AAUM\))\s*[:#-]?\s*'+currency+NUMBER+r'\s*'+unit,flat,re.I)
    if avg:add('average_aum',float(avg.group(1).replace(',','')))
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
        (r'(?:^|\n)(?:AMFI Tier 1 |Primary )?Benchmark(?: Index| Name)?\s*[:\n ]\s*([^\n]+)','benchmark'),
        (r'(?:^|\n)(?:Date of Allotment|Inception Date)\s*[:\n]\s*([^\n]+)','fund_launch'),
    ]:
        m=re.search(pattern,text,re.I)
        if m:
            v=m.group(1).strip()
            if key=='benchmark' and re.search(r'Nifty|BSE|CRISIL',v,re.I):add(key,v,unit='Reported')
            elif key=='fund_launch' and dated(v):add(key,dated(v),unit='Reported')
    if family=='SBI Small Cap Fund' and re.search(r'Benchmark BSE 250 Small Cap\s+Index TRI',text):
        for fact in out:
            if fact['metric']=='benchmark':fact['value']='BSE 250 Small Cap Index TRI'
    return out


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
