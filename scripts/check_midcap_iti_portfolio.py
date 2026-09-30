"""Read-only live preflight for ITI Mid Cap current portfolio evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from bs4 import BeautifulSoup

from tracker.midcap_portfolio_first_party import SOURCES, inspect_family
from tracker import providers


def main():
    family="ITI Mid Cap Fund"
    try:
        row=inspect_family(family,SOURCES[family],fetch_fn=providers.fetch)
    except ValueError as exc:
        body,_,typ=providers.fetch(SOURCES[family]["url"],archive=False,max_bytes=12*1024*1024)
        soup=BeautifulSoup(body,"html.parser")
        probes=[]
        for needle in ("Name of the Instrument","Bharat Heavy Electricals Limited","Equity & Equity Related Total"):
            node=soup.find(string=lambda value: value is not None and needle.casefold() in str(value).casefold())
            if node is not None:
                parent=node.parent
                probes.append({
                    "needle":needle,
                    "tag":getattr(parent,"name",None),
                    "parent":str(parent)[:1200],
                    "grandparent":str(getattr(parent,"parent",None))[:1800],
                })
        print(json.dumps({
            "mode":"read_only_iti_midcap_portfolio_dom_diagnostic",
            "error":str(exc),
            "content_type":typ,
            "table_count":len(soup.find_all("table")),
            "probes":probes,
            "production_writes":0,
            "public_export_enabled":False,
        },indent=2,ensure_ascii=False))
        raise
    print(json.dumps({
        "mode":"read_only_iti_midcap_portfolio_preflight",
        "family":family,
        "as_of":row["as_of"],
        "positions_observed":row["positions_observed"],
        "complete":row["complete"],
        "scope":row["scope"],
        "source":row["source"],
        "source_sha256":row["source_sha256"],
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
