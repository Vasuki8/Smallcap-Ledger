"""Read-only parser preflight for Taurus Mid Cap August portfolio workbook."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_structured import _parse_workbook
from tracker import providers

FAMILY="Taurus Mid Cap Fund"
SOURCE="https://taurusmutualfund.com/sites/default/files/scheme-summary/2026_08/excel/taurus_mid_cap_fund.xls"


def main():
    expected=expected_portfolio_as_of()
    body,_,typ=providers.fetch(SOURCE,archive=False,max_bytes=30*1024*1024)
    parsed=_parse_workbook(body,FAMILY,expected)
    print(json.dumps({
        "mode":"read_only_taurus_midcap_workbook_preflight",
        "family":FAMILY,
        "as_of":parsed.get("as_of"),
        "positions_observed":parsed.get("positions_observed"),
        "complete":parsed.get("complete"),
        "unknown_rows":parsed.get("unknown_rows"),
        "source":SOURCE,
        "source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
