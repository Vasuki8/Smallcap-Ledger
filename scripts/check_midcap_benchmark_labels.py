"""Read-only pre-merge check of the registered primary benchmark sources."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker import db
from tracker import midcap_benchmark_documents as documents
from tracker import midcap_benchmark_labels as labeled
from tracker import midcap_benchmark_invesco as invesco
from tracker import midcap_benchmark_first_party as first_party
from tracker import midcap_benchmark_explicit as explicit
from tracker import midcap_benchmark_explicit2 as explicit2
from tracker import midcap_benchmark_iti_jm as iti_jm
from tracker import midcap_benchmark_gate3 as gate3
from tracker import midcap_benchmark_bandhan as bandhan


def main():
    results, errors = [], []
    source_groups = (
        (labeled.SOURCES, labeled.inspect_family),
        (documents.SOURCES, documents.inspect_family),
        (invesco.sources(), invesco.inspect_family),
        (first_party.PREFLIGHT_SOURCES, first_party.inspect_family),
        (explicit.PREFLIGHT_SOURCES, explicit.inspect_family),
        (explicit2.SOURCES, explicit2.inspect_family),
        (iti_jm.SOURCES, iti_jm.inspect_family),
        (gate3.SOURCES, gate3.inspect_family),
        ({bandhan.FAMILY: bandhan.SOURCE}, bandhan.inspect_family),
    )
    expected = sum(len(sources) for sources, _ in source_groups)
    with patch.object(db, "connect", side_effect=AssertionError("Database access forbidden in source preflight")):
        for sources, inspect_family in source_groups:
            for family, url in sources.items():
                try:
                    results.append(inspect_family(family, url))
                except Exception as exc:
                    errors.append({"family": family, "error": str(exc)[:400]})
    print(json.dumps({"mode": "read_only_source_preflight", "results": results, "errors": errors,
                      "production_writes": 0, "public_export_enabled": False}, indent=2, ensure_ascii=False))
    return 1 if errors or len(results) != expected else 0


if __name__ == "__main__":
    raise SystemExit(main())
