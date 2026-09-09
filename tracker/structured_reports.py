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
