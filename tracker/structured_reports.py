"""Dated figures and reconciled holdings from identified public AMC reports."""
import json
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from . import db
from .report_parser import DATE,dated
from .disclosures import same_fund_title,portfolio
from .providers import number

URLS={
 'Franklin India Small Cap Fund':'https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html',
 'Pgim India Small Cap Fund':'https://www.pgimindia.com/mutual-funds/equity-funds/small-cap-fund',
 'Sundaram Small Cap Fund':'https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json',
}


def extract(content,family,url,h):
    if family=='Baroda Bnp Paribas Small Cap Fund' and urlparse(url).hostname in ('www.barodabnpparibasmf.in','barodabnpparibasmf.in') and re.fullmatch(r'/efactsheet/[A-Za-z]{3}\d{4}/Innerpages/Small-cap.html',urlparse(url).path):
        return baroda(content,family,url,h)
    expected=URLS.get(family)
    if not expected or urlparse(url)._replace(query='',fragment='')!=urlparse(expected):return None
    saved=0
    def put(metric,value,day,plan='All',unit='INR crore'):
        nonlocal saved
        if not day:return
        if metric in ('aum','average_aum') and not 0<value<10_000_000:return
        if metric in ('ter','base_expense_ratio') and not 0<=value<=5:return
        db.metric(family,plan,metric,day,value,unit,url,h);saved+=1
    if family=='Sundaram Small Cap Fund':
        rows=json.loads(content)
        row=next((r for r in rows if r.get('FUNDGROUP_ID')=='SC' and same_fund_title(r.get('GROUP_NAME',''),family)),None)
        if not row:return 0
        day=dated(row.get('AUMASONDATE',''))
        # Verified digital-factsheet labels: month-end/average, in INR crore.
        for key,metric in [('MONTHENDAUM','aum'),('AUM','average_aum')]:
            if row.get(key):put(metric,number(row[key]),day)
        terday=dated(row.get('TER_DATE_DISP',''))
        for key,plan in [('REG_TOT_TER_DISP','Regular'),('DP_TOT_TER_DISP','Direct')]:
            if row.get(key):put('ter',number(row[key]),terday,plan,'% p.a.')
        return saved
    soup=BeautifulSoup(content,'html.parser')
    text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True))
    if family=='Pgim India Small Cap Fund':
        if not any(same_fund_title(x.get_text(' ',strip=True),family) for x in soup.select('h1')):return 0
        m=re.search(r'\bAUM\s+as on\s+('+DATE+r')\s*₹\s*([\d,.]+)\s*Cr',text,re.I)
        if m:put('aum',number(m.group(2)),dated(m.group(1)))
        # Unqualified "Expense Ratio" cannot establish TER versus BER.
        return saved
    header=soup.select_one('table')
    if not header:return 0
    title=header.select_one('span')
    if not title or not same_fund_title(title.get_text(' ',strip=True),family):return 0
    m=re.search(r'As on\s+('+DATE+r')',header.get_text(' ',strip=True),re.I)
    day=dated(m.group(1)) if m else None
    if not day:return 0
    m=re.search(r'FUND SIZE\s*\(AUM\)\s*Month End\s*Rs\.?\s*([\d,.]+)\s*Crores\s*Monthly Average\s*Rs\.?\s*([\d,.]+)\s*Crores',text,re.I)
    if m:put('aum',number(m.group(1)),day);put('average_aum',number(m.group(2)),day)
    m=re.search(r'BASE EXPENSE RATIO\s*#?\s*\(DIRECT\)\s*:\s*([\d.]+)%',text,re.I)
    if m:put('base_expense_ratio',number(m.group(1)),day,'Direct','% p.a.')
    m=re.search(r'BASE EXPENSE RATIO\s*#?\s*:\s*([\d.]+)%',text,re.I)
    if m and re.search(r'Growth Plan Rs.*Direct - Growth Plan Rs',text):put('base_expense_ratio',number(m.group(1)),day,'Regular','% p.a.')
    for table in soup.select('table'):
        if re.search(r'Company Name.*No\. of shares.*Market Value.*% of',table.get_text(' ',strip=True)):
            positions=franklin_positions(table)
            if positions:portfolio(family,day,positions,True,url,h);saved+=len(positions)
    return saved


def baroda(content,family,url,h):
    soup=BeautifulSoup(content,'html.parser')
    if not soup.title or re.sub(r'[^a-z]','',soup.title.get_text().lower())!='bbnppsmallcapfund':return 0
    text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True));count=0
    for label,key in [('Monthly AAUM','average_aum'),('AUM','aum')]:
        m=re.search(r'\b'+label+r'## As on\s+('+DATE+r')\s*:\s*₹\s*([\d,.]+)\s*Crores',text,re.I)
        if m and dated(m.group(1)) and 0<number(m.group(2))<10_000_000:
            db.metric(family,'All',key,dated(m.group(1)),number(m.group(2)),'INR crore',url,h);count+=1
    return count


def uti_zip(content,family,url,h):
    """Read the named workbook in UTI's public monthly ZIP without extracting paths."""
    import io,zipfile,openpyxl
    from pathlib import PurePosixPath
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        entries=z.infolist()
        if len(entries)>100 or sum(i.file_size for i in entries)>100*1024*1024:raise ValueError('Oversized portfolio ZIP')
        for i in entries:
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or i.flag_bits&1:raise ValueError('Unsupported portfolio ZIP entry')
        matched=[i for i in entries if re.fullmatch(r'Sebi Exposure as on .+_final\.xlsx',PurePosixPath(i.filename).name,re.I)]
        if len(matched)!=1:return 0
        with z.open(matched[0]) as f:w=openpyxl.load_workbook(io.BytesIO(f.read()),data_only=True,read_only=True)
        count=0
        for sheet in w:
            rows=list(sheet.values);r=uti_rows(rows)
            if r is None:continue
            db.metric(family,'All','aum',r['day'],r['aum'],'INR crore',url,h);count+=1
            # This exposure report abbreviates small weights and short-term
            # deposit holdings. It cannot establish a complete position list.
            if r['positions']:portfolio(family,r['day'],r['positions'],False,url,h);count+=len(r['positions'])
        w.close();return count


def uti_rows(rows):
    from .disclosures import report_date
    begin=next((i for i,r in enumerate(rows) if str(r[0] or '').strip().lower()=='scheme: uti small cap fund'),None)
    if begin is None:return None
    block=[];total=None
    for row in rows[begin+1:]:
        label=str(row[0] or '').strip()
        if label.lower()=='total : uti small cap fund':
            total=number(row[3]);break
        if re.match(r'SCHEME(?:\s*:| CODE)',label,re.I):return None
        block.append(row)
    if not total or not 0<total/100<10_000_000:return None
    prefix=' '.join(str(v) for row in block[:4] for v in row if v)
    if not re.search(r'Market value in Lacs',prefix,re.I):return None
    day=report_date(prefix)
    if not day:return None
    header=next((r for r in block[:6] if len(r)>7 and str(r[7]).strip()=='ISIN'),None)
    if header is None or '% TO NAV' not in str(header[4]).upper():return None
    positions=[]
    for row in block:
        if len(row)<=7 or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}',str(row[7] or '')):continue
        try:weight=number(row[4])
        except ValueError:continue
        if not 0<=weight<=100:return None
        positions.append({'isin':row[7],'name':re.sub(r'^EQ\s*-\s*','',str(row[0])),'sector':str(row[1] or ''),'weight':weight,'asset_type':'Equity' if str(row[0]).startswith('EQ -') else 'Unclassified'})
    if sum(p['weight'] for p in positions)>100.5:return None
    return {'day':day,'aum':round(total/100,6),'positions':positions}


def franklin_positions(table):
    """Validate all equity, debt and cash rows against the published asset total."""
    positions=[];values=[];total=None;sector=None;asset='Equity'
    for row in table.select('tr'):
        cells=[c.get_text(' ',strip=True) for c in row.find_all(['td','th'],recursive=False)]
        if not cells:continue
        name=cells[0].rstrip('*').strip()
        if name=='Company Name':
            if 'Ratings' in ' '.join(cells):asset='Debt';sector=None
            continue
        if name.lower()=='total asset':
            try:total=(number(cells[-2]),number(cells[-1]))
            except ValueError:return []
            break
        if name.lower().startswith('total '):continue
        if not any(cells[1:]):sector=name;continue
        if len(cells) not in (3,4):return []
        if re.fullmatch(r'Call,\s*cash and other current asset',name,re.I):asset='Cash and net current assets';sector=None
        elif len(cells)==3:return []
        try:value=number(cells[-2]);weight=number(cells[-1])
        except ValueError:return []
        if re.search(r'\b(?:others|less than|top \d+|remaining)\b',name,re.I) or not -100<=weight<=100:return []
        positions.append({'name':name,'weight':weight,'sector':sector,'asset_type':asset});values.append(value)
    if not total or abs(total[1]-100)>.01 or not positions:return []
    if abs(sum(values)-total[0])>max(.05,.011*len(values)):return []
    if abs(sum(x['weight'] for x in positions)-100)>max(.05,.0051*len(positions)):return []
    if len({x['name'] for x in positions})!=len(positions):return []
    return positions
