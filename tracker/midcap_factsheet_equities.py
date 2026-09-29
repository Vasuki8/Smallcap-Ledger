"""Equity-only evidence from the reviewed Mahindra and Kotak HTML layouts.

Sector subtotals identify sections, never positions. A sector and the equity
subtotal must reconcile before this module returns any holdings. This is not
full-portfolio reconciliation: cash, fund units and derivatives stay excluded.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag


NAME_HEADERS = {"company / issuer", "issuer/instrument"}
WEIGHT_HEADERS = {"% of net assets", "% to net assets"}
EQUITY_TOTAL = re.compile(r"^Equity\s*(?:and|&)\s*Equity\s+Related\s*(?:-\s*)?Total$", re.I)
EQUITY_SECTION = re.compile(r"^Equity\s*(?:and|&)\s*Equity\s+Related$", re.I)
DATE_LABEL = re.compile(
    r"\bData\s+as\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2}|"
    r"[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2})\b", re.I)


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).casefold())


def validate_factsheet_context(
    soup: BeautifulSoup,
    family: str,
    expected: str,
    *,
    reviewed_heading_aliases: tuple[str, ...] = (),
) -> None:
    """Use an exact reviewed scheme text node and the factsheet's explicit date.

    A current NAV/performance/AUM date somewhere else on the page cannot make an
    older factsheet current. Aliases are opt-in and must be source-reviewed;
    fuzzy/substring matching is never used here.
    """
    accepted = {normalized(family), *(normalized(value) for value in reviewed_heading_aliases)}
    if not any(normalized(text) in accepted for text in soup.stripped_strings):
        raise ValueError("Factsheet lacks the exact staged scheme heading or reviewed alias")
    # Match a leading, standalone Data-as-on label. For example, Kotak also
    # prints "Folio Count data as on ..." for a different reporting period.
    # That qualified metric date must not override the overall factsheet date.
    texts = [clean(text) for text in soup.stripped_strings]
    texts.extend(clean(tag.get_text(" ", strip=True))
                 for tag in soup.find_all(["p", "span", "td", "div"]))
    labels = [match.group(1) for text in texts if (match := DATE_LABEL.match(text))]
    dates = set()
    for raw in labels:
        token = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", raw, flags=re.I)
        token = clean(token.replace(",", " "))
        for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
            try:
                dates.add(datetime.strptime(token, fmt).date())
                break
            except ValueError:
                continue
        else:
            raise ValueError("Unrecognized factsheet data-date label")
    expected_day = date.fromisoformat(expected)
    if dates != {expected_day} or expected_day > date.today():
        raise ValueError(f"Factsheet data date does not uniquely prove current portfolio date {expected}")


def is_bold(tag: Tag) -> bool:
    """Recognize valid font-weight declarations without repairing invalid CSS.

    The reviewed issuers' security rows contain 'f ont-weight'/'fo nt-weight';
    these are invalid property names, not bold sector rows. Do not remove the
    internal space and accidentally promote holdings to section headers.
    """
    for declaration in str(tag.get("style") or "").split(";"):
        name, separator, value = declaration.partition(":")
        if separator and name.strip().casefold() == "font-weight":
            weight = value.strip().casefold().removesuffix("!important").strip()
            return weight in ("bold", "bolder") or (weight.isdigit() and int(weight) >= 600)
    return False


def percentage(value: object) -> Decimal:
    token = clean(value).removesuffix("%").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", token):
        raise ValueError(f"Missing or invalid reported equity weight: {token!r}")
    result = Decimal(token)
    if not Decimal(0) <= result <= Decimal(100):
        raise ValueError("Reported equity weight is outside 0..100")
    return result


def _reconcile(actual: Decimal, reported: Decimal, count: int, label: str) -> None:
    # Source tables publish two decimal places; account only for that rounding.
    tolerance = max(Decimal("0.02"), Decimal("0.005") * (count + 1))
    if abs(actual - reported) > tolerance:
        raise ValueError(f"{label} weights do not reconcile with the reported subtotal")


def _parse_table(table: Tag) -> list[dict] | None:
    rows = [r for r in table.find_all("tr") if r.find_parent("table") is table]
    header = None
    for i, row in enumerate(rows[:8]):
        cells = row.find_all(["td", "th"], recursive=False)
        labels = [clean(c.get_text(" ", strip=True)).casefold() for c in cells]
        names = [j for j, v in enumerate(labels) if v in NAME_HEADERS]
        weights = [j for j, v in enumerate(labels) if v in WEIGHT_HEADERS]
        if len(names) == len(weights) == 1:
            header = (i, names[0], weights[0], len(cells))
            break
    if header is None:
        return None
    start, name_col, weight_col, width = header
    holdings: list[dict] = []
    names_seen: set[str] = set()
    sectors_seen: set[str] = set()
    sector: str | None = None
    reported_sector = Decimal(0)
    sector_sum = Decimal(0)
    sector_count = 0
    total = Decimal(0)
    equity_total_found = False

    def finish_sector() -> None:
        if sector is not None:
            if not sector_count:
                raise ValueError(f"Sector {sector!r} has no named holdings")
            _reconcile(sector_sum, reported_sector, sector_count, sector)

    for row in rows[start + 1:]:
        cells = row.find_all(["td", "th"], recursive=False)
        values = [clean(c.get_text(" ", strip=True)) for c in cells]
        if not any(values):
            continue
        if len(cells) != width:
            raise ValueError("Portfolio table column layout changed")
        name = values[name_col]
        raw_weight = values[weight_col]
        if name.casefold() in NAME_HEADERS and raw_weight.casefold() in WEIGHT_HEADERS:
            continue
        if EQUITY_SECTION.fullmatch(name) and not raw_weight:
            if holdings:
                raise ValueError("Unexpected repeated equity section")
            continue
        if EQUITY_TOTAL.fullmatch(name):
            finish_sector()
            _reconcile(total, percentage(raw_weight), len(holdings), "Equity")
            equity_total_found = True
            break
        if not name:
            raise ValueError("Portfolio row has a weight but no issuer or sector")
        weight = percentage(raw_weight)
        name_cell = cells[name_col]
        sector_row = is_bold(row) or is_bold(name_cell) or bool(name_cell.find(["b", "strong"]))
        if sector_row:
            finish_sector()
            if normalized(name) in sectors_seen or normalized(name) in names_seen:
                raise ValueError("Duplicate or ambiguous sector identity")
            sectors_seen.add(normalized(name))
            sector, reported_sector = name, weight
            sector_sum, sector_count = Decimal(0), 0
            continue
        if sector is None:
            raise ValueError("Named row is not within a verified sector section")
        key = normalized(name)
        if not key or key in names_seen or key in sectors_seen:
            raise ValueError("Duplicate or ambiguous holding identity")
        names_seen.add(key)
        holdings.append({"name": name, "weight": float(weight), "sector": sector, "asset_type": "Equity"})
        sector_sum += weight
        total += weight
        sector_count += 1
    if not equity_total_found or not holdings:
        raise ValueError("Factsheet lacks a reconciled equity subtotal")
    return holdings


def equity_positions(soup: BeautifulSoup) -> list[dict]:
    """Accept identical responsive copies, but reject conflicting table evidence."""
    tables = []
    for table in soup.find_all("table"):
        result = _parse_table(table)
        if result is not None:
            tables.append(result)
    if not tables:
        raise ValueError("No supported issuer/weight portfolio table")

    def fingerprint(rows: list[dict]) -> tuple:
        return tuple(sorted((normalized(r["name"]), r["weight"], normalized(r["sector"])) for r in rows))

    first = fingerprint(tables[0])
    if any(fingerprint(rows) != first for rows in tables[1:]):
        raise ValueError("Responsive portfolio tables disagree")
    return tables[0]
