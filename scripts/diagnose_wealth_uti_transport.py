"""Read-only transport diagnostic for Wealth Company and UTI communication shells."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers

OUT=ROOT/"deployment"/"communication-transport-wealth-uti.json"

TARGETS=(
    ("Wealth","https://www.wealthcompanyamc.in/knowledge-center/current-insights/"),
    ("UTI","https://www.utimf.com/learn"),
    ("UTI","https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments"),
    ("UTI","https://www.utimf.com/leadership-desk/dont-get-swayed-distractions-markets"),
)

TOKENS=(
    "Daily Wealth Recap",
    "The NewsMaker",
    "uploadDate",
    ".pdf",
    "leadership-desk",
    "market-insight",
    "investment-insight",
    "/api/",
    "__NEXT_DATA__",
    "self.__next_f.push",
)


def same_owner(label,url):
    host=(urlparse(url).hostname or "").lower().removeprefix("www.")
    if label=="Wealth":
        return host=="wealthcompanyamc.in" or host.endswith(".wealthcompanyamc.in")
    if label=="UTI":
        return host=="utimf.com" or host.endswith(".utimf.com")
    return False


def contexts(raw):
    low=raw.lower()
    out=[];seen=set()
    for token in TOKENS:
        start=0
        for _ in range(8):
            i=low.find(token.lower(),start)
            if i<0:break
            key=(token,i)
            if key not in seen:
                seen.add(key)
                out.append({
                    "token":token,
                    "index":i,
                    "context":raw[max(0,i-900):i+2200],
                })
            start=i+len(token)
            if len(out)>=40:return out
    return out


def inspect(label,url):
    item={"label":label,"url":url}
    try:
        providers.can_crawl(url)
        body,_,typ=providers.fetch(url,archive=False,max_bytes=15*1024*1024)
        item.update({"ok":True,"bytes":len(body),"media_type":typ})
        raw=body.decode("utf-8","replace")
        soup=BeautifulSoup(body,"html.parser")
        item["title"]=soup.title.get_text(" ",strip=True)[:500] if soup.title else ""
        item["text_prefix"]=" ".join(soup.stripped_strings)[:2500]
        item["scripts"]=[
            urljoin(url,s.get("src",""))
            for s in soup.select("script[src]")
            if s.get("src")
        ][:80]
        links=[]
        for target,name in providers.candidate_links(soup,url).items():
            combined=f"{name} {target}"
            if not re.search(
                r"daily wealth recap|newsmaker|leadership|market.?insight|investment.?insight|\.pdf",
                combined,re.I,
            ):
                continue
            links.append({
                "label":str(name or "")[:500],
                "url":target,
                "same_owner":same_owner(label,target),
            })
        item["candidate_links"]=links[:120]
        item["contexts"]=contexts(raw)
    except Exception as exc:
        item.update({
            "ok":False,
            "error":(str(exc) or type(exc).__name__).splitlines()[0][:1000],
        })
    return item


def main():
    report={
        "prepared_at":db.now(),
        "mode":"read_only_non_fatal",
        "targets":[inspect(label,url) for label,url in TARGETS],
        "notes":[
            "No response bytes are archived by this diagnostic.",
            "Raw contexts are bounded around known communication/API markers only.",
            "Candidate links still require source-specific validation before collection.",
        ],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Wrote",OUT,flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
