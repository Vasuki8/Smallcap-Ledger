"""Read-only live probe for Groww and HSBC AMC communication routes."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url,explicit_publication_date

SOURCES=(
    ("Groww","https://www.growwmf.in/distributor"),
    ("Groww","https://www.growwmf.in/distributor/knowledge-hub/publications"),
    ("HSBC","https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights?categories=%5B%27local-market-commentary%27%5D"),
    ("HSBC","https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-august-2026"),
)

def main():
    for amc,url in SOURCES:
        print("COMM3_START",amc,url,flush=True)
        try:
            providers.can_crawl(url)
            body,h,typ=providers.fetch(url,archive=False,max_bytes=10*1024*1024)
            print("COMM3_HTTP",amc,url,f"bytes={len(body)} type={typ} hash={h}",flush=True)
            soup=BeautifulSoup(body,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            text=" ".join(soup.stripped_strings)
            print("COMM3_TITLE",amc,repr(title[:350]),flush=True)
            print("COMM3_DATE",amc,url,explicit_publication_date(body,typ),flush=True)
            print("COMM3_TEXT",amc,url,repr(text[:4000]),flush=True)
            links=providers.candidate_links(soup,url)
            print("COMM3_LINK_COUNT",amc,url,len(links),flush=True)
            for target,label in links.items():
                combined=(label+" "+target).lower()
                if any(k in combined for k in (
                    "newsletter","report","market","outlook","commentar","review",
                    "rbi","insight","cio","publication","economy")):
                    print("COMM3_LINK",amc,
                          "official="+str(official_publication_url(target,amc)),
                          "kind="+providers.classify(label,target),
                          "label="+repr(label[:400]),
                          "url="+target,flush=True)
            for script in soup.find_all("script"):
                raw=(script.string or script.get_text() or "")
                low=raw.lower()
                if any(k in low for k in ("knowledge-hub","publication","newsletter",
                                          "market-commentary","news-and-insights","api/")):
                    print("COMM3_SCRIPT",amc,url,repr(raw[:6000]),flush=True)
        except Exception as exc:
            print("COMM3_ERROR",amc,url,
                  (str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":
    main()
