"""One-time read-only ICICI monthly portfolio contract diagnostic."""
from __future__ import annotations
import re,sys
from pathlib import Path
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGE=('https://www.icicipruamc.com/news-and-media/downloads'
      '?currentTabFilter=OtherSchemeDisclosures&subCatTabFilter=Monthly%20Portfolio%20Disclosures')
TERMS=('Monthly Portfolio Disclosures','OtherSchemeDisclosures','monthly portfolio',
       'download','api/','blob/downloads','portfolio')

def main():
    try:
        providers.can_crawl(PAGE)
        raw,_,mime=providers.fetch(PAGE,archive=False,max_bytes=12*1024*1024)
        print(f'ICICI_PORTFOLIO_PAGE bytes={len(raw)} mime={mime}',flush=True)
        text=raw.decode('utf-8','ignore')
        soup=BeautifulSoup(raw,'html.parser')
        scripts=[]
        for tag in soup.find_all('script'):
            src=tag.get('src')
            body=tag.string or tag.get_text('',strip=False) or ''
            if src:
                u=urljoin(PAGE,src)
                host=(urlparse(u).hostname or '').lower()
                if host.endswith('icicipruamc.com'):
                    scripts.append(u)
                    print('ICICI_PORTFOLIO_SCRIPT '+u,flush=True)
            elif body and any(re.search(re.escape(t),body,re.I) for t in TERMS):
                print('ICICI_PORTFOLIO_INLINE '+re.sub(r'\s+',' ',body)[:7000],flush=True)
        for term in TERMS:
            for m in list(re.finditer(re.escape(term),text,re.I))[:8]:
                ctx=re.sub(r'\s+',' ',text[max(0,m.start()-2200):m.end()+3600])
                print(f'ICICI_PORTFOLIO_HTML_CONTEXT {term} '+ctx[:6500],flush=True)
        for idx,u in enumerate(scripts[-8:]):
            try:
                providers.can_crawl(u)
                body,_,_=providers.fetch(u,archive=False,max_bytes=15*1024*1024)
                js=body.decode('utf-8','ignore')
                hits=[]
                for term in TERMS:
                    for m in list(re.finditer(re.escape(term),js,re.I))[:8]:
                        ctx=re.sub(r'\s+',' ',js[max(0,m.start()-3000):m.end()+5000])
                        hits.append((term,ctx[:8500]))
                if hits:
                    print(f'ICICI_PORTFOLIO_BUNDLE {idx} {u} bytes={len(body)} hits={len(hits)}',flush=True)
                    for term,ctx in hits[:20]:
                        print(f'ICICI_PORTFOLIO_JS_CONTEXT {term} '+ctx,flush=True)
            except Exception as exc:
                print(f'ICICI_PORTFOLIO_SCRIPT_ERROR {u} :: {(str(exc) or type(exc).__name__).splitlines()[0][:400]}',flush=True)
    except Exception as exc:
        print(f'ICICI_PORTFOLIO_ERROR {(str(exc) or type(exc).__name__).splitlines()[0][:500]}',flush=True)

if __name__=='__main__':main()
