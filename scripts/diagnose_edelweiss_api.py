"""One-time read-only Edelweiss statutory API contract probe."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urljoin,urlparse
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGE='https://www.edelweissmf.com/statutory'

def get(url,params=None,max_bytes=20*1024*1024):
    host=(urlparse(url).hostname or '').lower()
    if not (host.endswith('edelweissmf.com') or 'edelweiss' in host):
        raise ValueError('Refusing non-Edelweiss diagnostic host: '+host)
    with httpx.Client(timeout=httpx.Timeout(30,read=60),follow_redirects=True,
                      headers={'User-Agent':'Mozilla/5.0'}) as client:
        r=client.get(url,params=params);r.raise_for_status()
        body=r.content
    if len(body)>max_bytes:raise ValueError('response too large')
    return body,r.headers.get('content-type',''),str(r.url)

def main():
    raw,_,_=get(PAGE)
    soup=BeautifulSoup(raw,'html.parser')
    main_url=None
    for tag in soup.find_all('script'):
        src=tag.get('src')
        if src and re.search(r'/main\.[A-Za-z0-9]+\.js(?:[?#]|$)',src,re.I):
            main_url=urljoin(PAGE,src);break
    if not main_url:raise ValueError('main bundle missing')
    body,_,_=get(main_url,max_bytes=8*1024*1024)
    js=body.decode('utf-8','ignore')
    env=re.search(r'45312:\(.*?const i=\{(.{0,5000}?)\}\s*[,;]',js,re.S)
    scope=env.group(1) if env else js
    urls=re.findall(r'(?:URL|BASE_URL):"([^"]+)"',scope)
    print('EDELWEISS_API_BUNDLE '+main_url+' bytes='+str(len(body)),flush=True)
    print('EDELWEISS_API_ENV_URLS '+json.dumps(urls),flush=True)
    api=next((u for u in urls if u.startswith('https://') and 'edelweiss' in u.lower()
              and u.rstrip('/')!='https://www.edelweissmf.com'),None)
    if not api:
        # fallback: find the URL directly adjacent to production/URL keys
        m=re.search(r'production:!0,URL:"(https://[^"]+)"',js)
        api=m.group(1) if m else None
    if not api:raise ValueError('Edelweiss API base URL not resolved from live bundle')
    api=api.rstrip('/')+'/'
    print('EDELWEISS_API_BASE '+api,flush=True)

    tests=[
      ('menus','mf/statutory-menus',{'type':'Statutory','fundType':'MF'}),
      ('single','mf/statutory-menus/single',
       {'type':'Statutory','fundType':'MF','menuName':'Portfolio of scheme(s)'}),
      ('legacy_menu','third-party/getStatutoryMenu',None),
    ]
    for label,path,params in tests:
        try:
            b,mime,final=get(urljoin(api,path),params=params,max_bytes=12*1024*1024)
            txt=b.decode('utf-8','ignore')
            print(f'EDELWEISS_API_RESPONSE {label} status=ok bytes={len(b)} mime={mime} final={final}',flush=True)
            print(f'EDELWEISS_API_PAYLOAD {label} '+re.sub(r'\s+',' ',txt)[:50000],flush=True)
        except Exception as exc:
            print(f'EDELWEISS_API_ERROR {label} {(str(exc) or type(exc).__name__).splitlines()[0][:700]}',flush=True)

if __name__=='__main__':main()
