"""Focused read-only probe for SBI monthly-outlook transport and Sundaram knowledge-hub frontend data."""
from pathlib import Path
import re,sys
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

SBI="https://www.sbimf.com/monthly-outlook-videos"
SUNDARAM="https://www.sundarammutual.com/knowledge-hub"
TOKENS=(
    "outlook september 2026",
    "outlook august 2026",
    "outlook-june-2026",
    "knowledge hub",
    "knowledge-hub",
    "blog.sundarammutual.com/documents",
    "api/",
    "outlook",
)

def probe_sbi():
    print("COMM9_START SBI",SBI,flush=True)
    providers.can_crawl(SBI)
    body,_,typ=providers.fetch(SBI,archive=False,max_bytes=12*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    print("COMM9_HTTP SBI",len(body),typ,flush=True)
    for a in soup.find_all("a",href=True):
        href=urljoin(SBI,a.get("href",""))
        text=a.get_text(" ",strip=True)
        combined=(text+" "+href).lower()
        if "monthly market outlook" in combined:
            parent=a.parent
            print("COMM9_SBI_ITEM",
                  "text="+repr(text[:700]),
                  "href="+href,
                  "parent="+repr(parent.get_text(" ",strip=True)[:1200] if parent else ""),
                  "html="+repr(str(parent)[:6000] if parent else ""),flush=True)

def probe_sundaram():
    print("COMM9_START Sundaram",SUNDARAM,flush=True)
    providers.can_crawl(SUNDARAM)
    body,_,typ=providers.fetch(SUNDARAM,archive=False,max_bytes=12*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    print("COMM9_HTTP Sundaram",len(body),typ,flush=True)

    scripts=[]
    for tag in soup.find_all("script"):
        src=tag.get("src")
        raw=(tag.string or tag.get_text() or "")
        if src:
            u=urljoin(SUNDARAM,src)
            if (urlparse(u).hostname or "").endswith("sundarammutual.com"):
                scripts.append(u)
                print("COMM9_SUNDARAM_SCRIPT_SRC",u,flush=True)
        if raw:
            low=raw.lower()
            if any(t in low for t in TOKENS):
                print("COMM9_SUNDARAM_INLINE",repr(raw[:12000]),flush=True)

    for u in list(dict.fromkeys(scripts))[:40]:
        try:
            raw,_,stype=providers.fetch(u,archive=False,max_bytes=8*1024*1024)
        except Exception as exc:
            print("COMM9_SUNDARAM_SCRIPT_ERROR",u,(str(exc) or type(exc).__name__)[:500],flush=True)
            continue
        text=raw.decode("utf-8","ignore")
        low=text.lower()
        if not any(t in low for t in TOKENS):continue
        print("COMM9_SUNDARAM_SCRIPT_MATCH",u,len(raw),stype,flush=True)
        for token in TOKENS:
            start=0
            for _ in range(12):
                i=low.find(token,start)
                if i<0:break
                print("COMM9_SUNDARAM_CONTEXT",u,"token="+token,"index="+str(i),
                      repr(text[max(0,i-3500):i+7000]),flush=True)
                start=i+len(token)

if __name__=="__main__":
    probe_sbi()
    probe_sundaram()
