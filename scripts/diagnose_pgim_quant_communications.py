"""Read-only live probe for PGIM India and quant Mutual communication routes."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url,explicit_publication_date

SOURCES=(
    ("PGIM","https://www.pgimindia.com/mutual-funds/domestic-insights"),
    ("quant Mutual","https://www.quantmutual.com/downloads/investment_outlook"),
)

def main():
    for amc,url in SOURCES:
        print("COMM5_START",amc,url,flush=True)
        try:
            providers.can_crawl(url)
            body,h,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            print("COMM5_HTTP",amc,url,f"bytes={len(body)} type={typ} hash={h}",flush=True)
            soup=BeautifulSoup(body,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            text=" ".join(soup.stripped_strings)
            print("COMM5_TITLE",amc,repr(title[:400]),flush=True)
            print("COMM5_DATE",amc,url,explicit_publication_date(body,typ,url),flush=True)
            print("COMM5_TEXT",amc,url,repr(text[:6500]),flush=True)
            links=providers.candidate_links(soup,url)
            print("COMM5_LINK_COUNT",amc,url,len(links),flush=True)
            for target,label in links.items():
                combined=(label+" "+target).lower()
                if any(k in combined for k in (
                    "ceo","outlook","econom","predictive","vlrt","investment",
                    "analytics","letter","insight","pdf")):
                    print("COMM5_LINK",amc,
                          "official="+str(official_publication_url(target,amc)),
                          "kind="+providers.classify(label,target),
                          "label="+repr(label[:500]),
                          "url="+target,flush=True)
            for script in soup.find_all("script"):
                raw=(script.string or script.get_text() or "")
                low=raw.lower()
                if any(k in low for k in (
                    "ceo letters","outlooks & economy","uncertainty does not equal risk",
                    "predictive analytics","vlrt outlook","investment outlook")):
                    print("COMM5_SCRIPT",amc,url,repr(raw[:12000]),flush=True)
        except Exception as exc:
            print("COMM5_ERROR",amc,url,
                  (str(exc) or type(exc).__name__).splitlines()[0][:1500],flush=True)

if __name__=="__main__":
    main()
