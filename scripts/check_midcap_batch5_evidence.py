"""Exercise real batch-5 sources without restoring or accessing any database."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import providers
from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_batch5 import _kotak_result, _mahindra_result, _sundaram_result


def main():
    expected = expected_portfolio_as_of(date.today())
    report = {"expected": expected, "database_access_forbidden": True,
              "production_writes": 0, "public_export_enabled": False, "results": [], "errors": []}
    requests = []
    def read(url, **kwargs):
        if kwargs.get("archive") is not False:
            raise AssertionError("Evidence preflight attempted an archival write")
        body, digest, media = providers.fetch(url, **kwargs)
        requests.append({"url": url, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        return body, digest, media
    with patch("tracker.db.connect", side_effect=AssertionError("Database access is forbidden in source preflight")):
        for label, collector in (("Mahindra", _mahindra_result), ("Sundaram", _sundaram_result), ("Kotak", _kotak_result)):
            try:
                row = collector(read, expected)
                if row["as_of"] != expected or row["positions_observed"] < 5:
                    raise AssertionError("Source did not prove current named portfolio evidence")
                if label in ("Mahindra", "Kotak"):
                    names = {x["name"] for x in row["positions"]}
                    if names & {"Healthcare", "Information Technology", "Power", "Realty", "Financial Services"}:
                        raise AssertionError("Sector subtotal leaked into holdings")
                    if row["complete"] is not False:
                        raise AssertionError("Equity-only evidence was marked complete")
                report["results"].append({key: row.get(key) for key in (
                    "family", "as_of", "positions_observed", "complete", "scope", "equity_weight_sum",
                    "sectors_checked", "source", "source_sha256", "card_aum_as_of_raw", "unknown_rows")})
            except Exception as exc:
                report["errors"].append({"source": label, "error": str(exc)[:500]})
    report["requests"] = requests
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
