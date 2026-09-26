"""One-time read-only diagnostic for AMFI Portfolio Disclosure transport."""
from __future__ import annotations
import re,sys
from pathlib import Path
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGE='https://www.amfiindia.com/online-center/portfolio-disclosure'
TERMS=(
    'portfolio-disclosure','Portfolio Disclosure','portfolio','disclosure',
    'api/','xlsx','xls','download','mutual fund','scheme'
)

def main():
    try:
        providers.can_crawl(PAGE)
        raw,_,mime=providers.fetch(PAGE,archive=False,max_bytes=15*1024*1024)
        print(f'AMFI_PORTFOLIO_PAGE bytes={len(raw)} mime={mime}',flush=True)
        text=raw.decode('utf-8','ignore')
        soup=BeautifulSoup(raw,'html.parser')
        for url,title in providers.candidate_links(soup,PAGE).items():
            joined=url+' '+str(title)
            if any(re.search(re.escape(term),joined,re.I) for term in TERMS):
                print('AMFI_PORTFOLIO_LINK '+url+' :: '+str(title)[:1200],flush=True)
        scripts=[]
        for tag in soup.find_all('script'):
            src=tag.get('src')
            body=tag.string or tag.get_text('',strip=False) or ''
            if src:
                u=urljoin(PAGE,src)
                host=(urlparse(u).hostname or '').lower()
                if host.endswith('amfiindia.com'):
                    scripts.append(u);print('AMFI_PORTFOLIO_SCRIPT '+u,flush=True)
            elif body and any(re.search(re.escape(term),body,re.I) for term in TERMS):
                print('AMFI_PORTFOLIO_INLINE '+re.sub(r'\s+',' ',body)[:12000],flush=True)
        for term in TERMS:
            for m in list(re.finditer(re.escape(term),text,re.I))[:12]:
                ctx=re.sub(r'\s+',' ',text[max(0,m.start()-3000):m.end()+6000])
                print(f'AMFI_PORTFOLIO_HTML_CONTEXT {term} '+ctx[:11000],flush=True)
        for idx,u in enumerate(scripts[-20:]):
            try:
                providers.can_crawl(u)
                body,_,_=providers.fetch(u,archive=False,max_bytes=25*1024*1024)
                js=body.decode('utf-8','ignore')
                hits=[]
                for term in TERMS:
                    for m in list(re.finditer(re.escape(term),js,re.I))[:12]:
                        ctx=re.sub(r'\s+',' ',js[max(0,m.start()-5500):m.end()+9000])
                        hits.append((term,ctx[:14500]))
                if hits:
                    print(f'AMFI_PORTFOLIO_BUNDLE {idx} {u} bytes={len(body)} hits={len(hits)}',flush=True)
                    for term,ctx in hits[:30]:
                        print(f'AMFI_PORTFOLIO_JS_CONTEXT {term} '+ctx,flush=True)
            except Exception as exc:
                print(f'AMFI_PORTFOLIO_SCRIPT_ERROR {u} :: {(str(exc) or type(exc).__name__).splitlines()[0][:500]}',flush=True)
    except Exception as exc:
        print(f'AMFI_PORTFOLIO_ERROR {(str(exc) or type(exc).__name__).splitlines()[0][:700]}',flush=True)

if __name__=='__main__':main()
