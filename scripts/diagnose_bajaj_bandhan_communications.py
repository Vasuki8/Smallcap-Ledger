"""Read-only live probe for Bajaj/Bandhan communication sources."""
from pathlib import Path
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url

SOURCES=(
    ("Bajaj","https://cobranding.bajajamc.com/marketing/Cobrandingmarketingmaterial?LId=23"),
    ("Bajaj","https://cobranding.bajajamc.com/marketing/Cobrandingmarketingmaterial?LId=51"),
    ("Bajaj","https://cobranding.bajajamc.com/marketing/Cobrandingmarketingmaterial?LId=58"),
    ("Bandhan","https://bandhanmutual.com/downloads/market-outlook"),
    ("Bandhan","https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-equity-september-2026/"),
    ("Bandhan","https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-debt-september-2026/"),
)

def main():
    for amc,url in SOURCES:
        print("COMM_PROBE_START",amc,url,flush=True)
        try:
            body,h,typ=providers.fetch(url,archive=False,max_bytes=8*1024*1024)
            print("COMM_PROBE_HTTP",amc,url,
                  f"bytes={len(body)} type={typ} hash={h}",flush=True)
            if body.startswith(b'%PDF'):
                print("COMM_PROBE_PDF",amc,url,flush=True);continue
            soup=BeautifulSoup(body,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            text=" ".join(soup.stripped_strings)
            print("COMM_PROBE_PAGE",amc,url,"title="+repr(title[:250]),
                  "text="+repr(text[:2500]),flush=True)
            links=providers.candidate_links(soup,url)
            print("COMM_PROBE_LINK_COUNT",amc,url,len(links),flush=True)
            for target,label in links.items():
                combined=(label+" "+target).lower()
                if any(k in combined for k in (
                    "outlook","market update","market-outlook","equity","debt",
                    "newsletter","presentation","fund insight")):
                    print("COMM_PROBE_LINK",amc,
                          "official="+str(official_publication_url(target,amc)),
                          "kind="+providers.classify(label,target),
                          "label="+repr(label[:300]),
                          "url="+target,flush=True)
            if amc=="Bajaj" and "LId=5" in url:
                for node in soup.find_all(string=lambda x:isinstance(x,str) and "equity outlook" in x.lower()):
                    block=node.parent
                    for level in range(7):
                        if block is None:break
                        print("COMM_PROBE_BAJAJ_CARD_LEVEL",url,"level="+str(level),
                              "tag="+block.name,
                              "attrs="+repr(dict(block.attrs)),
                              "text="+repr(block.get_text(" ",strip=True)[:1400]),
                              "html="+repr(str(block)[:6000]),flush=True)
                        block=block.parent
                for tag in soup.find_all(["button","a","input"]):
                    attrs=dict(tag.attrs);txt=tag.get_text(" ",strip=True)
                    raw=(txt+" "+repr(attrs)).lower()
                    if "download" in raw or "outlook" in raw:
                        print("COMM_PROBE_BAJAJ_CONTROL",url,
                              "tag="+tag.name,"text="+repr(txt[:500]),
                              "attrs="+repr(attrs),flush=True)
            for script in soup.find_all("script"):
                raw=(script.string or script.get_text() or "")
                if any(k in raw.lower() for k in ("outlook","marketingmaterial","api/","ajax","download")):
                    print("COMM_PROBE_SCRIPT",amc,url,repr(raw[:3500]),flush=True)
        except Exception as exc:
            print("COMM_PROBE_ERROR",amc,url,
                  (str(exc) or type(exc).__name__).splitlines()[0][:800],flush=True)

if __name__=="__main__":
    main()
