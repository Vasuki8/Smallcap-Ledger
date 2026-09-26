"""Read-only production probe for Kotak and Mirae AMC communication sources."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url, explicit_publication_date

SOURCES=(
    ("Kotak","https://www.kotakmf.com/monthly-market-update"),
    ("Mirae","https://www.miraeassetmf.co.in/docs/default-source/marketing-insights/annual-outlook-2025.pdf"),
)

def main():
    for amc,url in SOURCES:
        print("COMM4_START",amc,url,flush=True)
        try:
            providers.can_crawl(url)
            body,h,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            print("COMM4_HTTP",amc,url,f"bytes={len(body)} type={typ} hash={h}",flush=True)
            if body.startswith(b"%PDF"):
                print("COMM4_PDF",amc,url,repr(body[:32]),flush=True)
                continue
            soup=BeautifulSoup(body,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            text=" ".join(soup.stripped_strings)
            print("COMM4_TITLE",amc,repr(title[:350]),flush=True)
            print("COMM4_DATE",amc,url,explicit_publication_date(body,typ,url),flush=True)
            print("COMM4_TEXT",amc,url,repr(text[:4500]),flush=True)
            links=providers.candidate_links(soup,url)
            print("COMM4_LINK_COUNT",amc,url,len(links),flush=True)
            for target,label in links.items():
                combined=(label+" "+target).lower()
                if any(k in combined for k in ("outlook","market","monthly","ppt","presentation","download")):
                    print("COMM4_LINK",amc,
                          "official="+str(official_publication_url(target,amc)),
                          "kind="+providers.classify(label,target),
                          "label="+repr(label[:500]),
                          "url="+target,flush=True)
            for script in soup.find_all("script"):
                raw=(script.string or script.get_text() or "")
                if any(k in raw.lower() for k in ("monthly outlook","market update","august 2026","july 2026")):
                    print("COMM4_SCRIPT",amc,url,repr(raw[:7000]),flush=True)
        except Exception as exc:
            print("COMM4_ERROR",amc,url,(str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":
    main()
