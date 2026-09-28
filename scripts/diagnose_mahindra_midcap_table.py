"""Explicit, read-only Mahindra Mid Cap HTML contract probe.

Fetch one approved official factsheet and report only table-shape diagnostics.
This command does not modify the database, publish a site, or count coverage.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup
from tracker import providers
from tracker.midcap_factsheet_validation import _HEADER, _norm, _rows, mahindra_positions
from tracker.midcap_portfolio_batch5 import MAHINDRA_URL


def main():
    body, _, media_type = providers.fetch(
        MAHINDRA_URL, archive=False, max_bytes=12 * 1024 * 1024)
    soup = BeautifulSoup(body, "html.parser")
    diagnostics = []
    for index, table in enumerate(soup.find_all("table")):
        if table.find("table") is not None:
            continue
        rows = _rows(table)
        starts = [i for i, cells in enumerate(rows)
                  if tuple(_norm(cell) for cell in cells) == _HEADER]
        if not starts:
            continue
        invalid_shapes = [{"row_index": i, "cells": cells,
                           "raw_html": str(tr)[:1500]}
                          for i, tr in enumerate(table.find_all("tr"))
                          for cells in [[" ".join(cell.get_text(" ", strip=True).split())
                                         for cell in tr.find_all(("td", "th"), recursive=False)]]
                          if any(cells) and len([cell for cell in cells if cell]) != 2]
        diagnostics.append({"table_index": index, "header_row_index": starts[0],
                            "rows": len(rows), "first_rows": rows[:8],
                            "last_rows": rows[-8:],
                            "non_two_column_rows": invalid_shapes[:20]})
    result = {"source": MAHINDRA_URL, "source_sha256": hashlib.sha256(body).hexdigest(),
              "content_type": media_type, "bytes": len(body), "tables": diagnostics,
              "production_writes": 0, "public_export_enabled": False}
    try:
        positions = mahindra_positions(soup)
        result["accepted_positions"] = len(positions)
        result["named_weight_sum"] = round(sum(row["weight"] for row in positions), 6)
    except ValueError as exc:
        result["parser_error"] = str(exc)
    print("MAHINDRA_TABLE_CONTRACT=" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
