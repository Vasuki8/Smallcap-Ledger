"""Reviewed ITI and JM Mid Cap benchmark sources.

Both readers require the exact registered first-party URL and an explicit
publisher benchmark field. JM's publisher currently uses the reviewed alias
"JM Midcap Fund" while the staged AMFI family is "JM Mid Cap Fund".
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re

from bs4 import BeautifulSoup


SOURCES = {
    "ITI Mid Cap Fund": (
        "https://www.itiamc.com/digitalfactsheet/August2026/innerpages/Mid-Cap.html"
    ),
    "JM Mid Cap Fund": (
        "https://docviewer.jmfinancialmf.com/jmmidcapfund/jmmidcapfund/Index.aspx"
    ),
}
AMCS = {
    "ITI Mid Cap Fund": "ITI Mutual Fund",
    "JM Mid Cap Fund": "JM Financial Mutual Fund",
}
ALIASES = {
    "ITI Mid Cap Fund": ("ITI Mid Cap Fund",),
    "JM Mid Cap Fund": ("JM Midcap Fund",),
}
MAX_BYTES = 8 * 1024 * 1024
PARSER_VERSION = "explicit-midcap-benchmark-iti-jm-v1"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:.-")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _text(body):
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized benchmark page")
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Benchmark page is not valid UTF-8 HTML") from exc
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def _require_alias(text, family):
    normalized = _norm(text)
    if not any(_norm(alias) in normalized for alias in ALIASES[family]):
        raise ValueError("First-party page does not contain the reviewed exact scheme identity/alias")


def _base(family, value, locator, excerpt, additional=None, source_data_as_of=None):
    return {
        "family": family,
        "status": "recovered",
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": list(additional or []),
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": ALIASES[family][0],
        "source_locator": locator,
        "evidence_excerpt": excerpt,
        "source_data_as_of": source_data_as_of,
        "benchmark_effective_as_of": None,
        "source_kind": "digital_factsheet_page" if family == "ITI Mid Cap Fund" else "current_fund_page",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_iti(text):
    family = "ITI Mid Cap Fund"
    _require_alias(text, family)
    values = re.findall(
        r"\bBenchmark\s*:\s*(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I,
    )
    unique = {_norm(value): _clean(value) for value in values}
    if len(unique) != 1:
        raise ValueError("ITI page lacks one unambiguous reviewed Benchmark value")
    value = next(iter(unique.values()))
    as_of = None
    match = re.search(r"Data\s+is\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})", text, re.I)
    if match:
        try:
            as_of = datetime.strptime(_clean(match.group(1)), "%B %d, %Y").date().isoformat()
        except ValueError:
            as_of = None
    return _base(
        family, value,
        "Digital factsheet Scheme Details; Benchmark field",
        f"Benchmark: {value}",
        additional=["Nifty 50 TRI"] if re.search(r"Additional\s+Benchmark\s*:\s*Nifty\s+50\s+TRI", text, re.I) else [],
        source_data_as_of=as_of,
    )


def _parse_jm(text):
    family = "JM Mid Cap Fund"
    _require_alias(text, family)
    values = re.findall(
        r"(?<!Additional )\bBenchmark(?:\s+Index)?\s*:?\s*(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I,
    )
    unique = {_norm(value): _clean(value) for value in values}
    if len(unique) != 1:
        raise ValueError("JM page lacks one unambiguous Benchmark Index value")
    value = next(iter(unique.values()))
    additional = []
    for raw in re.findall(
        r"Additional\s+Benchmark(?:\s+Index)?\s*:?\s*(Nifty\s+50\s+TRI)\b",
        text,
        re.I,
    ):
        cleaned = _clean(raw)
        if _norm(cleaned) not in {_norm(x) for x in additional}:
            additional.append(cleaned)
    return _base(
        family, value,
        "JM Midcap Fund scheme microsite; Benchmark field",
        f"Benchmark: {value}",
        additional=additional,
    )


PARSERS = {
    "ITI Mid Cap Fund": _parse_iti,
    "JM Mid Cap Fund": _parse_jm,
}


def parse_source(family, body):
    if family not in SOURCES:
        raise ValueError("Unregistered ITI/JM benchmark family")
    return PARSERS[family](_text(body))


def inspect_family(family, url, *, fetch_fn=None, now=None):
    if family not in SOURCES or url != SOURCES[family]:
        raise ValueError("Benchmark audit requires the exact registered first-party source URL")
    if now is not None and (
        not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None
    ):
        raise ValueError("Observation clock must be timezone-aware")
    if fetch_fn is None:
        from .providers import fetch
        fetch_fn = fetch
    body, _, content_type = fetch_fn(url, archive=False, max_bytes=MAX_BYTES)
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if media_type not in ("text/html", "application/xhtml+xml"):
        raise ValueError("ITI/JM benchmark source did not return HTML")
    parsed = parse_source(family, body)
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        **parsed,
        "amc": AMCS[family],
        "source": url,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_content_type": content_type,
        "observed_at": observed.isoformat(),
    }
