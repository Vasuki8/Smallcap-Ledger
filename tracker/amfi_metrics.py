"""AMC-reported fund figures distributed through AMFI's public website."""
from __future__ import annotations
import json
import re
from datetime import date,timedelta
import httpx
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from . import db
from .providers import fetch,number,iso

BASE='https://www.amfiindia.com'
TER_PAGE=BASE+'/ter-of-mf-schemes'
PERFORMANCE_PAGE=BASE+'/otherdata/fund-performance'
POLLING_BASE=BASE+'/gateway/pollingsebi'
PERFORMANCE_FILTERS='/api/amfi/fundperformancefilters'
PERFORMANCE_SUBCATEGORY='/api/amfi/getsubcategory'
PERFORMANCE_DATA='/api/amfi/fundperformance'
PORTFOLIO_DISCLOSURE='https://portal.amfiindia.com/DownloadSchemeData_Po.aspx'


def normalized(value):return re.sub('[^a-z0-9]','',str(value).split('(')[0].lower())


def inspect_portfolio_response(content,family):
    """Return read-only diagnostics for AMFI's scheme portfolio response."""
    soup=BeautifulSoup(content,'html.parser')
    page_text=' '.join(soup.stripped_strings)
    tables=soup.find_all('table')
    table_info=[]
    for table in tables:
        rows=[]
        for tr in table.find_all('tr'):
            cells=[' '.join(x.stripped_strings) for x in tr.find_all(['th','td'])]
            if cells:rows.append(cells)
        table_info.append(rows)
    largest=max(table_info,key=len,default=[])
    headers=largest[0] if largest else []
    pct_cells=0
    for row in largest[1:]:
        for value in row:
            if re.fullmatch(r'-?[\d,]+(?:\.\d+)?\s*%?',value.strip()):
                try:
                    n=number(value)
                    if -100<=n<=100:pct_cells+=1
                except ValueError:
                    pass
    expected=normalized(family)
    visible=normalized(page_text)
    dates=re.findall(r'\b(?:\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',page_text)
    return {
        'bytes':len(content),
        'tables':len(tables),
        'largest_table_rows':len(largest),
        'largest_table_columns':max((len(r) for r in largest),default=0),
        'headers':headers[:12],
        'family_visible':bool(expected and expected in visible),
        'date_mentions':dates[:6],
        'numeric_cells':pct_cells,
        'sample_rows':[row[:6] for row in largest[1:4]],
    }


def probe_portfolio_endpoint(families=('Bank Of India Small Cap Fund','Edelweiss Small Cap Fund')):
    """Probe the public AMFI scheme-portfolio endpoint without storing its data."""
    today=date.today()
    year,month=divmod(today.year*12+today.month-2,12);month+=1
    diagnostics=[]
    for family in families:
        scheme=db.one("""SELECT code,name,family,plan,option FROM schemes WHERE family=?
          ORDER BY CASE WHEN plan='Direct' AND option='Growth' THEN 0
                        WHEN option='Growth' THEN 1 ELSE 2 END,code LIMIT 1""",(family,))
        if not scheme:
            diagnostics.append({'family':family,'status':'missing_scheme_code'})
            continue
        params={'mession':'24','mession_code':scheme['code'],'mf':month,'yr':year,'myession':'S'}
        url=PORTFOLIO_DISCLOSURE+'?'+urlencode(params)
        try:
            body,_,typ=fetch(url,archive=False,max_bytes=5*1024*1024)
            info=inspect_portfolio_response(body,family)
            info.update({'family':family,'scheme_code':scheme['code'],'plan':scheme['plan'],
                         'option':scheme['option'],'month':month,'year':year,
                         'content_type':typ,'status':'ok'})
        except Exception as e:
            info={'family':family,'scheme_code':scheme['code'],'month':month,'year':year,
                  'status':'unavailable','detail':(str(e) or type(e).__name__)[:220]}
        diagnostics.append(info)
    return diagnostics


def save_fees(records,source,content_hash):
    families={normalized(r['family']):r['family'] for r in db.rows('SELECT DISTINCT family FROM schemes')}
    count=0;matched=set();unmatched=set();values=[];observed=db.now()
    for r in records:
        family=families.get(normalized(r.get('Scheme_Name','')))
        if not family:unmatched.add(r.get('Scheme_Name',''));continue
        day=iso(str(r.get('TER_Date',''))[:10])
        if day>date.today().isoformat():continue
        if 'small cap' not in r.get('SchemeCat_Desc','').lower():continue
        for prefix,plan in [('R','Regular'),('D','Direct')]:
            for field,metric in [('TER','ter'),('BER','base_expense_ratio'),('BaseTER','base_ter'),('BrokerageCost','brokerage'),('TransactionCost','transaction_cost'),('StatutoryLevies','statutory_levies')]:
                raw=r.get(prefix+'_'+field)
                if raw is None or str(raw).strip() in ('','-','NA','N/A'):continue
                value=number(raw)
                if not 0<=value<=10:continue
                values.append((family,plan,metric,day,str(value),'% p.a. · reported by AMC via AMFI',source,content_hash,observed))
                count+=1;matched.add(family)
    with db.connect() as c:c.executemany('INSERT OR IGNORE INTO metrics(family,plan,metric,as_of,value,unit,source,hash,observed_at) VALUES(?,?,?,?,?,?,?,?,?)',values)
    return count,matched,unmatched



def save_daily_aum(records,source,content_hash):
    """Store dated scheme-level daily AUM from AMFI without replacing older observations."""
    families={normalized(r['family']):r['family'] for r in db.rows('SELECT DISTINCT family FROM schemes')}
    values=[];matched=set();unmatched=set();observed=db.now()
    for r in records:
        scheme=str(r.get('schemeName','')).strip()
        family=families.get(normalized(scheme))
        if not family:
            if scheme:unmatched.add(scheme)
            continue
        raw=r.get('dailyAUM')
        if raw is None or str(raw).strip() in ('','-','NA','N/A'):continue
        try:
            value=number(raw);day=iso(r.get('navDate',''))
        except ValueError:
            continue
        if value<=0 or day>date.today().isoformat():continue
        values.append((family,'All','aum',day,str(value),'₹ crore · daily scheme AUM · AMC-reported via AMFI',source,content_hash,observed))
        matched.add(family)
    with db.connect() as c:
        c.executemany('INSERT OR IGNORE INTO metrics(family,plan,metric,as_of,value,unit,source,hash,observed_at) VALUES(?,?,?,?,?,?,?,?,?)',values)
    return len(values),matched,unmatched


def _performance_json(client,path,payload):
    r=client.post(path,json=payload)
    r.raise_for_status()
    if len(r.content)>8*1024*1024:raise ValueError('AMFI fund-performance response is unexpectedly large')
    data=r.json()
    return r,data.get('data',data) if isinstance(data,dict) else data


def daily_aum(progress=lambda _:None,lookback_days=12):
    """Fetch the latest available official AMFI daily scheme AUM for small-cap funds."""
    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Accept':'application/json, text/plain, */*',
        'Referer':PERFORMANCE_PAGE,
    }
    families={normalized(r['family']):r['family'] for r in db.rows('SELECT DISTINCT family FROM schemes')}
    if not families:raise ValueError('No small-cap schemes are available for AMFI AUM matching')
    with httpx.Client(base_url=POLLING_BASE,headers=headers,timeout=60,follow_redirects=True) as client:
        progress('AMFI daily AUM · resolving official filters')
        _,filters=_performance_json(client,PERFORMANCE_FILTERS,{})
        if not isinstance(filters,dict):raise ValueError('AMFI fund-performance filters changed format')
        maturity=next((x for x in filters.get('maturityTypeList',[]) if 'open' in str(x.get('name','')).lower()),None)
        equity=next((x for x in filters.get('investmentTypeList',[]) if str(x.get('name','')).strip().lower()=='equity'),None)
        if not maturity or not equity:raise ValueError('AMFI fund-performance filters no longer identify open-ended equity')
        _,subs=_performance_json(client,PERFORMANCE_SUBCATEGORY,{'category':equity.get('id')})
        if not isinstance(subs,list):raise ValueError('AMFI small-cap subcategory response changed format')
        small=next((x for x in subs if 'small' in str(x.get('name','')).lower() and 'cap' in str(x.get('name','')).lower()),None)
        if not small:raise ValueError('AMFI fund-performance filters no longer identify Small Cap')
        for offset in range(lookback_days):
            day=date.today()-timedelta(days=offset)
            if day.weekday()>=5:continue
            label=day.strftime('%d-%b-%Y')
            progress('AMFI daily AUM · '+label)
            request={'maturityType':maturity.get('id'),'category':equity.get('id'),'subCategory':small.get('id'),'mfid':0,'reportDate':label}
            response,rows=_performance_json(client,PERFORMANCE_DATA,request)
            if not isinstance(rows,list):continue
            plausible=set()
            for row in rows:
                if not isinstance(row,dict):continue
                family=families.get(normalized(row.get('schemeName','')))
                if not family:continue
                try:value=number(row.get('dailyAUM'))
                except (TypeError,ValueError):continue
                if value>0:plausible.add(family)
            # A category-wide response should cover most of the known small-cap
            # universe. A sparse/wrong response is ignored rather than published.
            minimum=max(20,len(families)//2)
            if len(plausible)<minimum:continue
            h=db.archive(response.content,response.headers.get('content-type','application/json'))
            evidence=POLLING_BASE+PERFORMANCE_DATA+'?'+urlencode({'maturityType':request['maturityType'],'category':request['category'],'subCategory':request['subCategory'],'mfid':0,'reportDate':label})
            with db.connect() as c:
                c.execute("INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",(evidence,db.now(),'ok',h))
            count,matched,unmatched=save_daily_aum(rows,PERFORMANCE_PAGE,h)
            if len(matched)<minimum:raise ValueError('AMFI daily AUM rows did not match the retained small-cap universe')
            as_of=max(iso(r.get('navDate','')) for r in rows if isinstance(r,dict) and normalized(r.get('schemeName','')) in families and r.get('dailyAUM') not in (None,''))
            return f'{len(matched)} funds with official AMFI daily scheme AUM as of {as_of}; {count} dated values checked'+(' · unmatched names: '+', '.join(sorted(unmatched)) if unmatched else '')
    raise ValueError('AMFI fund-performance API returned no plausible recent small-cap daily AUM response')


def fees(progress=lambda _:None,months=3):
    today=date.today();total=0;matched=set();unmatched=set()
    for offset in range(months):
        year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
        label=f'{month:02d}-{year}'
        # Completed prior months are immutable unless a manual backfill is run.
        # Current and previous months are rechecked for AMC corrections.
        if offset>1 and db.setting('amfi_fee_month_'+label,False):continue
        page=1
        while True:
            progress('AMFI expense ratios · '+label+' · page '+str(page))
            url=BASE+'/api/populate-te-rdata-revised?'+urlencode({'MF_ID':'All','Month':label,'strCat':'18','strType':'1','page':page,'pageSize':1000})
            body,h,_=fetch(url);payload=json.loads(body)
            records=payload.get('data',[]) if isinstance(payload,dict) else payload
            if not isinstance(records,list):raise ValueError('AMFI expense response has changed')
            n,yes,no=save_fees(records,url,h);total+=n;matched.update(yes);unmatched.update(no)
            meta=payload.get('meta',{}) if isinstance(payload,dict) else {}
            pages=meta.get('totalPages') or meta.get('pageCount')
            if not records or (pages and page>=int(pages)) or (not pages and len(records)<int(meta.get('pageSize',1000))):break
            page+=1
            if page>20:raise ValueError('Unexpected size of the small-cap expense feed')
        with db.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('amfi_fee_month_'+label,'true'))
    return f'{len(matched)} funds with AMC-reported expense figures; {total} dated plan/fee values checked'+(' · unmatched fund names: '+', '.join(sorted(unmatched)) if unmatched else '')
