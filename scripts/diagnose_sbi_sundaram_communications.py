"""Read-only production probe for SBI and Sundaram AMC communications."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url,explicit_publication_date

SOURCES=(
    ("SBI","https://www.sbimf.com/"),
    ("SBI","https://www.sbimf.com/learn-about-mutual-funds/2026-outlook"),
    ("Sundaram","https://www.sundarammutual.com/"),
    ("Sundaram","https://blog.sundarammutual.com/Documents/outlook-june-2026.pdf"),
)

def main():
    for amc,url in SOURCES:
        print("COMM6_START",amc,url,flush=True)
        try:
            providers.can_crawl(url)
            body,h,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
            print("COMM6_HTTP",amc,url,f"bytes={len(body)} type={typ} hash={h}",flush=True)
            if body.startswith(b"%PDF"):
                print("COMM6_PDF",amc,url,repr(body[:32]),flush=True)
                continue
            soup=BeautifulSoup(body,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            text=" ".join(soup.stripped_strings)
            print("COMM6_TITLE",amc,repr(title[:350]),flush=True)
            print("COMM6_DATE",amc,url,explicit_publication_date(body,typ,url),flush=True)
            print("COMM6_TEXT",amc,url,repr(text[:5000]),flush=True)
            links=providers.candidate_links(soup,url)
            print("COMM6_LINK_COUNT",amc,url,len(links),flush=True)
            for target,label in links.items():
                combined=(label+" "+target).lower()
                if any(k in combined for k in (
                    "outlook","cio","monthly","market","knowledge","insight","blog")):
                    print("COMM6_LINK",amc,
                          "official="+str(official_publication_url(target,amc)),
                          "kind="+providers.classify(label,target),
                          "label="+repr(label[:600]),
                          "url="+target,flush=True)
            for script in soup.find_all("script"):
                raw=(script.string or script.get_text() or "")
                low=raw.lower()
                if any(k in low for k in ("monthly market","2026 outlook","cio", "outlook september 2026","knowledge hub")):
                    print("COMM6_SCRIPT",amc,url,repr(raw[:8000]),flush=True)
        except Exception as exc:
            print("COMM6_ERROR",amc,url,(str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":
    main()
