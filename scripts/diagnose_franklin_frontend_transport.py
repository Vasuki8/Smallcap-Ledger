"""Read-only probe of Franklin's public frontend transport for communication indexes."""
from pathlib import Path
import re,sys
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers

URL="https://www.franklintempletonindia.com/sebi-circular/current"
KEYS=("sebi-circular","latest-commentaries","market-insights","widen.net","api/","graphql","search","circular","commentary","contentapi","endpoint")

def main():
    body,_,_=providers.fetch(URL,archive=False,max_bytes=8*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    print("FRONTEND_BYTES",len(body),flush=True)
    base_tag=soup.find("base")
    browser_base=urljoin(URL,base_tag.get("href")) if base_tag and base_tag.get("href") else URL
    print("FRONTEND_BASE",repr(base_tag.get("href") if base_tag else None),browser_base,flush=True)
    scripts=[]
    for tag in soup.select("script"):
        src=tag.get("src")
        inline=(tag.string or tag.get_text() or "")
        if src:
            u=urljoin(browser_base,src)
            if (urlparse(u).hostname or "").endswith("franklintempletonindia.com"):
                scripts.append(u)
                print("FRONTEND_SCRIPT_SRC",u,flush=True)
        if inline:
            low=inline.lower()
            if any(k in low for k in KEYS):
                print("FRONTEND_INLINE",repr(inline[:7000]),flush=True)
    for u in scripts[:30]:
        try:
            raw,_,typ=providers.fetch(u,archive=False,max_bytes=6*1024*1024)
        except Exception as exc:
            print("FRONTEND_SCRIPT_ERROR",u,(str(exc) or type(exc).__name__)[:500],flush=True)
            continue
        text=raw.decode("utf-8","ignore")
        low=text.lower()
        if not any(k in low for k in KEYS):continue
        print("FRONTEND_SCRIPT_MATCH",u,f"bytes={len(raw)} type={typ}",flush=True)
        for key in KEYS:
            start=0
            for _ in range(6):
                i=low.find(key,start)
                if i<0:break
                print("FRONTEND_MATCH",u,"key="+key,repr(text[max(0,i-800):i+1800]),flush=True)
                start=i+len(key)
    # Also expose all absolute Franklin API-looking URLs already present in shell/scripts.
    seen=set()
    for u in scripts[:30]:
        pass

if __name__=="__main__":main()
