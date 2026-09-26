"""Read-only ICICI monthly portfolio transport probe using current blob delivery."""
from __future__ import annotations
import sys
from pathlib import Path
from urllib.parse import urlparse
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

OLD=('https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/'
     '2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip')
BLOB=('https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/'
      '2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip')

def safe(url):
    host=(urlparse(url).hostname or '').lower()
    return host=='www.icicipruamc.com' or host.endswith('.icicipruamc.com')

def probe(url,follow):
    if not safe(url):raise ValueError('Refusing non-ICICI host')
    with httpx.Client(
        timeout=httpx.Timeout(30,read=60),follow_redirects=follow,
        headers={'User-Agent':'Mozilla/5.0','Accept':'*/*',
                 'Referer':'https://www.icicipruamc.com/'}) as client:
        r=client.get(url)
        print('ICICI_BLOB_HTTP url='+url+' follow='+str(follow).lower()+
              f' status={r.status_code} bytes={len(r.content)} content_type={r.headers.get("content-type","")}'+
              ' location='+str(r.headers.get('location') or '')+' final='+str(r.url),flush=True)
        return r

def main():
    try:
        old=probe(OLD,False)
        location=old.headers.get('location')
        if location and location.startswith('https://') and safe(location):
            try:probe(location,True)
            except Exception as exc:
                print('ICICI_REDIRECT_ERROR '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
    except Exception as exc:
        print('ICICI_OLD_ERROR '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
    try:
        r=probe(BLOB,True)
        print('ICICI_BLOB_SIGNATURE '+r.content[:32].hex(),flush=True)
        if r.status_code==200 and r.content.startswith(b'PK'):
            print('ICICI_BLOB_ZIP_OK bytes='+str(len(r.content)),flush=True)
    except Exception as exc:
        print('ICICI_BLOB_ERROR '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)

if __name__=='__main__':main()
