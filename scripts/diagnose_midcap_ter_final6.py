"""Probe official TER/disclosure pages for the final six staged Mid Cap gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers


TARGETS={
    "Bandhan Mid Cap Fund":[
        "https://bandhanmutual.com/downloads/disclosures",
        "https://bandhanmutual.com/downloads/factsheet/all-schemes",
    ],
    "Bank of India Mid Cap Fund":[
        "https://www.boimf.in/siddisclosures/scheme-expense-ratio",
        "https://www.boimf.in/investor-corner",
        "https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund",
    ],
    "Helios Mid Cap Fund":[
        "https://www.heliosmf.in/daily-ter/",
        "https://www.heliosmf.in/helios-mid-cap-fund/",
    ],
    "Kotak Mid Cap Fund":[
        "https://www.kotakmf.com/Information/TER",
        "https://www.kotakmf.com/mutual-funds/equity-funds/kotak-mid-cap-fund/dir-g",
        "https://www.kotakmf.com/mutual-funds/equity-funds/kotak-mid-cap-fund/reg-g",
    ],
    "The Wealth Company Mid Cap Fund":[
        "https://www.wealthcompanyamc.in/total-expense-ratio/",
        "https://www.wealthcompanyamc.in/our-funds/fund/the-wealth-company-mid-cap-fund/154479/",
    ],
    "WhiteOak Capital Mid Cap Fund":[
        "https://mf.whiteoakamc.com/regulatory-disclosures",
        "https://mf.whiteoakamc.com/",
    ],
}

URL_RE=re.compile(
    r"""(?P<url>https?://[^"'<>\s\\]+|/[^"'<>\s\\]+\.(?:xlsx?|xls|csv|json|pdf)(?:\?[^"'<>\s\\]*)?)""",
    re.I,
)


def _snippets(text,terms=("mid cap","midcap","ter","expense ratio"),radius=220):
    flat=re.sub(r"\s+"," ",text)
    found=[]
    lower=flat.casefold()
    for term in terms:
        start=0
        needle=term.casefold()
        while True:
            i=lower.find(needle,start)
            if i<0:break
            found.append(flat[max(0,i-radius):min(len(flat),i+len(term)+radius)])
            start=i+len(term)
            if len(found)>=16:return found
    return found


def inspect_page(url,fetch_fn=providers.fetch):
    body,_,typ=fetch_fn(url,archive=False,max_bytes=8*1024*1024)
    digest=hashlib.sha256(body).hexdigest()
    text=body.decode("utf-8","replace")
    soup=BeautifulSoup(text,"html.parser")
    links=providers.candidate_links(soup,url)
    candidates={}
    for href,title in links.items():
        low=(title+" "+href).casefold()
        if any(x in low for x in ("ter","expense","ratio","mid cap","midcap")):
            candidates[href]=title
    for match in URL_RE.finditer(text):
        raw=match.group("url").replace("\\/","/")
        absolute=urljoin(url,raw)
        low=absolute.casefold()
        if any(x in low for x in ("ter","expense","ratio","midcap","mid-cap","mid_cap")):
            candidates.setdefault(absolute,"embedded_url")
    api_hints=sorted(set(
        m.group(0)[:500]
        for m in re.finditer(
            r"""[^"'<>\s]{0,100}(?:api|ajax|download|expense|ter)[^"'<>\s]{0,240}""",
            text,re.I,
        )
        if "/" in m.group(0)
    ))[:30]
    return {
        "url":url,
        "status":"ok",
        "bytes":len(body),
        "content_type":typ,
        "sha256":digest,
        "candidate_links":[{"url":u,"label":t} for u,t in sorted(candidates.items())[:80]],
        "snippets":_snippets(soup.get_text(" ",strip=True)),
        "api_hints":api_hints,
    }


def run(fetch_fn=providers.fetch):
    out={"mode":"read_only_source_discovery","production_writes":0,"targets":[]}
    for family,urls in TARGETS.items():
        item={"family":family,"pages":[]}
        for url in urls:
            try:
                item["pages"].append(inspect_page(url,fetch_fn=fetch_fn))
            except Exception as exc:
                item["pages"].append({
                    "url":url,"status":"error",
                    "error":(str(exc) or type(exc).__name__)[:500],
                })
        out["targets"].append(item)
    out["summary"]={
        "families":len(out["targets"]),
        "pages_ok":sum(p["status"]=="ok" for t in out["targets"] for p in t["pages"]),
        "pages_error":sum(p["status"]=="error" for t in out["targets"] for p in t["pages"]),
        "candidate_links":sum(len(p.get("candidate_links",[])) for t in out["targets"] for p in t["pages"]),
    }
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    result=run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result["summary"],indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
