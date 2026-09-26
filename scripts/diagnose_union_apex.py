"""One-time read-only diagnostic for Union Mutual Fund apex portfolio routes."""
from __future__ import annotations
import re,sys
from pathlib import Path
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGES=(
    'https://unionmf.com/about-us/downloads/monthly-portfolio',
    'https://unionmf.com/funddetail/union-small-cap-fund',
)

def main():
    for page in PAGES:
        try:
            providers.can_crawl(page)
            raw,_,mime=providers.fetch(page,archive=False,max_bytes=12*1024*1024)
            print(f'UNION_APEX_PAGE {page} bytes={len(raw)} mime={mime}',flush=True)
            text=raw.decode('utf-8','ignore')
            soup=BeautifulSoup(raw,'html.parser')
            for url,title in providers.candidate_links(soup,page).items():
                joined=(url+' '+str(title))
                if re.search(r'portfolio|monthly|small.?cap|xlsx?|xls|pdf|download',joined,re.I):
                    print('UNION_APEX_LINK '+url+' :: '+str(title)[:900],flush=True)
            for tag in soup.find_all('script'):
                src=tag.get('src')
                body=tag.string or tag.get_text('',strip=False) or ''
                if src:
                    url=urljoin(page,src)
                    if (urlparse(url).hostname or '').endswith('unionmf.com'):
                        print('UNION_APEX_SCRIPT '+url,flush=True)
                elif body and re.search(r'portfolio|monthly|download|api',body,re.I):
                    print('UNION_APEX_INLINE '+re.sub(r'\s+',' ',body)[:5000],flush=True)
            for term in ('monthly-portfolio','Monthly Portfolio','portfolio','api/','Ajax','download'):
                for m in list(re.finditer(re.escape(term),text,re.I))[:8]:
                    ctx=re.sub(r'\s+',' ',text[max(0,m.start()-1800):m.end()+2600])
                    print(f'UNION_APEX_CONTEXT {term} '+ctx[:5000],flush=True)
        except Exception as exc:
            print(f'UNION_APEX_ERROR {page} :: {(str(exc) or type(exc).__name__).splitlines()[0][:500]}',flush=True)

if __name__=='__main__':main()
