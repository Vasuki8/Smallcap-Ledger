"""Read-only live preflight for Bandhan Mid Cap current portfolio evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db, providers
from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_batch5 import _bandhan_result


def main():
    expected=expected_portfolio_as_of()
    try:
        with patch.object(
            db,"connect",
            side_effect=AssertionError("Database access forbidden in Bandhan portfolio preflight"),
        ):
            row=_bandhan_result(providers.fetch,expected)
        if row.get("as_of")!=expected:
            raise ValueError("Bandhan preflight did not return the required month-end")
        if int(row.get("positions_observed") or 0)<5:
            raise ValueError("Bandhan preflight returned too few positions")
        result={
            "mode":"read_only_bandhan_portfolio_preflight",
            "expected_as_of":expected,
            "result":row,
            "errors":[],
            "production_writes":0,
            "public_export_enabled":False,
        }
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "mode":"read_only_bandhan_portfolio_preflight",
            "expected_as_of":expected,
            "result":None,
            "errors":[{"family":"BANDHAN MID CAP FUND","error":(str(exc) or type(exc).__name__)[:500]}],
            "production_writes":0,
            "public_export_enabled":False,
        },indent=2,ensure_ascii=False))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
