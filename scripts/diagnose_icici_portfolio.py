"""One-time read-only diagnostic for ICICI's current monthly portfolio route."""
from __future__ import annotations
import re,sys
from pathlib import Path
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGES=(
    'https://www.icicipruamc.com/media-center/downloads?currentTabFilter=otherSchemeDisclosures&subCatTabFilter=MonthlyPortfolioDisclosures',
    'https://www.icicipruamc.com/media-center/downloads?currentTabFilter=otherSchemeDisclosures&&subCatTabFilter=MonthlyPortfolioDisclosures',
)
TERMS=('MonthlyPortfolioDisclosures','Monthly Portfolio Disclosures','otherSchemeDisclosures',
       'monthly portfolio','download','api/','portfolio')

def inspect_page(page):
    providers.can_crawl(page)
    raw,_,mime=providers.fetch(page,archive=False,max_bytes=15*1024*1024)
    print(f'ICICI_MEDIA_PAGE {page} bytes={len(raw)} mime={mime}',flush=True)
    text=raw.decode('utf-8','ignore')
    soup=BeautifulSoup(raw,'html.parser')
    links=providers.candidate_links(soup,page)
    for url,title in links.items():
        joined=url+' '+str(title)
        if any(re.search(re.escape(term),joined,re.I) for term in TERMS) or re.search(r'\.zip|\.xlsx?|\.xls|portfolio',joined,re.I):
            print('ICICI_MEDIA_LINK '+url+' :: '+str(title)[:1200],flush=True)
    scripts=[]
    for tag in soup.find_all('script'):
        src=tag.get('src')
        body=tag.string or tag.get_text('',strip=False) or ''
        if src:
            u=urljoin(page,src)
            host=(urlparse(u).hostname or '').lower()
            if host.endswith('icicipruamc.com'):
                scripts.append(u);print('ICICI_MEDIA_SCRIPT '+u,flush=True)
        elif body and any(re.search(re.escape(term),body,re.I) for term in TERMS):
            print('ICICI_MEDIA_INLINE '+re.sub(r'\s+',' ',body)[:9000],flush=True)
    for term in TERMS:
        for m in list(re.finditer(re.escape(term),text,re.I))[:10]:
            ctx=re.sub(r'\s+',' ',text[max(0,m.start()-2500):m.end()+5000])
            print(f'ICICI_MEDIA_HTML_CONTEXT {term} '+ctx[:9000],flush=True)
    for idx,u in enumerate(scripts[-12:]):
        try:
            providers.can_crawl(u)
            body,_,_=providers.fetch(u,archive=False,max_bytes=20*1024*1024)
            js=body.decode('utf-8','ignore')
            hits=[]
            for term in TERMS:
                for m in list(re.finditer(re.escape(term),js,re.I))[:10]:
                    ctx=re.sub(r'\s+',' ',js[max(0,m.start()-4500):m.end()+7500])
                    hits.append((term,ctx[:12000]))
            if hits:
                print(f'ICICI_MEDIA_BUNDLE {idx} {u} bytes={len(body)} hits={len(hits)}',flush=True)
                for term,ctx in hits[:24]:
                    print(f'ICICI_MEDIA_JS_CONTEXT {term} '+ctx,flush=True)
        except Exception as exc:
            print(f'ICICI_MEDIA_SCRIPT_ERROR {u} :: {(str(exc) or type(exc).__name__).splitlines()[0][:500]}',flush=True)

def main():
    for page in PAGES:
        try:inspect_page(page)
        except Exception as exc:
            print(f'ICICI_MEDIA_ERROR {page} :: {(str(exc) or type(exc).__name__).splitlines()[0][:600]}',flush=True)

if __name__=='__main__':main()
