"""Reviewed first-party benchmark documents for staged Mid Cap funds.

These parsers are intentionally source-specific. They require the exact registered
URL, exact scheme identity and an explicit primary/Tier-I benchmark label. They
never infer a benchmark from category membership and never mark an index series
as available merely because the identity is published.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader


SOURCES = {
    "Aditya Birla Sun Life Midcap Fund": (
        "https://mutualfund.adityabirlacapital.com/empower/Equity-Funds/Midcap-Fund.html"
    ),
    "SBI MIDCAP FUND": (
        "https://www.sbimf.com/docs/default-source/sif-forms/"
        "kim---sbi-midcap-fund.pdf?sfvrsn=f93cc0ce_0"
    ),
}
AMCS = {
    "Aditya Birla Sun Life Midcap Fund": "Aditya Birla Sun Life Mutual Fund",
    "SBI MIDCAP FUND": "SBI Mutual Fund",
}
MAX_BYTES = 16 * 1024 * 1024
PARSER_VERSION = "explicit-benchmark-documents-v1"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", _clean(value).casefold())


def _one(values, label):
    unique = {}
    for value in values:
        unique.setdefault(_norm(value), value)
    if len(unique) != 1:
        raise ValueError(f"{label} must identify one unambiguous benchmark")
    return next(iter(unique.values()))


def _parse_absl(body):
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("ABSL benchmark source is not valid UTF-8 HTML") from exc
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select("script, style, nav, header, footer, aside, template, noscript"):
        element.decompose()
    headings = [
        _clean(tag.get_text(" ", strip=True))
        for tag in soup.find_all(("h1", "h2"))
        if _norm(tag.get_text(" ", strip=True)) == _norm("Aditya Birla Sun Life Midcap Fund")
    ]
    if len(headings) != 1:
        raise ValueError("ABSL page lacks one exact staged Mid Cap scheme heading")
    text = _clean(soup.get_text(" ", strip=True))
    values = [
        _clean(match.group(1))
        for match in re.finditer(
            r"\bBenchmark\s*:\s*(Nifty\s+Midcap\s+150\s+TRI)\b",
            text,
            re.I,
        )
    ]
    primary = _one(values, "ABSL explicit Benchmark label")
    return {
        "primary_benchmark": primary,
        "reported_benchmarks": [primary],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": headings[0],
        "source_locator": "scheme heading; Fund Snapshot Benchmark:",
        "evidence_excerpt": f"Benchmark: {primary}",
        "source_data_as_of": None,
        "benchmark_effective_as_of": None,
        "source_kind": "digital_factsheet_page",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _pdf_first_page_text(body):
    try:
        reader = PdfReader(BytesIO(body), strict=False)
    except Exception as exc:
        raise ValueError("SBI benchmark source is not a readable PDF") from exc
    if not reader.pages:
        raise ValueError("SBI benchmark PDF has no pages")
    try:
        text = reader.pages[0].extract_text()
    except Exception as exc:
        raise ValueError("SBI benchmark PDF first page text could not be extracted") from exc
    text = _clean(text)
    if not text:
        raise ValueError("SBI benchmark PDF first page has no extractable text")
    return text


def _sbi_document_date(text):
    match = re.search(
        r"Key\s+Information\s+Memorandum\s+is\s+dated\s+"
        r"(\d{1,2})\s*(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s*(20\d{2})",
        text,
        re.I,
    )
    if not match:
        return None
    try:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2)} {match.group(3)}", "%d %B %Y"
        ).date().isoformat()
    except ValueError:
        return None


def _parse_sbi(body, *, pdf_text_fn=None):
    text = (pdf_text_fn or _pdf_first_page_text)(body)
    if not re.search(r"\bKIM\s*[-–—]\s*SBI\s+Midcap\s+Fund\b", text, re.I):
        raise ValueError("SBI KIM does not identify the exact Midcap Fund")
    if not re.search(r"\bKEY\s+INFORMATION\s+MEMORANDUM\b", text, re.I):
        raise ValueError("SBI source is not identified as the Key Information Memorandum")
    values = [
        _clean(match.group(1))
        for match in re.finditer(
            r"\bTier\s*I\s+Benchmark\s+i\.?\s*e\.?\s*"
            r"(Nifty\s+Midcap\s+150\s+Index\s+TRI)\b",
            text,
            re.I,
        )
    ]
    primary = _one(values, "SBI Tier-I benchmark")
    document_date = _sbi_document_date(text)
    return {
        "primary_benchmark": primary,
        "reported_benchmarks": [primary],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "KIM – SBI Midcap Fund",
        "source_locator": "KIM first page; Tier I Benchmark i.e.",
        "evidence_excerpt": f"Tier I Benchmark i.e. {primary}",
        "source_data_as_of": None,
        "source_document_as_of": document_date,
        "benchmark_effective_as_of": None,
        "source_kind": "key_information_memorandum",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def parse_source(family, body, *, pdf_text_fn=None):
    if family not in SOURCES:
        raise ValueError("Unregistered benchmark document family")
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized benchmark document")
    if family == "Aditya Birla Sun Life Midcap Fund":
        return _parse_absl(body)
    return _parse_sbi(body, pdf_text_fn=pdf_text_fn)


def inspect_family(family, url, *, fetch_fn=None, now=None, pdf_text_fn=None):
    if family not in SOURCES or url != SOURCES[family]:
        raise ValueError("Benchmark audit requires the exact registered first-party source URL")
    if now is not None and (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        raise ValueError("Observation clock must be timezone-aware")
    if fetch_fn is None:
        from .providers import fetch
        fetch_fn = fetch
    body, _, content_type = fetch_fn(url, archive=False, max_bytes=MAX_BYTES)
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if family == "Aditya Birla Sun Life Midcap Fund":
        if media_type not in ("text/html", "application/xhtml+xml"):
            raise ValueError("ABSL benchmark source did not return HTML")
    elif media_type != "application/pdf":
        raise ValueError("SBI benchmark source did not return PDF")
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
