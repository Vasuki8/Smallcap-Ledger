"""Read-only live preflight for Kotak Mid Cap current portfolio evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_batch5 import _kotak_result
from tracker import providers


def main():
    expected=expected_portfolio_as_of()
    row=_kotak_result(providers.fetch,expected)
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
