"""Reviewed first-party benchmark sources for three staged Mid Cap funds.

Source-specific parsing preserves each publisher's exact primary benchmark
wording and keeps additional comparators separate. Scheme aliases are accepted
only where the publisher itself currently uses a reviewed name that differs
from the staged AMFI family spelling.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader


SOURCES = {
    "Franklin India Mid Cap Fund": (
        "https://www.franklintempletonindia.com/static/factsheet/Innerpage/"
        "Franklin-India-Prima-Fund.html"
    ),
    "Motilal Oswal Midcap Fund": (
        "https://www.motilaloswalmf.com/mutual-funds/motilal-oswal-midcap-fund"
    ),
    "HSBC Midcap Fund": (
        "https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/"
        "f73ce2a0-34a8-4ecc-8740-f9017e53e73e/hsbc-midcap-fund-jan-2026.pdf"
    ),
}
AMCS = {
    "Franklin India Mid Cap Fund": "Franklin Templeton Mutual Fund",
    "Motilal Oswal Midcap Fund": "Motilal Oswal Mutual Fund",
    "HSBC Midcap Fund": "HSBC Mutual Fund",
}
ALIASES = {
    "Franklin India Mid Cap Fund": (
        "Franklin India Mid Cap Fund",
        "Franklin India Mid Cap Fund (Erstwhile Franklin India Prima Fund)",
    ),
    "Motilal Oswal Midcap Fund": ("Motilal Oswal Midcap Fund",),
    "HSBC Midcap Fund": ("HSBC Midcap Fund",),
}
HTML_FAMILIES = {
    "Franklin India Mid Cap Fund",
    "Motilal Oswal Midcap Fund",
}
MAX_BYTES = 20 * 1024 * 1024
PARSER_VERSION = "explicit-midcap-benchmark-four-v2"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:.-")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _require_alias(text, family):
    normalized = _norm(text)
    if not any(_norm(alias) in normalized for alias in ALIASES[family]):
        raise ValueError("Source does not contain a reviewed exact scheme identity/alias")


def _pdf_text(body, max_pages=4):
    try:
        reader = PdfReader(BytesIO(body), strict=False)
    except Exception as exc:
        raise ValueError("Benchmark source is not a readable PDF") from exc
    if not reader.pages:
        raise ValueError("Benchmark PDF has no pages")
    pages = []
    for index, page in enumerate(reader.pages[:max_pages], start=1):
        try:
            text = page.extract_text()
        except Exception as exc:
            raise ValueError(f"Benchmark PDF page {index} text could not be extracted") from exc
        if text:
            pages.append(text)
    joined = "\n".join(pages).strip()
    if not joined:
        raise ValueError("Benchmark PDF has no extractable text")
    return joined


def _parse_date(text, patterns):
    values = []
    for pattern, fmt in patterns:
        for match in re.finditer(pattern, text, re.I):
            raw = _clean(match.group(1))
            try:
                values.append(datetime.strptime(raw, fmt).date())
            except ValueError:
                pass
    return max(values).isoformat() if values else None


def _base(value, *, source_heading, source_locator, evidence_excerpt,
          source_kind, source_data_as_of=None, source_document_period=None):
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": (
            "total_return"
            if re.search(r"\b(?:TRI|Total\s+Returns?\s+Index)\b", value, re.I)
            else "publisher_unspecified"
        ),
        "source_heading": source_heading,
        "source_locator": source_locator,
        "evidence_excerpt": evidence_excerpt,
        "source_data_as_of": source_data_as_of,
        "source_document_period": source_document_period,
        "benchmark_effective_as_of": None,
        "source_kind": source_kind,
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_franklin(text):
    family = "Franklin India Mid Cap Fund"
    _require_alias(text, family)
    matches = re.findall(
        r"\bBENCHMARK\s*:?\s*(Nifty\s+Midcap\s+150)(?!\s+TRI)\b",
        text,
        re.I,
    )
    values = {_norm(x): _clean(x) for x in matches}
    if len(values) != 1:
        raise ValueError("Franklin factsheet lacks one unambiguous reviewed BENCHMARK value")
    value = next(iter(values.values()))
    as_of = _parse_date(text, ((r"\bAs\s+on\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})", "%B %d, %Y"),))
    return _base(
        value,
        source_heading="Franklin India Mid Cap Fund (Erstwhile Franklin India Prima Fund)",
        source_locator="Static factsheet inner page; BENCHMARK field",
        evidence_excerpt=f"BENCHMARK: {value}",
        source_kind="static_factsheet_page",
        source_data_as_of=as_of,
    )


def _parse_motilal(text):
    family = "Motilal Oswal Midcap Fund"
    _require_alias(text, family)
    matches = re.findall(
        r"\bBenchmark\s*:?[ \t]*(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I,
    )
    values = {_norm(x): _clean(x) for x in matches}
    if len(values) != 1:
        raise ValueError("Motilal Oswal page lacks one unambiguous Benchmark value")
    value = next(iter(values.values()))
    as_of = _parse_date(
        text,
        ((r"latestAumAsOnDt\s*:?\s*(20\d{2}-\d{2}-\d{2})T", "%Y-%m-%d"),),
    )
    return _base(
        value,
        source_heading="Motilal Oswal Midcap Fund",
        source_locator="Current fund page; Benchmark field / PRIMARY benchmark data",
        evidence_excerpt=f"Benchmark {value}",
        source_kind="current_fund_page",
        source_data_as_of=as_of,
    )


def _parse_hsbc(text):
    family = "HSBC Midcap Fund"
    _require_alias(text, family)
    matches = re.findall(
        r"Scheme\s+Benchmark\s*\(\s*(NIFTY\s+Midcap\s+150\s+TRI)\s*\)",
        text,
        re.I,
    )
    values = {_norm(x): _clean(x) for x in matches}
    if len(values) != 1:
        raise ValueError("HSBC product note lacks one unambiguous Scheme Benchmark value")
    value = next(iter(values.values()))
    additional = []
    for match in re.findall(
        r"Additional\s+Benchmark\s*\(\s*(Nifty\s+50\s+TRI)\s*\)",
        text,
        re.I,
    ):
        cleaned = _clean(match)
        if _norm(cleaned) not in {_norm(x) for x in additional}:
            additional.append(cleaned)
    result = _base(
        value,
        source_heading="HSBC Midcap Fund",
        source_locator="Product note; Scheme Benchmark rows",
        evidence_excerpt=f"Scheme Benchmark ({value})",
        source_kind="product_note_pdf",
        source_document_period="2026-01",
    )
    result["additional_benchmarks"] = additional
    return result


PARSERS = {
    "Franklin India Mid Cap Fund": _parse_franklin,
    "Motilal Oswal Midcap Fund": _parse_motilal,
    "HSBC Midcap Fund": _parse_hsbc,
}


def parse_source(family, body, *, pdf_text_fn=None):
    if family not in SOURCES:
        raise ValueError("Unregistered benchmark family")
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized benchmark source")
    if family in HTML_FAMILIES:
        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Benchmark HTML source is not UTF-8") from exc
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    else:
        text = (pdf_text_fn or _pdf_text)(body)
    return PARSERS[family](text)


def inspect_family(family, url, *, fetch_fn=None, now=None, pdf_text_fn=None):
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
    if family in HTML_FAMILIES:
        if media_type not in ("text/html", "application/xhtml+xml"):
            raise ValueError("Benchmark page did not return HTML")
    elif media_type != "application/pdf":
        raise ValueError("Benchmark document did not return PDF")
    parsed = parse_source(family, body, pdf_text_fn=pdf_text_fn)
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "family": family,
        "amc": AMCS[family],
        "status": "recovered",
        **parsed,
        "source": url,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_content_type": content_type,
        "observed_at": observed.isoformat(),
    }
