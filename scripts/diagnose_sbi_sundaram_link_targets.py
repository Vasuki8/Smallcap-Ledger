"""Focused read-only probe for SBI/Sundaram current communication link targets."""
from pathlib import Path
import re,sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

TARGETS=(
    ("SBI","https://www.sbimf.com/","Monthly Presentation on Economy & Markets - July 2026"),
    ("SBI","https://www.sbimf.com/cio-desk","Monthly Presentation on Economy & Markets"),
    ("Sundaram","https://www.sundarammutual.com/","Outlook September 2026"),
    ("Sundaram","https://www.sundarammutual.com/knowledge-hub","Outlook September 2026"),
    ("Sundaram","https://blog.sundarammutual.com/","Outlook September 2026"),
)

def attrs(node):
    out={}
    for k,v in getattr(node,"attrs",{}).items():
        if k in ("href","src","onclick","data-href","data-url","data-link","data-file","data-pdf","target","class","id"):
            out[k]=v
    return out

def main():
    for amc,url,needle in TARGETS:
        print("COMM8_START",amc,url,"needle="+needle,flush=True)
        try:
            providers.can_crawl(url)
            body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            soup=BeautifulSoup(body,"html.parser")
            print("COMM8_HTTP",amc,url,len(body),typ,flush=True)
            matches=[]
            for node in soup.find_all(string=lambda x: x and needle.lower() in str(x).lower()):
                matches.append(node)
            print("COMM8_MATCHES",amc,url,len(matches),flush=True)
            for mi,node in enumerate(matches[:8]):
                parent=node.parent
                for level in range(7):
                    if parent is None:break
                    links=[]
                    for a in parent.find_all("a",href=True):
                        links.append({
                            "text":a.get_text(" ",strip=True)[:300],
                            "href":urljoin(url,a.get("href","")),
                            "attrs":attrs(a),
                        })
                    buttons=[]
                    for b in parent.find_all(["button","div"],limit=80):
                        at=attrs(b)
                        if any(k.startswith("data-") for k in at) or "onclick" in at:
                            buttons.append({"text":b.get_text(" ",strip=True)[:300],"attrs":at})
                    print("COMM8_NODE",amc,url,f"match={mi}",f"level={level}",
                          "tag="+str(parent.name),
                          "attrs="+repr(attrs(parent)),
                          "text="+repr(parent.get_text(" ",strip=True)[:1600]),
                          "links="+repr(links[:20]),
                          "buttons="+repr(buttons[:20]),
                          "html="+repr(str(parent)[:14000]),flush=True)
                    parent=parent.parent

            # Global relevant hrefs/data attributes even if the visible label is elsewhere.
            for a in soup.find_all("a",href=True):
                text=a.get_text(" ",strip=True)
                href=urljoin(url,a.get("href",""))
                combined=(text+" "+href).lower()
                if any(k in combined for k in ("outlook","economy","markets","cio","presentation")):
                    print("COMM8_LINK",amc,url,repr(text[:500]),href,repr(attrs(a)),flush=True)
            decoded=body.decode("utf-8","ignore")
            low=decoded.lower()
            for token in ("outlook september 2026","monthly presentation on economy","outlook-june-2026","outlook-september"):
                start=0
                for _ in range(8):
                    i=low.find(token,start)
                    if i<0:break
                    print("COMM8_RAW",amc,url,"token="+token,"index="+str(i),
                          repr(decoded[max(0,i-5000):i+10000]),flush=True)
                    start=i+len(token)
        except Exception as exc:
            print("COMM8_ERROR",amc,url,(str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":
    main()
