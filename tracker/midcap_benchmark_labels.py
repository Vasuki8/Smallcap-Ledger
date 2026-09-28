"""Exact, labeled primary benchmarks for two reviewed first-party fund pages.

No proximity search across navigation/marketing text, no inferred TRI, and no
financial database access. A new publisher structure requires contract review.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re

from bs4 import BeautifulSoup

SOURCES = {
    "Axis Midcap Fund": "https://www.axismf.com/mutual-funds/equity-funds/axis-mid-cap-fund/mc-gp/regular",
    "Mirae Asset Midcap Fund": "https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-midcap-fund",
}
AMCS = {"Axis Midcap Fund": "Axis Mutual Fund", "Mirae Asset Midcap Fund": "Mirae Asset Mutual Fund"}
MAX_BYTES = 4 * 1024 * 1024
PARSER_VERSION = "explicit-primary-benchmark-labels-v1"
# Recognition is deliberately bounded; none of these names is a default value.
INDEX = re.compile(
    r"(?:NIFTY\s+(?:Mid\s*cap\s+(?:100|150)|50)|BSE\s+(?:Mid\s*cap\s+150|150\s+Mid\s*cap))"
    r"(?:\s+Index)?(?:\s*(?:\(\s*(?:TRI|PRI)\s*\)|TRI|PRI|Total\s+Returns?\s+Index|Price\s+Return\s+Index))?",
    re.I,
)


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", _clean(value).casefold())


def _index(value):
    value = _clean(value)
    if not INDEX.fullmatch(value):
        raise ValueError("Publisher benchmark value is missing, ambiguous or outside the reviewed contract")
    return value


def _one(values, label):
    unique = {}
    for value in values:
        unique.setdefault(_norm(value), value)
    if len(unique) != 1:
        raise ValueError(f"{label} must identify one unambiguous benchmark")
    return next(iter(unique.values()))


def _mirae(soup):
    values, excerpts = [], []
    for card in soup.select("div.fund_fact_text"):
        labels = card.find_all("span", recursive=False)
        if not any(_clean(label.get_text(" ", strip=True)).casefold() == "benchmark index" for label in labels):
            continue
        paragraphs = card.find_all("p", recursive=False)
        if len(paragraphs) != 1:
            raise ValueError("Mirae benchmark index card has missing or multiple values")
        values.append(_index(paragraphs[0].get_text(" ", strip=True)))
        excerpts.append(_clean(card.get_text(" ", strip=True)))
    return _one(values, "Mirae benchmark index"), [], excerpts, "div.fund_fact_text > span: benchmark index; sibling p", None


def _axis(soup):
    headings = [_clean(h.get_text(" ", strip=True)) for h in soup.find_all("h4")
                if _clean(h.get_text(" ", strip=True)).startswith("Performance of ")]
    dates = []
    for heading in headings:
        match = re.fullmatch(r"Performance of Axis Mid Cap Fund - Regular Growth as of (.+)", heading)
        if not match:
            raise ValueError("Axis performance heading does not identify the exact registered scheme/plan")
        try:
            dates.append(datetime.strptime(match[1], "%B %d, %Y").date().isoformat())
        except ValueError as exc:
            raise ValueError("Axis performance heading date changed format") from exc
    if not dates or len(set(dates)) != 1:
        raise ValueError("Axis exact scheme performance heading is missing or conflicting")
    banner_values = []
    for banner in soup.select(".since-inception"):
        labels = banner.select("label.benchmark-returns")
        if len(labels) != 1 or _clean(labels[0].get_text(" ", strip=True)) != "Benchmark Returns":
            raise ValueError("Axis banner does not designate primary Benchmark Returns")
        values = banner.select("label.nifty-multicap-text")
        if len(values) != 1:
            raise ValueError("Axis banner benchmark is missing or ambiguous")
        banner_values.append(_index(values[0].get_text(" ", strip=True)))
    banner_value = _one(banner_values, "Axis banner")
    primary, additional, units, excerpts = [], [], set(), []
    for cell in soup.select("tr.header-title > th"):
        labels = cell.find_all("span")
        for label in labels:
            key = re.sub(r"\s+", "", label.get_text(" ", strip=True)).casefold()
            if key not in ("benchmark(%)", "benchmark(₹)", "additionalbenchmark(%)", "additionalbenchmark(₹)"):
                continue
            # Only text outside this role label is the index, not a neighbouring cell.
            copy = BeautifulSoup(str(cell), "html.parser").find("th")
            for child in copy.find_all("span"):
                child.decompose()
            value = _index(copy.get_text(" ", strip=True))
            if key.startswith("additional"):
                additional.append(value)
            else:
                primary.append(value)
                units.add(key)
            excerpts.append(_clean(cell.get_text(" ", strip=True)))
    if units != {"benchmark(%)", "benchmark(₹)"}:
        raise ValueError("Axis primary percentage and rupee benchmark columns are required")
    primary_value = _one(primary, "Axis primary table columns")
    if _norm(primary_value) != _norm(banner_value):
        raise ValueError("Axis banner and primary table benchmarks conflict")
    return primary_value, list(dict.fromkeys(additional)), excerpts, "h4 scheme performance; .since-inception; th Benchmark(%)/Benchmark(₹)", dates[0]


def parse_page(family, body):
    if family not in SOURCES:
        raise ValueError("Unregistered benchmark family")
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized benchmark page")
    soup = BeautifulSoup(body.decode("utf-8"), "html.parser")
    for element in soup.select("script, style, nav, header, footer, aside, template, noscript"):
        element.decompose()
    headings = [_clean(h.get_text(" ", strip=True)) for h in soup.find_all("h1")]
    if not headings or {_norm(h) for h in headings} != {_norm(family)}:
        raise ValueError("Page lacks an exact, unambiguous staged scheme heading")
    primary, additional, excerpts, locator, performance_day = (
        _axis(soup) if family == "Axis Midcap Fund" else _mirae(soup))
    variant = "total_return" if re.search(r"\bTRI\b|Total\s+Returns?", primary, re.I) else (
        "price_return" if re.search(r"\bPRI\b|Price\s+Return", primary, re.I) else "unspecified")
    return {
        "primary_benchmark": primary, "reported_benchmarks": [primary],
        "additional_benchmarks": additional, "benchmark_role": "primary",
        "return_variant": variant, "source_heading": headings[0],
        "source_locator": locator, "evidence_excerpt": " | ".join(dict.fromkeys(excerpts)),
        "source_data_as_of": None, "benchmark_effective_as_of": None,
        "source_performance_as_of": performance_day, "source_kind": "current_fund_page",
        "benchmark_series_verified": False, "parser_version": PARSER_VERSION,
    }


def inspect_family(family, url, *, fetch_fn=None, now=None):
    if family not in SOURCES or url != SOURCES[family]:
        raise ValueError("Benchmark audit requires the exact registered first-party fund URL")
    if now is not None and (not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("Observation clock must be timezone-aware")
    if fetch_fn is None:
        from .providers import fetch
        fetch_fn = fetch
    body, _, content_type = fetch_fn(url, archive=False, max_bytes=MAX_BYTES)
    if str(content_type).split(";", 1)[0].strip().lower() not in ("text/html", "application/xhtml+xml"):
        raise ValueError("Benchmark source did not return HTML")
    parsed = parse_page(family, body)
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if parsed["source_performance_as_of"] and parsed["source_performance_as_of"] > observed.date().isoformat():
        raise ValueError("Source performance reporting date is in the future")
    return {
        "family": family, "amc": AMCS[family], "status": "recovered", **parsed,
        "source": url, "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_content_type": content_type, "observed_at": observed.isoformat(),
    }
