"""Read-only live preflight for Motilal Oswal Midcap current portfolio evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers
from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_batch5 import MOTILAL_PAGE,_motilal_result


def main():
    expected=expected_portfolio_as_of(date.today())
    requests=[]
    def read(url,**kwargs):
        if kwargs.get("archive") is not False:
            raise AssertionError("Motilal portfolio preflight attempted an archival write")
        body,digest,media=providers.fetch(url,**kwargs)
        requests.append({
            "url":url,
            "sha256":hashlib.sha256(body).hexdigest(),
            "bytes":len(body),
            "content_type":media,
        })
        return body,digest,media
    with patch("tracker.db.connect",side_effect=AssertionError("Database access forbidden in Motilal portfolio preflight")), \
         patch("tracker.db.rows",side_effect=AssertionError("Database access forbidden in Motilal portfolio preflight")):
        row=_motilal_result(read,expected)
    if row.get("discovery_source")!=MOTILAL_PAGE:
        raise AssertionError("Motilal preflight used an unexpected discovery source")
    if row["as_of"]!=expected or row["positions_observed"]<5:
        raise AssertionError("Motilal source did not prove current named portfolio evidence")
    if row["scope"]!="structured_monthly_portfolio":
        raise AssertionError("Motilal current portfolio did not use the structured workbook contract")
    print(json.dumps({
        "mode":"read_only_motilal_portfolio_preflight",
        "expected":expected,
        "result":{key:row.get(key) for key in (
            "family","as_of","positions_observed","complete","scope",
            "source","source_sha256","sheet","unknown_rows"
        )},
        "requests":requests,
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
