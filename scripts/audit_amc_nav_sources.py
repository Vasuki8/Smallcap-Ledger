"""Read-only diagnostic for ABSL and DSP first-party historical NAV transports."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

PAGES=(
    ("ABSL","https://mutualfund.adityabirlacapital.com/historical_nav_and_dividend"),
    ("DSP","https://www.dspim.com/investor-centre/nav"),
)
TERMS=re.compile(r"historical.?nav|nav.?histor|navhistory|history.?nav|download.?nav|nav.?download|from.?date|to.?date|api/|ajax|graphql",re.I)

def snippets(text,limit=18,width=900):
    out=[]
    for m in TERMS.finditer(text):
        s=max(0,m.start()-350);e=min(len(text),m.end()+width)
        hit=re.sub(r"\s+"," ",text[s:e]).strip()
        if hit not in out:out.append(hit)
        if len(out)>=limit:break
    return out

def main():
    for label,page in PAGES:
        body,_,mime=providers.fetch(page,archive=False,max_bytes=12*1024*1024)
        html=body.decode("utf-8","ignore")
        soup=BeautifulSoup(body,"html.parser")
        print(f"NAV_SOURCE_PAGE {label} {page} bytes={len(body)} mime={mime}",flush=True)
        for form in soup.find_all("form")[:12]:
            print("NAV_SOURCE_FORM",label,
                  "action="+str(form.get("action")),
                  "method="+str(form.get("method")),
                  "id="+str(form.get("id")),
                  "class="+str(form.get("class")),flush=True)
        for hit in snippets(html,limit=20):
            print("NAV_SOURCE_HTML",label,hit[:1800],flush=True)
        scripts=[]
        for tag in soup.find_all("script"):
            src=tag.get("src")
            if src:
                u=urljoin(page,src)
                if (urlparse(u).hostname or "").lower().endswith((urlparse(page).hostname or "").lower()):
                    scripts.append(u)
            else:
                inline=tag.string or tag.get_text(" ",strip=True)
                for hit in snippets(inline,limit=8):
                    print("NAV_SOURCE_INLINE",label,hit[:1800],flush=True)
        print("NAV_SOURCE_SCRIPTS",label,len(scripts),flush=True)
        ranked=sorted(dict.fromkeys(scripts),
                      key=lambda u:(0 if re.search(r"nav|histor|main|app|bundle|common",u,re.I) else 1,len(u)))
        checked=0
        for u in ranked:
            if checked>=28:break
            try:
                js,_,_=providers.fetch(u,archive=False,max_bytes=8*1024*1024)
            except Exception as exc:
                print(f"NAV_SOURCE_SCRIPT_ERR {label} {u} :: {(str(exc) or type(exc).__name__)[:220]}",flush=True)
                continue
            checked+=1
            text=js.decode("utf-8","ignore")
            hits=snippets(text,limit=12)
            if hits:
                print("NAV_SOURCE_SCRIPT",label,u,"bytes="+str(len(js)),flush=True)
                for hit in hits:print("NAV_SOURCE_HIT",label,hit[:2200],flush=True)

if __name__=="__main__":
    main()
