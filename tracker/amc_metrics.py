"""Conservative parsers for dated figures on official, single-fund pages."""
from __future__ import annotations
from datetime import date
import calendar
import json
import re
from urllib.parse import urlparse
from . import db
from .providers import fetch,can_crawl,iso,number,save_document,doc_version
from .disclosures import same_fund_title,report_date
from bs4 import BeautifulSoup

PAGES=[
    ('Axis','Axis Small Cap Fund','https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct'),
    ('DSP','DSP Small Cap Fund','https://www.dspim.com/invest/mutual-fund-schemes/equity-funds/small-cap-fund/dspmc-direct-growth'),
    ('Kotak','Kotak Small Cap Fund','https://www.kotakmf.com/mutual-funds/equity-funds/kotak-smallcap-fund/dir-g'),
    ('Aditya Birla','Aditya Birla Sun Life Small Cap Fund','https://mutualfund.adityabirlacapital.com/empower/Equity-Funds/Small-Cap-Fund.html'),
    ('Tata','Tata Small Cap Fund','https://www.tatamutualfund.com/mutual-funds/tata-small-cap-fund-direct-growth'),
]


def parse_page(content,family,url,h):
    expected=next((u for _,f,u in PAGES if f==family),None)
    if expected:
        actual,known=urlparse(url),urlparse(expected)
        if actual.hostname.removeprefix('www.')!=known.hostname.removeprefix('www.') or actual.path.rstrip('/')!=known.path.rstrip('/'):return 0
    soup=BeautifulSoup(content,'html.parser')
    exact=any(same_fund_title(tag.get_text(' ',strip=True),family) for tag in soup.select('h1,h2,h3'))
    # Tata renders its fund title in a div; its document title identifies the plan.
    if family=='Tata Small Cap Fund' and soup.title:
        exact=soup.title.get_text().startswith('Tata Small Cap Fund Direct Growth')
    if family=='Mahindra Manulife Small Cap Fund' and '/digital-factsheet/' in url:
        exact=any(same_fund_title(tag.get_text(' ',strip=True),family) for tag in soup.select('.fund-name,.fundname,.scheme-name,.heading,p.p-4'))
    if not exact:return 0
    text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True)).replace('Sept ','Sep ')
    patterns={
        'Axis Small Cap Fund':r'AUM \(In Cr\.\)\s*₹\s*([\d,.]+)\s*(As On [A-Za-z]+ \d{1,2}, \d{4})',
        'DSP Small Cap Fund':r'Total AUM\s*₹\s*([\d,.]+)\s*crores\s*(as of [A-Za-z]+ \d{1,2}, \d{4})',
        'Kotak Small Cap Fund':r'\bAUM:\s*₹\s*([\d,.]+)\s*Cr\.\s*(As on \d{1,2}-[A-Za-z]+-\d{4})',
        'Tata Small Cap Fund':r'Overview Fund Size \(\s*AUM\s*\)\s*₹\s*([\d,.]+)\s*Cr\s*(as on \d{1,2} [A-Za-z]+ \d{4})',
    }
    value=None;day=None
    if family in patterns:
        m=re.search(patterns[family],text,re.I)
        if m:value=number(m.group(1));day=report_date(m.group(2))
    elif family=='Aditya Birla Sun Life Small Cap Fund':
        m=re.search(r'AUM (as on [A-Za-z]+ \d{1,2}, \d{4})\s*\(in ₹Crore\)\s*Month End AUM\s*([\d,.]+)',text,re.I)
        if m:day=report_date(m.group(1));value=number(m.group(2))
    elif family=='Mahindra Manulife Small Cap Fund':
        m=re.search(r'Monthly AUM (as on [A-Za-z]+ \d{1,2}, \d{4}) \(Rs\. in Cr\.\):\s*([\d,.]+)',text,re.I)
        if m:day=report_date(m.group(1));value=number(m.group(2))
    elif family=='Iti Small Cap Fund' and '/digitalfactsheet/' in url:
        m=re.search(r'Portfolio Details AUM \(in Rs\. Cr\):\s*([\d,.]+)',text,re.I)
        # The dated monthly report identifies the reporting month in its URL;
        # it must also show a NAV date in that month. Use its month-end AUM date,
        # which can differ from the last business-day NAV date.
        month=re.search(r'/digitalfactsheet/([A-Za-z]+)(\d{4})/',url)
        nav=re.search(r'NAV (as on [A-Za-z]+ \d{1,2}, \d{4})',text,re.I)
        if m and month and nav:
            from datetime import datetime
            report=datetime.strptime(month.group(1)+month.group(2),'%B%Y').date()
            navday=report_date(nav.group(1))
            if navday and navday[:7]==report.strftime('%Y-%m'):
                day=report.replace(day=calendar.monthrange(report.year,report.month)[1]).isoformat();value=number(m.group(1))
    if value is None or day is None or day>date.today().isoformat() or not 0<value<10_000_000:return 0
    db.metric(family,'All','aum',day,value,'INR crore',url,h)
    if family=='DSP Small Cap Fund':
        m=re.search(r'Base Expense Ratio\s*([\d.]+)%\s*(as of [A-Za-z]+ \d{1,2}, \d{4})',text,re.I)
        if m:db.metric(family,'Direct','base_expense_ratio',report_date(m.group(2)),number(m.group(1)),'% p.a.',url,h)
    # Only unambiguous fund-level benchmark text in the summary region.
    if family=='DSP Small Cap Fund' and re.search(r'Benchmark:\s*BSE 250 Small Cap TRI',text,re.I):db.metric(family,'All','benchmark',date.today().isoformat(),'BSE 250 Small Cap TRI','Observed on official fund page',url,h)
    if family=='Axis Small Cap Fund' and re.search(r'Benchmark Returns.{0,35}NIFTY Smallcap 250 TRI',text,re.I):db.metric(family,'All','benchmark',date.today().isoformat(),'Nifty Smallcap 250 TRI','Observed on official fund page',url,h)
    return 1


def update(progress=lambda _:None):
    saved=0;gaps=[]
    pages=list(PAGES)
    for offset in range(3):
        today=date.today();year,month=divmod(today.year*12+today.month-1-offset,12);month+=1;name=calendar.month_name[month]
        pages.extend([
            ('Mahindra','Mahindra Manulife Small Cap Fund',f'https://www.mahindramanulife.com/digital-factsheet/{name.lower()}-{year}/Equity-funds/Small-Cap-Fund.html'),
            ('ITI','Iti Small Cap Fund',f'https://www.itiamc.com/digitalfactsheet/{name}{year}/innerpages/Small-Cap.html'),
        ])
    for amc,family,url in pages:
        if not db.one('SELECT code FROM schemes WHERE family=?',(family,)):continue
        progress('Official AUM · '+family)
        with db.connect() as c:c.execute('INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)',(amc,url,'Fund figures and publications'))
        try:
            can_crawl(url);body,h,_=fetch(url);count=parse_page(body,family,url,h);saved+=count
            did=save_document(family,'Monthly digital factsheet' if 'factsheet/' in url.lower() else 'Official fund page',url,'factsheet' if 'factsheet/' in url.lower() else 'source page','Fund',origin='AMC');doc_version(did,h)
            status='Checked' if count else 'Limited';detail='Dated AUM extracted; original page archived' if count else 'No unambiguous dated AUM could be extracted'
            if not count:gaps.append(family)
        except Exception as e:status='Gap';detail=str(e)[:350];gaps.append(family)
        with db.connect() as c:c.execute('UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE amc_match=? AND url=?',(db.now(),status,detail,amc,url))
    return f'{saved} official fund reports with dated AUM'+('; some reporting pages unavailable for: '+', '.join(sorted(set(gaps))) if gaps else '')
