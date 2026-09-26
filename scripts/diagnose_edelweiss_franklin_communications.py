"""Read-only live probe for Edelweiss and Franklin communication sources."""
from pathlib import Path
import sys
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url

SOURCES=(
    ("Edelweiss","https://www.edelweissmf.com/investor-insights/fund-market"),
    ("Edelweiss","https://www.edelweissmf.com/investor-insights/fund-market/factor-investing-2026-outlook"),
    ("Franklin","https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries"),
)
FRANKLIN_WIDEN="https://franklintempletonprod.widen.net/s/rrxmvxwmh9/ft-monthly-equity-market-outlook"

def probe_source(amc,url):
    print("COMM2_START",amc,url,flush=True)
    try:
        body,h,typ=providers.fetch(url,archive=False,max_bytes=8*1024*1024)
        print("COMM2_HTTP",amc,url,f"bytes={len(body)} type={typ} hash={h}",flush=True)
        soup=BeautifulSoup(body,"html.parser")
        print("COMM2_TITLE",amc,url,repr(soup.title.get_text(" ",strip=True)[:300] if soup.title else ""),flush=True)
        text=" ".join(soup.stripped_strings)
        print("COMM2_TEXT",amc,url,repr(text[:3500]),flush=True)
        links=providers.candidate_links(soup,url)
        print("COMM2_LINK_COUNT",amc,url,len(links),flush=True)
        for target,label in links.items():
            combined=(label+" "+target).lower()
            if any(k in combined for k in ("outlook","market","commentar","review","curve","viewpoint","factor")):
                print("COMM2_LINK",amc,
                      "official="+str(official_publication_url(target,amc)),
                      "kind="+providers.classify(label,target),
                      "label="+repr(label[:300]),
                      "url="+target,flush=True)
        if amc=="Franklin":
            for a in soup.select("a[href]"):
                href=a.get("href","")
                if "widen.net" not in href:continue
                block=a
                for level in range(5):
                    if block is None:break
                    txt=block.get_text(" ",strip=True)
                    print("COMM2_FRANKLIN_CARD",f"level={level}",repr(txt[:1200]),repr(str(block)[:5000]),flush=True)
                    if any(x in txt.lower() for x in ("monthly equity outlook","weekly market review","market outlook")) and len(txt)>25:
                        break
                    block=block.parent
        if amc=="Edelweiss":
            for a in soup.select("a[href]"):
                href=a.get("href","")
                txt=a.get_text(" ",strip=True)
                if "/investor-insights/fund-market/" in href or "outlook" in (txt+" "+href).lower():
                    print("COMM2_EDELWEISS_LINK",repr(txt[:400]),href,flush=True)
    except Exception as exc:
        print("COMM2_ERROR",amc,url,(str(exc) or type(exc).__name__).splitlines()[0][:900],flush=True)

def probe_widen():
    try:
        with httpx.Client(timeout=httpx.Timeout(30,connect=15),follow_redirects=True,
                          headers={"User-Agent":"Mozilla/5.0","Accept":"*/*"}) as client:
            r=client.get(FRANKLIN_WIDEN)
            print("COMM2_WIDEN_HTTP",r.status_code,len(r.content),r.headers.get("content-type",""),str(r.url),flush=True)
            soup=BeautifulSoup(r.content,"html.parser")
            print("COMM2_WIDEN_TITLE",repr(soup.title.get_text(" ",strip=True)[:300] if soup.title else ""),flush=True)
            for a in soup.select("a[href]"):
                if "download" in (a.get_text(" ",strip=True)+" "+a.get("href","")).lower():
                    print("COMM2_WIDEN_LINK",repr(a.get_text(" ",strip=True)[:200]),a.get("href"),flush=True)
    except Exception as exc:
        print("COMM2_WIDEN_ERROR",(str(exc) or type(exc).__name__).splitlines()[0][:900],flush=True)

def main():
    for amc,url in SOURCES:probe_source(amc,url)
    probe_widen()

if __name__=="__main__":
    main()
