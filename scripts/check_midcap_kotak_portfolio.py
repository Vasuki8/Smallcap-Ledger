"""Read-only live preflight for Kotak Mid Cap current portfolio evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_factsheet_equities import clean
from tracker.midcap_portfolio_batch5 import KOTAK_URL, _kotak_result
from tracker import providers


def _diagnose_identity_failure(exc):
    """Print bounded first-party heading evidence only when the live parser fails."""
    body,_,typ=providers.fetch(KOTAK_URL,archive=False,max_bytes=12*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    candidates=[]
    for tag in soup.find_all(["h1","h2","h3","h4","h5","h6","p","span","div"]):
        value=clean(tag.get_text(" ",strip=True))
        folded=value.casefold()
        if value and ("mid cap" in folded or "midcap" in folded):
            candidates.append(value[:300])
    unique=list(dict.fromkeys(candidates))[:20]
    print(json.dumps({
        "mode":"read_only_kotak_portfolio_identity_diagnostic",
        "error":str(exc) or type(exc).__name__,
        "source":KOTAK_URL,
        "source_content_type":typ,
        "heading_candidates":unique,
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))


def main():
    expected=expected_portfolio_as_of()
    try:
        row=_kotak_result(providers.fetch,expected)
    except Exception as exc:
        _diagnose_identity_failure(exc)
        raise
    print(json.dumps({
        "mode":"read_only_kotak_portfolio_preflight",
        "family":row["family"],
        "as_of":row["as_of"],
        "positions_observed":row["positions_observed"],
        "complete":row["complete"],
        "source":row["source"],
        "source_sha256":row["source_sha256"],
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
