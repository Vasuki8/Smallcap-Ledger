"""Read-only probe of AMFI's centralized monthly scheme portfolio endpoint.

This script never archives or stores the response. It exists only to establish
whether AMFI exposes a reusable public portfolio feed for current tracker gaps.
"""
from __future__ import annotations
from pathlib import Path
import sys
import json
import re
from datetime import date
from urllib.parse import urlencode
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.providers import fetch

ENDPOINT='https://portal.amfiindia.com/DownloadSchemeData_Po.aspx'
FAMILIES=(
    'Bank Of India Small Cap Fund',
    'ICICI Prudential Small Cap Fund',
    'Jm Small Cap Fund',
    'Union Small Cap Fund',
    'Bandhan Small Cap Fund',
    'Quant Small Cap Fund',
    'Tata Small Cap Fund',
    'Trustmf Small Cap Fund',
    'Groww Small Cap Fund',
)

def response_shape(body:bytes,content_type:str|None):
    magic=body[:16].hex()
    kind='binary'
    if body.startswith(b'%PDF'):kind='pdf'
    elif body.startswith(b'PK\x03\x04'):kind='zip'
    elif body.startswith(b'\xd0\xcf\x11\xe0'):kind='ole-xls'
    elif b'<html' in body[:4096].lower() or b'<table' in body[:4096].lower():
        kind='html'
    out={'bytes':len(body),'content_type':content_type,'kind':kind,'magic':magic}
    if kind=='html':
        soup=BeautifulSoup(body,'html.parser')
        text=' '.join(soup.stripped_strings)
        tables=soup.find_all('table')
        links=[a.get('href','') for a in soup.select('a[href]') if a.get('href')]
        inputs=[x.get('name') or x.get('id') for x in soup.select('input,select') if x.get('name') or x.get('id')]
        out.update({
            'tables':len(tables),
            'largest_table_rows':max((len(t.find_all('tr')) for t in tables),default=0),
            'text_sample':re.sub(r'\s+',' ',text)[:500],
            'links':links[:8],
            'inputs':inputs[:20],
            'session_or_error':bool(re.search(r'session|login|application error|try again',text,re.I)),
        })
    return out

def main():
    db.init()
    today=date.today()
    year,month=divmod(today.year*12+today.month-2,12);month+=1
    rows=[]
    for family in FAMILIES:
        scheme=db.one("""SELECT code,name,plan,option FROM schemes WHERE family=?
          ORDER BY CASE WHEN plan='Direct' AND option='Growth' THEN 0
                        WHEN option='Growth' THEN 1 ELSE 2 END,code LIMIT 1""",(family,))
        if not scheme:
            rows.append({'family':family,'status':'missing_scheme'})
            continue
        params={'mession':'24','mession_code':scheme['code'],'mf':month,'yr':year,'myession':'S'}
        url=ENDPOINT+'?'+urlencode(params)
        try:
            body,_,typ=fetch(url,archive=False,max_bytes=5*1024*1024)
            row={'family':family,'scheme_code':scheme['code'],'scheme_name':scheme['name'],
                 'plan':scheme['plan'],'option':scheme['option'],'month':month,'year':year,
                 'status':'ok',**response_shape(body,typ)}
        except Exception as exc:
            row={'family':family,'scheme_code':scheme['code'],'month':month,'year':year,
                 'status':'unavailable','detail':(str(exc) or type(exc).__name__)[:300]}
        rows.append(row)
    print('AMFI_PORTFOLIO_PROBE='+json.dumps(rows,ensure_ascii=False,separators=(',',':')),flush=True)

if __name__=='__main__':
    main()
