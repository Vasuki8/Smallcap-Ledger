"""Read-only live preflight for Bank of India Mid Cap portfolio evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.midcap_portfolio_first_party import SOURCES, inspect_family
from tracker import providers


def main():
    family="BANK OF INDIA MID CAP FUND"
    row=inspect_family(family,SOURCES[family],fetch_fn=providers.fetch)
    print(json.dumps({
        "mode":"read_only_boi_midcap_portfolio_preflight",
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
