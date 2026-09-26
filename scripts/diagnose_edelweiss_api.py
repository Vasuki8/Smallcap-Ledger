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
FALLBACK_BUNDLE='https://www.edelweissmf.com/main.0411e4933dfdb2cb.js'

def get(url,params=None,max_bytes=20*1024*1024,headers=None):
    host=(urlparse(url).hostname or '').lower()
    if not (host.endswith('edelweissmf.com') or 'edelweiss' in host):
        raise ValueError('Refusing non-Edelweiss diagnostic host: '+host)
    request_headers={'User-Agent':'Mozilla/5.0'}
    request_headers.update(headers or {})
    with httpx.Client(timeout=httpx.Timeout(30,read=60),follow_redirects=True,
                      headers=request_headers) as client:
        r=client.get(url,params=params);r.raise_for_status()
        body=r.content
    if len(body)>max_bytes:raise ValueError('response too large')
    return body,r.headers.get('content-type',''),str(r.url)

def main():
    main_url=None
    try:
        raw,_,_=get(PAGE)
        soup=BeautifulSoup(raw,'html.parser')
        for tag in soup.find_all('script'):
            src=tag.get('src')
            if src and re.search(r'/main\.[A-Za-z0-9]+\.js(?:[?#]|$)',src,re.I):
                main_url=urljoin(PAGE,src);break
        print('EDELWEISS_API_PAGE status=ok bundle='+(main_url or 'missing'),flush=True)
    except Exception as exc:
        print('EDELWEISS_API_PAGE status=unavailable detail='+
              (str(exc) or type(exc).__name__).splitlines()[0][:500],flush=True)
    main_url=main_url or FALLBACK_BUNDLE
    try:
        body,_,_=get(main_url,max_bytes=8*1024*1024)
    except Exception as exc:
        print('EDELWEISS_API_BUNDLE_ERROR '+
              (str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
        return
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
    if not api:
        print('EDELWEISS_API_BASE unresolved',flush=True)
        return
    api=api.rstrip('/')+'/'
    print('EDELWEISS_API_BASE '+api,flush=True)
    for label,pattern in (
        ('x_api_key',r'x[-_ ]?api[-_ ]?key'),
        ('subscription',r'subscription[-_ ]?key|ocp-apim'),
        ('client_key',r'x[-_ ]?(?:client|app)[-_ ]?(?:id|key)'),
        ('interceptor',r'interceptor'),
    ):
        matches=list(re.finditer(pattern,js,re.I))
        print(f'EDELWEISS_API_HEADER_TERM {label} count={len(matches)}',flush=True)
        for idx,m in enumerate(matches[:8]):
            ctx=re.sub(r'\s+',' ',js[max(0,m.start()-700):m.end()+1200])
            print(f'EDELWEISS_API_HEADER_CONTEXT {label} {idx} '+ctx[:1900],flush=True)
    api_host=(urlparse(api).hostname or '').lower()
    if not (api_host.endswith('edelweissmf.com') or 'edelweiss' in api_host):
        print('EDELWEISS_API_BASE_UNVERIFIED_HOST '+api_host,flush=True)
        return

    tests=[
      ('menus','mf/statutory-menus',{'type':'Statutory','fundType':'MF'}),
      ('single','mf/statutory-menus/single',
       {'type':'Statutory','fundType':'MF','menuName':'Portfolio of scheme(s)'}),
      ('legacy_menu','third-party/getStatutoryMenu',None),
    ]
    profiles=[
        ('bare',{}),
        ('browser',{
            'Accept':'application/json, text/plain, */*',
            'Origin':'https://www.edelweissmf.com',
            'Referer':'https://www.edelweissmf.com/statutory',
            'Sec-Fetch-Site':'same-site',
            'Sec-Fetch-Mode':'cors',
            'Sec-Fetch-Dest':'empty',
        }),
    ]
    for label,path,params in tests:
        for profile,headers in profiles:
            try:
                b,mime,final=get(urljoin(api,path),params=params,max_bytes=12*1024*1024,
                                 headers=headers)
                txt=b.decode('utf-8','ignore')
                print(f'EDELWEISS_API_RESPONSE {label} profile={profile} status=ok bytes={len(b)} mime={mime} final={final}',flush=True)
                print(f'EDELWEISS_API_PAYLOAD {label} profile={profile} '+re.sub(r'\s+',' ',txt)[:50000],flush=True)
            except Exception as exc:
                print(f'EDELWEISS_API_ERROR {label} profile={profile} {(str(exc) or type(exc).__name__).splitlines()[0][:700]}',flush=True)

if __name__=='__main__':main()
