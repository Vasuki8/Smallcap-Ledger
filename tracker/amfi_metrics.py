"""AMC-reported fund figures distributed through AMFI's public website."""
from __future__ import annotations
import json
import re
from datetime import date
from urllib.parse import urlencode
from . import db
from .providers import fetch,number,iso

BASE='https://www.amfiindia.com'
TER_PAGE=BASE+'/ter-of-mf-schemes'


def normalized(value):return re.sub('[^a-z0-9]','',str(value).split('(')[0].lower())


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
