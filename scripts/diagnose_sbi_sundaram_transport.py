"""Focused read-only transport probe for SBI/Sundaram communications."""
from pathlib import Path
import re,sys
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

SBI_OUTLOOK="https://www.sbimf.com/learn-about-mutual-funds/2026-outlook"
SBI_CIO="https://www.sbimf.com/cio-desk"
SUNDARAM_HOME="https://www.sundarammutual.com/"
SUNDARAM_KH="https://www.sundarammutual.com/knowledge-hub"
SUNDARAM_PDFS=[
    f"https://blog.sundarammutual.com/Documents/outlook-{m}-2026.pdf"
    for m in ("june","july","august","september")
]

def probe_sbi():
    for url in (SBI_OUTLOOK,SBI_CIO):
        try:
            providers.can_crawl(url)
            body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            soup=BeautifulSoup(body,"html.parser")
            text=" ".join(soup.stripped_strings)
            print("COMM9_SBI",url,len(body),typ,repr(text[:3500]),flush=True)
            for script in soup.select("script[src]"):
                src=urljoin(url,script.get("src",""))
                if (urlparse(src).hostname or "").endswith("sbimf.com") and (
                    "/Content/Service/" in src or "cio" in src.lower() or "home" in src.lower()):
                    print("COMM9_SBI_SCRIPT",src,flush=True)
                    try:
                        raw,_,st=providers.fetch(src,archive=False,max_bytes=3*1024*1024)
                        js=raw.decode("utf-8","ignore")
                        for token in ("cio","outlook","monthly","ajax","api/","Get"):
                            i=js.lower().find(token.lower())
                            if i>=0:
                                print("COMM9_SBI_JS",src,"token="+token,
                                      repr(js[max(0,i-2500):i+7000]),flush=True)
                    except Exception as exc:
                        print("COMM9_SBI_JS_ERROR",src,(str(exc) or type(exc).__name__)[:500],flush=True)
        except Exception as exc:
            print("COMM9_SBI_ERROR",url,(str(exc) or type(exc).__name__)[:1200],flush=True)

def probe_sundaram():
    for url in (SUNDARAM_HOME,SUNDARAM_KH):
        try:
            providers.can_crawl(url)
            body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            soup=BeautifulSoup(body,"html.parser")
            raw=body.decode("utf-8","ignore")
            print("COMM9_SUNDARAM",url,len(body),typ,flush=True)
            for token in ("Outlook September 2026","Knowledge Hub","knowledge-hub","GetKnowledge","outlook"):
                start=0
                for _ in range(8):
                    i=raw.lower().find(token.lower(),start)
                    if i<0:break
                    print("COMM9_SUNDARAM_RAW",url,"token="+token,"index="+str(i),
                          repr(raw[max(0,i-3500):i+8000]),flush=True)
                    start=i+len(token)
            for script in soup.select("script[src]"):
                src=urljoin(url,script.get("src",""))
                if (urlparse(src).hostname or "").endswith("sundarammutual.com"):
                    low=src.lower()
                    if any(k in low for k in ("home","knowledge","custom","site","script")):
                        print("COMM9_SUNDARAM_SCRIPT",src,flush=True)
        except Exception as exc:
            print("COMM9_SUNDARAM_ERROR",url,(str(exc) or type(exc).__name__)[:1200],flush=True)

    for url in SUNDARAM_PDFS:
        try:
            providers.can_crawl(url)
            body,_,typ=providers.fetch(url,archive=False,max_bytes=8*1024*1024)
            print("COMM9_SUNDARAM_PDF",url,len(body),typ,body[:8],flush=True)
        except Exception as exc:
            print("COMM9_SUNDARAM_PDF_ERROR",url,(str(exc) or type(exc).__name__)[:900],flush=True)

if __name__=="__main__":
    probe_sbi()
    probe_sundaram()
