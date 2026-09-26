"""Read-only production diagnostic for remaining AMC communication gaps.

Writes a compact, non-fatal report under deployment/ so the normal build can
preserve the exact first-party link structures seen by the GitHub runner.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers

OUT=ROOT/"deployment"/"communication-diagnostic-trust-uti-union.json"

PAGES=(
    ("Trust","https://www.trustmf.com/"),
    ("Trust","https://www.trustmf.com/get-curious"),
    ("UTI","https://www.utimf.com/learn"),
    ("UTI","https://www.utimf.com/"),
    ("Union","https://www.unionmf.com/knowledge-hub/fund-managers-desk/market-outlook"),
    ("Union","https://www.unionmf.com/knowledge-hub/fund-managers-desk/research-notes"),
)

KEYWORDS=re.compile(
    r"market|outlook|insight|leadership|investment|cio|fund manager|"
    r"newsletter|weekly|research|economy|equity|debt",
    re.I,
)


def same_owner(amc,url):
    host=(urlparse(url).hostname or "").lower().removeprefix("www.")
    roots={
        "Trust":("trustmf.com",),
        "UTI":("utimf.com","doc.utimf.com"),
        "Union":("unionmf.com",),
    }[amc]
    return any(host==root or host.endswith("."+root) for root in roots)


def summarize(amc,url):
    item={"amc":amc,"url":url}
    try:
        providers.can_crawl(url)
        body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
        item.update({"ok":True,"bytes":len(body),"media_type":typ})
        if body.startswith(b"%PDF"):
            item["pdf"]=True
            item["prefix"]=body[:16].decode("latin1","replace")
            return item
        soup=BeautifulSoup(body,"html.parser")
        item["title"]=soup.title.get_text(" ",strip=True)[:500] if soup.title else ""
        text=" ".join(soup.stripped_strings)
        item["text_prefix"]=text[:3500]
        links=providers.candidate_links(soup,url)
        relevant=[]
        for target,label in links.items():
            combined=f"{label} {target}"
            if not KEYWORDS.search(combined):
                continue
            relevant.append({
                "label":str(label or "")[:500],
                "url":target,
                "same_owner":same_owner(amc,target),
            })
        item["relevant_links"]=relevant[:80]
    except Exception as exc:
        item.update({
            "ok":False,
            "error":(str(exc) or type(exc).__name__).splitlines()[0][:1000],
        })
    return item


def secondary_uti(primary):
    rows=[]
    seen=set()
    for item in primary:
        if item.get("amc")!="UTI" or not item.get("ok"):
            continue
        for link in item.get("relevant_links",[]):
            label=(link.get("label") or "").strip().lower()
            target=link.get("url") or ""
            if not link.get("same_owner"):
                continue
            if not re.search(r"market\s*insight|leadership\s*desk|investment\s*insight",label,re.I):
                continue
            if target in seen:
                continue
            seen.add(target)
            rows.append(summarize("UTI",target))
            if len(rows)>=8:
                return rows
    return rows


def main():
    primary=[summarize(amc,url) for amc,url in PAGES]
    report={
        "prepared_at":db.now(),
        "mode":"read_only_non_fatal",
        "primary":primary,
        "uti_secondary":secondary_uti(primary),
        "notes":[
            "No source binary is archived by this diagnostic.",
            "Factsheets are not treated as communication sources.",
            "Only first-party ownership/link structure is inspected.",
        ],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Wrote",OUT,flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
