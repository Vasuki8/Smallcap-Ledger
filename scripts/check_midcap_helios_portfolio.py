"""Read-only live preflight for the exact Helios Mid Cap monthly workbook."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import db, providers
from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_helios_portfolio import inspect


def main():
    with patch.object(db, "connect", side_effect=AssertionError("Read-only preflight cannot write production data")):
        row = inspect(expected_portfolio_as_of(), providers.fetch)
    print(json.dumps({
        "mode": "read_only_helios_midcap_portfolio_preflight",
        **{key: row[key] for key in (
            "family", "as_of", "positions_observed", "complete", "unknown_rows", "sheet",
            "source", "source_sha256", "discovery_source", "discovery_source_sha256",
            "source_locator", "parser_version",
        )},
        "observed_at": db.now(),
        "production_writes": 0, "public_export_enabled": False,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
