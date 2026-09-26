"""Read-only Bajaj first-party media catalog probe for monthly portfolio files."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlencode,urlparse
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

HOST='media.bajajamc.com'
BASE='https://media.bajajamc.com/wp-json/wp/v2'

def get(path,params):
    url=BASE+'/'+path+'?'+urlencode(params)
    if (urlparse(url).hostname or '').lower()!=HOST:
        raise ValueError('unexpected Bajaj media host')
    with httpx.Client(
        timeout=httpx.Timeout(30,read=60),follow_redirects=True,
        headers={
            'User-Agent':'Mozilla/5.0',
            'Accept':'application/json',
            'Referer':'https://www.bajajamc.com/downloads',
        }) as client:
        r=client.get(url)
        print(f'BAJAJ_MEDIA_HTTP path={path} search={params.get("search")} status={r.status_code} bytes={len(r.content)} content_type={r.headers.get("content-type","")}',flush=True)
        r.raise_for_status()
        return r.json()

def media_row(row):
    source=str(row.get('source_url') or '')
    title=((row.get('title') or {}).get('rendered') if isinstance(row.get('title'),dict) else row.get('title')) or ''
    caption=((row.get('caption') or {}).get('rendered') if isinstance(row.get('caption'),dict) else row.get('caption')) or ''
    return {
        'id':row.get('id'),'date':row.get('date'),'modified':row.get('modified'),
        'mime_type':row.get('mime_type'),'source_url':source,
        'title':re.sub(r'<[^>]+>',' ',str(title)),
        'caption':re.sub(r'<[^>]+>',' ',str(caption)),
    }

def main():
    found={}
    for term in ('portfolio','monthly portfolio','small cap','small-cap','smallcap'):
        try:
            rows=get('media',{'search':term,'per_page':100,'orderby':'date','order':'desc'})
            if not isinstance(rows,list):
                print(f'BAJAJ_MEDIA_UNEXPECTED search={term} type={type(rows).__name__}',flush=True)
                continue
            for row in rows:
                item=media_row(row)
                hay=' '.join(str(item.get(k) or '') for k in ('source_url','title','caption','mime_type'))
                if re.search(r'portfolio|small.?cap|xlsx?|xls|zip|csv',hay,re.I):
                    found[str(item['id'])]=item
        except Exception as exc:
            print(f'BAJAJ_MEDIA_ERROR search={term} {(str(exc) or type(exc).__name__).splitlines()[0][:700]}',flush=True)
    print('BAJAJ_MEDIA_MATCH_COUNT '+str(len(found)),flush=True)
    for item in sorted(found.values(),key=lambda x:str(x.get('date') or ''),reverse=True)[:100]:
        print('BAJAJ_MEDIA_MATCH '+json.dumps(item,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
