"""Read-only pre-merge check of the two registered primary benchmark sources."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker import db
from tracker.midcap_benchmark_labels import SOURCES, inspect_family


def main():
    results, errors = [], []
    with patch.object(db, "connect", side_effect=AssertionError("Database access forbidden in source preflight")):
        for family, url in SOURCES.items():
            try:
                results.append(inspect_family(family, url))
            except Exception as exc:
                errors.append({"family": family, "error": str(exc)[:400]})
    print(json.dumps({"mode": "read_only_source_preflight", "results": results, "errors": errors,
                      "production_writes": 0, "public_export_enabled": False}, indent=2, ensure_ascii=False))
    return 1 if errors or len(results) != len(SOURCES) else 0


if __name__ == "__main__":
    raise SystemExit(main())
