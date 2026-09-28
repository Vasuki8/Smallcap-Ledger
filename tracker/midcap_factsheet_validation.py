"""Read-only Mahindra factsheet row validation; no database or network access.

Sector headings are aggregate rows, even when they contain company-like words.
Only explicit issuer rows under the published portfolio header are returned.
Unknown row shapes and conflicting responsive copies fail closed.
"""
from __future__ import annotations

from decimal import Decimal
import re

from bs4 import BeautifulSoup, Tag

PARSER_VERSION = "mahindra-midcap-issuer-rows-v1"

# Published sector labels in the AMC's August 2026 Mid Cap portfolio table.
# These labels are classification evidence, not inferred holdings or weights.
_SECTOR_LABELS = (
    "Automobile And Auto Components", "Capital Goods", "Chemicals",
    "Construction", "Construction Materials", "Consumer Durables",
    "Consumer Services", "Fast Moving Consumer Goods", "Financial Services",
    "Healthcare", "Information Technology", "Metals & Mining", "Power",
    "Realty", "Services", "Telecommunication",
)
_SUMMARY_LABELS = (
    "Equity and Equity Related Total", "Cash & Other Receivables", "Grand Total",
)
_ISSUER = re.compile(r"(?:\b(?:Limited|Ltd\.?)$|^Bank of [A-Za-z][A-Za-z &.-]+$)", re.I)
_HEADER = ("companyissuer", "ofnetassets")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


_SECTORS = {_norm(value) for value in _SECTOR_LABELS}
_SUMMARIES = {_norm(value) for value in _SUMMARY_LABELS}


def _weight(value: str) -> Decimal:
    token = value.strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?\s*%?", token):
        raise ValueError("Mahindra portfolio weight is missing or malformed")
    number = Decimal(token.rstrip("%").strip())
    if not 0 <= number <= 100:
        raise ValueError("Mahindra portfolio weight is outside 0..100%")
    return number


def _rows(table: Tag) -> list[list[str]]:
    rows = []
    for tr in table.find_all("tr"):
        # Do not count a nested table a second time through its outer container.
        if tr.find_parent("table") is not table:
            continue
        cells = [_clean(cell.get_text(" ", strip=True))
                 for cell in tr.find_all(("td", "th"), recursive=False)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    return rows


def mahindra_positions(soup: BeautifulSoup) -> list[dict]:
    """Return named issuer weights, excluding all published sectors and totals.

    No BER/TER, sector-allocation or performance table can establish a holding.
    A responsive duplicate is accepted only when every named weight agrees.
    This function does not claim a complete portfolio: cash is intentionally not
    included and a complete financial reconciliation is a separate requirement.
    """
    candidates = []
    for table in soup.find_all("table"):
        if table.find("table") is not None:
            continue
        rows = _rows(table)
        starts = [i for i, cells in enumerate(rows)
                  if tuple(_norm(cell) for cell in cells) == _HEADER]
        if not starts:
            continue
        out = []
        seen = set()
        for cells in rows[starts[0] + 1:]:
            if tuple(_norm(cell) for cell in cells) == _HEADER:
                continue
            if len(cells) != 2:
                raise ValueError("Mahindra portfolio row no longer has name and weight columns")
            name, raw_weight = cells
            weight = _weight(raw_weight)
            key = _norm(name)
            if key in _SECTORS or key in _SUMMARIES:
                continue
            if not _ISSUER.search(name):
                raise ValueError(f"Unclassified Mahindra portfolio row: {name[:100]}")
            if key in seen:
                raise ValueError(f"Duplicate Mahindra issuer row: {name[:100]}")
            seen.add(key)
            out.append({"name": name, "weight": float(weight)})
        if sum(Decimal(str(item["weight"])) for item in out) > Decimal("100.5"):
            raise ValueError("Mahindra named issuer weights exceed 100.5%")
        if out:
            candidates.append(out)
    if not candidates:
        return []
    signature = lambda rows: sorted((_norm(row["name"]), Decimal(str(row["weight"])))
                                    for row in rows)
    expected = signature(candidates[0])
    if any(signature(rows) != expected for rows in candidates[1:]):
        raise ValueError("Conflicting Mahindra responsive portfolio tables")
    return candidates[0]
