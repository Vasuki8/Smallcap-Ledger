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
    ('Bajaj','Bajaj Finserv Small Cap Fund','https://www.bajajamc.com/mutual-funds/equity-funds/bajaj-finserv-small-cap-fund'),
    ('Quantum','Quantum Small Cap Fund','https://www.quantumamc.com/equity-funds/quantum-small-cap-fund'),
    ('Franklin','Franklin India Small Cap Fund','https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html'),
    ('PGIM','Pgim India Small Cap Fund','https://www.pgimindia.com/mutual-funds/equity-funds/small-cap-fund'),
    ('Bank of India','Bank Of India Small Cap Fund','https://www.boimf.in/products/equity-funds/bank-of-india-small-cap-fund'),
    ('Sundaram','Sundaram Small Cap Fund','https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json'),
]


def mahindra_portfolio(soup,day,url,h):
    """Parse only a fully reconciled Mahindra Small Cap digital-factsheet table."""
    from .disclosures import portfolio
    table=None
    for candidate in soup.select('table'):
        text=re.sub(r'\s+',' ',candidate.get_text(' ',strip=True))
        if re.search(r'Company\s*/\s*Issuer',text,re.I) and re.search(r'Grand\s+Total',text,re.I):
            table=candidate;break
    if table is None:return 0
    positions=[];sector=None;equity_total=None;cash=None;grand=None
    for tr in table.select('tr'):
        cells=tr.find_all(['th','td'],recursive=False)
        if len(cells)<2:continue
        texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
        for j in range(1,len(cells)):
            raw=texts[j]
            if not re.fullmatch(r'-?[\d,]+(?:\.\d+)?\s*%?',raw):continue
            k=j-1
            while k>=0 and not texts[k]:k-=1
            if k<0:continue
            label=texts[k];value=number(raw)
            key=re.sub(r'[^a-z]','',label.lower())
            if key=='equityandequityrelatedtotal':equity_total=value;continue
            if key in ('cashotherreceivables','cashandotherreceivables'):cash=value;continue
            if key=='grandtotal':grand=value;continue
            if re.search(r'company\s*/\s*issuer|%\s*of\s*net\s*assets',label,re.I):continue
            bold=bool(cells[k].find(['b','strong']))
            issuer=bool(re.search(r'(?:\b(?:bank|corporation)\b|\b(?:limited|ltd\.?|industries)\s*$)',label,re.I))
            if bold or not issuer:
                sector=label;continue
            if not 0<=value<=100:return 0
            positions.append({'name':label,'isin':None,'sector':sector,'weight':value,'asset_type':'Equity'})
    if equity_total is None or cash is None or grand is None or abs(grand-100)>.02:return 0
    if abs((equity_total+cash)-grand)>.03 or not positions:return 0
    if abs(sum(x['weight'] for x in positions)-equity_total)>max(.08,.011*len(positions)):return 0
    positions.append({'name':'Cash & Other Receivables','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    portfolio('Mahindra Manulife Small Cap Fund',day,positions,True,url,h)
    return len(positions)


def iti_portfolio(soup,day,url,h):
    """Parse a fully reconciled ITI Small Cap digital-factsheet portfolio."""
    from .disclosures import portfolio
    table=None;label_col=None;base_col=None;deriv_col=None
    for candidate in soup.select('table'):
        for tr in candidate.select('tr'):
            cells=tr.find_all(['th','td'],recursive=False)
            texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
            lc=next((i for i,x in enumerate(texts) if re.search(r'Name\s+of\s+the\s+Instrument',x,re.I)),None)
            bc=next((i for i,x in enumerate(texts) if re.fullmatch(r'%\s*to\s*NAV',x,re.I)),None)
            dc=next((i for i,x in enumerate(texts) if re.search(r'%\s*to\s*NAV.*Derivatives',x,re.I)),None)
            if None not in (lc,bc,dc):
                table=candidate;label_col=lc;base_col=bc;deriv_col=dc;break
        if table is not None:break
    if table is None:return 0
    positions=[];sector=None;equity_total=None;derivative_total=0.0;fund_total=None;cash=None
    fund_mode=False
    def cell(texts,index):return texts[index] if index is not None and index<len(texts) else ''
    def numeric_cell(texts,index):
        raw=cell(texts,index)
        return number(raw) if re.fullmatch(r'-?[\d,.]+(?:\.\d+)?\s*%?',raw or '') else None
    for tr in table.select('tr'):
        cells=tr.find_all(['th','td'],recursive=False)
        texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
        label=cell(texts,label_col)
        if not label or re.search(r'Name\s+of\s+the\s+Instrument',label,re.I):continue
        base=numeric_cell(texts,base_col);deriv=numeric_cell(texts,deriv_col)
        key=re.sub(r'[^a-z]','',label.lower())
        if key=='equityequityrelatedtotal':
            equity_total=base;derivative_total=deriv or 0.0;fund_mode=False;continue
        if key=='mutualfundunits':
            fund_total=base;fund_mode=True;sector=None;continue
        if key=='shorttermdebtnetcurrentassets':
            cash=base;fund_mode=False;continue
        issuer=bool(re.search(r'(?:\b(?:bank|corporation)\b|\b(?:limited|ltd\.?)\s*$)',label,re.I))
        if fund_mode and label.lower().startswith('iti ') and 'fund' in label.lower():
            if base is None:return 0
            positions.append({'name':label,'isin':None,'sector':None,'weight':base,'asset_type':'Fund units'})
            continue
        if not issuer:
            sector=label;fund_mode=False;continue
        if base is not None:
            positions.append({'name':label,'isin':None,'sector':sector,'weight':base,'asset_type':'Equity'})
        if deriv is not None:
            positions.append({'name':label+' (Derivative)','isin':None,'sector':sector,'weight':deriv,'asset_type':'Derivative'})
    if equity_total is None or fund_total is None or cash is None or not positions:return 0
    equity=sum(x['weight'] for x in positions if x['asset_type']=='Equity')
    derivatives=sum(x['weight'] for x in positions if x['asset_type']=='Derivative')
    funds=sum(x['weight'] for x in positions if x['asset_type']=='Fund units')
    if abs(equity-equity_total)>max(.08,.011*sum(x['asset_type']=='Equity' for x in positions)):return 0
    if abs(derivatives-derivative_total)>.03:return 0
    if abs(funds-fund_total)>.03:return 0
    if abs((equity_total+derivative_total+fund_total+cash)-100)>.03:return 0
    positions.append({'name':'Short Term Debt & Net Current Assets','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    portfolio('Iti Small Cap Fund',day,positions,True,url,h)
    return len(positions)


def canara_portfolio(soup,day,url,h):
    """Parse only a fully reconciled Canara Robeco Small Cap digital portfolio."""
    from .disclosures import portfolio
    table=None;label_col=None;mcap_col=None;weight_col=None
    for candidate in soup.select('table'):
        for tr in candidate.select('tr'):
            cells=tr.find_all(['th','td'],recursive=False)
            texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
            lc=next((i for i,x in enumerate(texts) if re.search(r'Name\s+of\s+the\s+Instruments?/?Issuer',x,re.I)),None)
            mc=next((i for i,x in enumerate(texts) if re.fullmatch(r'Market\s*Cap',x,re.I)),None)
            wc=next((i for i,x in enumerate(texts) if re.fullmatch(r'%\s*to\s*NAV',x,re.I)),None)
            if None not in (lc,mc,wc):
                table=candidate;label_col=lc;mcap_col=mc;weight_col=wc;break
        if table is not None:break
    if table is None:return 0
    positions=[];sector=None;equity_total=None;money_total=None;cash=None;grand=None
    def cell(texts,index):return texts[index] if index is not None and index<len(texts) else ''
    def pct(texts,index):
        raw=cell(texts,index)
        return number(raw) if re.fullmatch(r'-?[\d,.]+(?:\.\d+)?\s*%?',raw or '') else None
    for tr in table.select('tr'):
        cells=tr.find_all(['th','td'],recursive=False)
        texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
        label=cell(texts,label_col)
        if not label or re.search(r'Name\s+of\s+the\s+Instruments?/?Issuer',label,re.I):continue
        weight=pct(texts,weight_col);mcap=cell(texts,mcap_col).upper()
        key=re.sub(r'[^a-z]','',label.lower())
        if key in ('equities','equityequityrelated'):equity_total=weight;sector=None;continue
        if key=='moneymarketinstruments':money_total=weight;sector=None;continue
        if key=='netcurrentassets':cash=weight;sector=None;continue
        if key in ('grandtotalnetasset','grandtotalnetassets','grandtotal'):grand=weight;continue
        if mcap in ('L','M','S'):
            if weight is None:return 0
            positions.append({'name':label,'isin':None,'sector':sector,'weight':weight,'asset_type':'Equity'})
            continue
        if key=='treps':
            if weight is None:return 0
            positions.append({'name':'TREPS','isin':None,'sector':None,'weight':weight,'asset_type':'Money market'})
            continue
        # Rows without a market-cap flag are section/industry totals.
        if weight is not None:sector=label
    if None in (equity_total,money_total,cash,grand) or abs(grand-100)>.03:return 0
    equity=sum(x['weight'] for x in positions if x['asset_type']=='Equity')
    money=sum(x['weight'] for x in positions if x['asset_type']=='Money market')
    if abs(equity-equity_total)>max(.08,.011*sum(x['asset_type']=='Equity' for x in positions)):return 0
    if abs(money-money_total)>.03:return 0
    if abs((equity_total+money_total+cash)-grand)>.03:return 0
    positions.append({'name':'Net Current Assets','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
    portfolio('Canara Robeco Small Cap Fund',day,positions,True,url,h)
    return len(positions)



def axis_top_holdings(soup,page_text,url,h):
    """Retain Axis' explicitly dated top-10 table as a partial portfolio only."""
    from .disclosures import portfolio
    m=re.search(r'Top\s*10\s*Stocks\s*\(%\)\s*([\d.]+).*?Updated\s+as\s+on:\s*(?:As\s+of\s+)?([A-Za-z]+\s+\d{1,2},\s*\d{4})',page_text,re.I)
    if not m:return 0
    stated=number(m.group(1));day=report_date('as on '+m.group(2))
    if not day or day>date.today().isoformat() or not 0<stated<100:return 0
    for table in soup.select('table'):
        table_text=re.sub(r'\s+',' ',table.get_text(' ',strip=True))
        if not (re.search(r'\bStocks\b',table_text,re.I) and re.search(r'%\s*of\s*holdings',table_text,re.I)):continue
        positions=[]
        for tr in table.select('tr'):
            cells=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in tr.find_all(['th','td'],recursive=False)]
            if len(cells)<2:continue
            name=next((x for x in cells[:-1] if x),'');raw=cells[-1]
            if not name or re.fullmatch(r'Stocks',name,re.I) or not re.fullmatch(r'[\d.]+\s*%?',raw):continue
            weight=number(raw)
            if not 0<weight<20:return 0
            positions.append({'name':name,'isin':None,'sector':None,'weight':weight,'asset_type':'Equity'})
        if not 5<=len(positions)<=20:continue
        if len({x['name'] for x in positions})!=len(positions):continue
        if abs(sum(x['weight'] for x in positions)-stated)>.08:continue
        portfolio('Axis Small Cap Fund',day,positions,False,url,h)
        return len(positions)
    return 0



def boi_top_holdings(soup,page_text,url,h):
    """Retain BOI's explicitly dated Top 10 holdings as a partial snapshot."""
    from .disclosures import portfolio
    d=re.search(r'portfolio\s+as\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s*,?\s*\d{4})',page_text,re.I)
    if not d:return 0
    day=report_date('as on '+d.group(1))
    if not day or day>date.today().isoformat():return 0
    table=None
    for candidate in soup.select('table'):
        tx=re.sub(r'\s+',' ',candidate.get_text(' ',strip=True))
        if re.search(r'Portfolio\s+Details',tx,re.I) and re.search(r'%\s*to\s*Net\s*Assets',tx,re.I):
            table=candidate;break
    if table is None:return 0
    positions=[]
    for tr in table.select('tr'):
        cells=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in tr.find_all(['th','td'],recursive=False)]
        if len(cells)<2:continue
        name=cells[0];raw=cells[-1]
        if not name or re.search(r'Portfolio\s+Details|%\s*to\s*Net\s*Assets',name,re.I):continue
        if not re.fullmatch(r'\d+(?:\.\d+)?\s*%?',raw):continue
        weight=number(raw)
        if not 0<weight<20:return 0
        positions.append({'name':name,'isin':None,'sector':None,'weight':weight,'asset_type':'Equity'})
    if not 5<=len(positions)<=15:return 0
    if len({x['name'].lower() for x in positions})!=len(positions):return 0
    if not 5<=sum(x['weight'] for x in positions)<=60:return 0
    portfolio('Bank Of India Small Cap Fund',day,positions,False,url,h)
    b=re.search(r'Benchmark\s+Riskometer\s*:?\s*(NIFTY\s+Smallcap\s+250\s+TRI)',page_text,re.I)
    if b:db.metric('Bank Of India Small Cap Fund','All','benchmark',day,'NIFTY Smallcap 250 TRI','Reported',url,h)
    return len(positions)

def kotak_portfolio(soup,day,url,h):
    """Parse Kotak's full monthly Small Cap factsheet portfolio by reconciliation."""
    from .disclosures import portfolio
    def parse_table(table):
        equity_rows=[];equity_total=None;repo=None;cash=None;grand=None
        for tr in table.select('tr'):
            cells=tr.find_all(['th','td'],recursive=False)
            texts=[re.sub(r'\s+',' ',c.get_text(' ',strip=True)).strip() for c in cells]
            if not texts:continue
            label=next((x for x in texts if x),'')
            raw=next((x for x in reversed(texts[1:]) if re.fullmatch(r'-?[\d,]+(?:\.\d+)?\s*%?',x)),None)
            if not label or raw is None:continue
            value=number(raw);key=re.sub(r'[^a-z]','',label.lower())
            if key=='equityequityrelatedtotal':equity_total=value;continue
            if key=='tripartyrepo':repo=value;continue
            if key in ('netcurrentassetsliabilities','netcurrentassetsliability'):cash=value;continue
            if key=='grandtotal':grand=value;continue
            if equity_total is None:equity_rows.append((label,value))
        if None in (equity_total,repo,cash,grand) or abs(grand-100)>.03 or not equity_rows:return None
        positions=[];i=0;sector_totals=0.0
        while i<len(equity_rows):
            sector,sector_total=equity_rows[i];i+=1
            if not 0<=sector_total<=100:return None
            group=[];subtotal=0.0
            while i<len(equity_rows):
                name,weight=equity_rows[i]
                if not 0<=weight<=100:return None
                group.append((name,weight));subtotal+=weight;i+=1
                tolerance=max(.03,.006*len(group))
                if abs(subtotal-sector_total)<=tolerance:break
                if subtotal>sector_total+tolerance:return None
            tolerance=max(.03,.006*len(group))
            if not group or abs(subtotal-sector_total)>tolerance:return None
            sector_totals+=sector_total
            positions.extend({'name':name,'isin':None,'sector':sector,'weight':weight,'asset_type':'Equity'} for name,weight in group)
        if abs(sector_totals-equity_total)>max(.08,.006*len(positions)):return None
        if abs(sum(x['weight'] for x in positions)-equity_total)>max(.08,.006*len(positions)):return None
        if abs((equity_total+repo+cash)-grand)>.03:return None
        if len({x['name'] for x in positions})!=len(positions):return None
        positions.append({'name':'Triparty Repo','isin':None,'sector':None,'weight':repo,'asset_type':'Money market'})
        positions.append({'name':'Net Current Assets/(Liabilities)','isin':None,'sector':None,'weight':cash,'asset_type':'Cash and net current assets'})
        return positions
    for table in soup.select('table'):
        text=re.sub(r'\s+',' ',table.get_text(' ',strip=True))
        if not (re.search(r'Issuer\s*/\s*Instrument',text,re.I) and re.search(r'Equity\s*&\s*Equity\s+related\s*-\s*Total',text,re.I) and re.search(r'Grand\s+Total',text,re.I)):
            continue
        positions=parse_table(table)
        if positions:
            portfolio('Kotak Small Cap Fund',day,positions,True,url,h)
            return len(positions)
    return 0

def parse_page(content,family,url,h):
    from .structured_reports import extract
    special=extract(content,family,url,h)
    if special is not None:return special
    expected=next((u for _,f,u in PAGES if f==family),None)
    actual=urlparse(url)
    kotak_monthly=family=='Kotak Small Cap Fund' and (actual.hostname or '').lower().removeprefix('www.')=='kotakmf.com' and bool(re.fullmatch(r'/factsheet/[A-Za-z]+_\d{4}/kotak/SMALL-CAP\.html',actual.path,re.I))
    if expected:
        known=urlparse(expected)
        if (actual.hostname or '').removeprefix('www.')!=(known.hostname or '').removeprefix('www.') or (actual.path.rstrip('/')!=known.path.rstrip('/') and not kotak_monthly):return 0
    soup=BeautifulSoup(content,'html.parser')
    exact=any(same_fund_title(tag.get_text(' ',strip=True),family) for tag in soup.select('h1,h2,h3'))
    # Tata renders its fund title in a div; its document title identifies the plan.
    if family=='Tata Small Cap Fund' and soup.title:
        exact=soup.title.get_text().startswith('Tata Small Cap Fund Direct Growth')
    if family=='Mahindra Manulife Small Cap Fund' and '/digital-factsheet/' in url:
        exact=exact or any(same_fund_title(tag.get_text(' ',strip=True),family) for tag in soup.select('.fund-name,.fundname,.scheme-name,.heading,p.p-4'))
    if family=='Canara Robeco Small Cap Fund' and '/digital-factsheet/' in url:
        exact=exact or any('CANARA ROBECO SMALL CAP FUND'==tag.get_text(' ',strip=True).upper() for tag in soup.select('h1,h2,h3,h4'))
    if kotak_monthly:
        visible=re.sub(r'\s+',' ',soup.get_text(' ',strip=True))
        exact=exact or bool(re.search(r'\bKOTAK\s+SMALL\s+CAP\s+FUND\b',visible,re.I) and
                            re.search(r'predominantly\s+investing\s+in\s+small\s+cap\s+stocks',visible,re.I) and
                            re.search(r'Equity\s*&\s*Equity\s+related\s*-\s*Total',visible,re.I))
    if not exact:return 0
    text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True)).replace('Sept ','Sep ')
    if family=='Bank Of India Small Cap Fund':return boi_top_holdings(soup,text,url,h)
    if kotak_monthly:
        day=report_date(text)
        if not day or day>date.today().isoformat():return 0
        saved=kotak_portfolio(soup,day,url,h)
        if not saved:return 0
        a=re.search(r'\bAUM\s+Rs\s*([\d,.]+)\s*crs\b',text,re.I)
        if a and 0<number(a.group(1))<10_000_000:db.metric(family,'All','aum',day,number(a.group(1)),'INR crore',url,h)
        b=re.search(r'Benchmark[^A-Za-z0-9]+(NIFTY\s+Smallcap\s+250\s+TRI)',text,re.I)
        if b:db.metric(family,'All','benchmark',day,'NIFTY Smallcap 250 TRI','Reported',url,h)
        return saved
    patterns={
        'Axis Small Cap Fund':r'AUM \(In Cr\.\)\s*₹\s*([\d,.]+)\s*(As On [A-Za-z]+ \d{1,2}, \d{4})',
        'DSP Small Cap Fund':r'Total AUM\s*₹\s*([\d,.]+)\s*crores\s*(as of [A-Za-z]+ \d{1,2}, \d{4})',
        'Kotak Small Cap Fund':r'\bAUM:\s*₹\s*([\d,.]+)\s*Cr\.\s*(As on \d{1,2}-[A-Za-z]+-\d{4})',
        'Tata Small Cap Fund':r'Overview Fund Size \(\s*AUM\s*\)\s*₹\s*([\d,.]+)\s*Cr\s*(as on \d{1,2} [A-Za-z]+ \d{4})',
        'Bajaj Finserv Small Cap Fund':r'Total AUM\s*₹\s*([\d,.]+)\s*crores\s*(As on \d{1,2}-\d{1,2}-\d{4})',
        'Quantum Small Cap Fund':r'Asset Size \(in Crore\)\s*₹\s*([\d,.]+)\s*(as on \d{1,2}/\d{1,2}/\d{4})',
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
    elif family=='Canara Robeco Small Cap Fund' and '/digital-factsheet/' in url:
        d=re.search(r'\(as on ([A-Za-z]+ \d{1,2}, \d{4})\)',text,re.I)
        a=re.search(r'Month end Assets Under Management \(AUM\)[^₹]*₹\s*([\d,.]+)\s*Crores',text,re.I)
        if d and a:day=iso(d.group(1));value=number(a.group(1))
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
    saved=1
    if family=='Axis Small Cap Fund':
        from .report_parser import DATE,dated
        m=re.search(r'Expense Ratio\s*([\d.]+)%\s*As On\s*('+DATE+r')',text,re.I)
        if m and dated(m.group(2)) and 0<=float(m.group(1))<=5:
            # The page does not state TER versus BER. Preserve its own label.
            db.metric(family,'Direct','expense_ratio',dated(m.group(2)),float(m.group(1)),'% p.a.',url,h)
        saved+=axis_top_holdings(soup,text,url,h)
    if family=='Mahindra Manulife Small Cap Fund':
        from .report_parser import DATE,dated
        m=re.search(r'Base Expense Ratio\s*\d?\s*as on\s*('+DATE+r')\s*:\s*Regular Plan:\s*([\d.]+)%\s*Direct Plan:\s*([\d.]+)%',text,re.I)
        if m and dated(m.group(1)):
            for plan,v in zip(('Regular','Direct'),m.groups()[1:]):
                if 0<=float(v)<=5:db.metric(family,plan,'base_expense_ratio',dated(m.group(1)),float(v),'% p.a.',url,h)
        b=re.search(r'\bBenchmark\s*:?\s*(BSE\s*250\s*Small\s*Cap\s*TRI)\b',text,re.I)
        if b:db.metric(family,'All','benchmark',day,'BSE 250 Small Cap TRI','Reported',url,h)
        saved+=mahindra_portfolio(soup,day,url,h)
    if family=='Iti Small Cap Fund':
        saved+=iti_portfolio(soup,day,url,h)
    if family=='Canara Robeco Small Cap Fund':
        b=re.search(r'BENCHMARK\s+(Nifty\s+Smallcap\s+250\s+Index\s+TRI)',text,re.I)
        if b:db.metric(family,'All','benchmark',day,'Nifty Smallcap 250 Index TRI','Reported',url,h)
        saved+=canara_portfolio(soup,day,url,h)
    if family=='DSP Small Cap Fund':
        m=re.search(r'Base Expense Ratio\s*([\d.]+)%\s*(as of [A-Za-z]+ \d{1,2}, \d{4})',text,re.I)
        if m:db.metric(family,'Direct','base_expense_ratio',report_date(m.group(2)),number(m.group(1)),'% p.a.',url,h)
    # Only unambiguous fund-level benchmark text in the summary region.
    if family=='DSP Small Cap Fund' and re.search(r'Benchmark:\s*BSE 250 Small Cap TRI',text,re.I):db.metric(family,'All','benchmark',date.today().isoformat(),'BSE 250 Small Cap TRI','Observed on official fund page',url,h)
    if family=='Axis Small Cap Fund' and re.search(r'Benchmark Returns.{0,35}NIFTY Smallcap 250 TRI',text,re.I):db.metric(family,'All','benchmark',date.today().isoformat(),'Nifty Smallcap 250 TRI','Observed on official fund page',url,h)
    return saved


def update(progress=lambda _:None):
    saved=0;gaps=[]
    pages=list(PAGES)
    for offset in range(3):
        today=date.today();year,month=divmod(today.year*12+today.month-1-offset,12);month+=1;name=calendar.month_name[month]
        pages.extend([
            ('Baroda','Baroda Bnp Paribas Small Cap Fund',f'https://www.barodabnpparibasmf.in/efactsheet/{name[:3]}{year}/Innerpages/Small-cap.html'),
            ('Mahindra','Mahindra Manulife Small Cap Fund',f'https://www.mahindramanulife.com/digital-factsheet/{name.lower()}-{year}/Equity-funds/Small-Cap-Fund.html'),
            ('ITI','Iti Small Cap Fund',f'https://www.itiamc.com/digitalfactsheet/{name}{year}/innerpages/Small-Cap.html'),
            ('Kotak','Kotak Small Cap Fund',f'https://www.kotakmf.com/factsheet/{name}_{year}/kotak/SMALL-CAP.html'),
        ])
    for amc,family,url in pages:
        if not db.one('SELECT code FROM schemes WHERE family=?',(family,)):continue
        progress('Official AUM · '+family)
        with db.connect() as c:c.execute('INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)',(amc,url,'Fund figures and publications'))
        try:
            can_crawl(url);body,h,_=fetch(url);count=parse_page(body,family,url,h);saved+=count
            did=save_document(family,'Monthly digital factsheet' if 'factsheet/' in url.lower() else 'Official fund page',url,'factsheet' if 'factsheet/' in url.lower() else 'source page','Fund',origin='AMC');doc_version(did,h)
            status='Checked' if count else 'Limited';detail='Dated fund facts/holdings extracted; original page archived' if count else 'No unambiguous dated fund facts/holdings could be extracted'
            if not count:gaps.append(family)
        except Exception as e:status='Gap';detail=str(e)[:350];gaps.append(family)
        with db.connect() as c:c.execute('UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE amc_match=? AND url=?',(db.now(),status,detail,amc,url))
    return f'{saved} official fund reports with dated AUM'+('; some reporting pages unavailable for: '+', '.join(sorted(set(gaps))) if gaps else '')
