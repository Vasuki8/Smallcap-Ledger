"""Read-only probe for Franklin's official-domain communication index."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.disclosures import official_publication_url

URL="https://www.franklintempletonindia.com/sebi-circular/current"

def main():
    try:
        body,h,typ=providers.fetch(URL,archive=False,max_bytes=12*1024*1024)
        print("FRANKLIN_INDEX_HTTP",f"bytes={len(body)} type={typ} hash={h}",flush=True)
        soup=BeautifulSoup(body,"html.parser")
        print("FRANKLIN_INDEX_TITLE",repr(soup.title.get_text(" ",strip=True)[:300] if soup.title else ""),flush=True)
        text=" ".join(soup.stripped_strings)
        print("FRANKLIN_INDEX_TEXT",repr(text[:5000]),flush=True)
        links=providers.candidate_links(soup,URL)
        print("FRANKLIN_INDEX_LINK_COUNT",len(links),flush=True)
        for target,label in links.items():
            combined=(label+" "+target).lower()
            if any(k in combined for k in (
                "market outlook","outlook highlights","monthly debt outlook",
                "letter from president","president to investors","fact sheet & market outlook",
                "equity market outlook","debt market outlook")):
                print("FRANKLIN_INDEX_LINK",
                      "official="+str(official_publication_url(target,"Franklin")),
                      "kind="+providers.classify(label,target),
                      "label="+repr(label[:500]),
                      "url="+target,flush=True)
        for a in soup.select("a[href]"):
            label=a.get_text(" ",strip=True)
            combined=(label+" "+a.get("href","")).lower()
            if "market outlook" in combined or "president" in combined:
                block=a
                for level in range(4):
                    if block is None:break
                    print("FRANKLIN_INDEX_CARD",f"level={level}",
                          repr(block.get_text(" ",strip=True)[:1000]),
                          repr(str(block)[:4500]),flush=True)
                    block=block.parent
    except Exception as exc:
        print("FRANKLIN_INDEX_ERROR",(str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":main()
