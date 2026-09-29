"""Reviewed first-party benchmark documents for three staged Mid Cap funds.

These readers are deliberately source-specific. They require exact registered
first-party URLs, reviewed scheme identities and explicit publisher benchmark
roles. Historical document dates remain explicit; no currentness is invented
and no index time series is implied by a reported benchmark identity.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re

from pypdf import PdfReader


SOURCES = {
    "UTI - Mid Cap Fund": (
        "https://doc.utimf.com/uticontainer/"
        "UTI%20Mid%20Cap%20Fund%20-%20SID%2029%20October%20202120211109-060535.pdf"
    ),
    "ICICI Prudential Mid Cap Fund": (
        "https://www.icicipruamc.com/blob/knowledgecentre/factsheet-abridged/Abridged.pdf"
    ),
    "Union Midcap Fund": (
        "https://unionmf.com/docs/default-source/funddetail-downloads/kim/"
        "union-midcap-fund.pdf?sfvrsn=4c6e3f39_6"
    ),
}
AMCS = {
    "UTI - Mid Cap Fund": "UTI Mutual Fund",
    "ICICI Prudential Mid Cap Fund": "ICICI Prudential Mutual Fund",
    "Union Midcap Fund": "Union Mutual Fund",
}
MAX_BYTES = 24 * 1024 * 1024
PARSER_VERSION = "midcap-benchmark-gate3-v1"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:.-")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _pdf_text(body, max_pages=40):
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


def _base(value, *, heading, locator, excerpt, source_kind,
          document_as_of=None, data_as_of=None, additional=None):
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": list(additional or []),
        "benchmark_role": "primary",
        "return_variant": (
            "total_return"
            if re.search(r"\b(?:TRI|Total\s+Return)", value, re.I)
            else "publisher_unspecified"
        ),
        "source_heading": heading,
        "source_locator": locator,
        "evidence_excerpt": excerpt,
        "source_data_as_of": data_as_of,
        "source_document_as_of": document_as_of,
        "benchmark_effective_as_of": None,
        "source_kind": source_kind,
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_uti(text):
    if _norm("UTI Mid Cap Fund") not in _norm(text):
        raise ValueError("UTI SID lacks the reviewed exact scheme identity")
    base = re.findall(
        r"\bBenchmark\s+(Nifty\s+Midcap\s+150)\b(?!\s+TRI)",
        text,
        re.I,
    )
    tri = re.findall(
        r"Total\s+Return\s+Variant\s+of\s+the\s+benchmark\s+index\s+that\s+is\s+"
        r"(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I | re.S,
    )
    base_values = {_norm(v): _clean(v) for v in base}
    tri_values = {_norm(v): _clean(v) for v in tri}
    if len(base_values) != 1 or len(tri_values) != 1:
        raise ValueError("UTI SID lacks one reviewed benchmark and total-return variant")
    base_value = next(iter(base_values.values()))
    value = next(iter(tri_values.values()))
    if _norm(value).replace("tri", "") != _norm(base_value):
        raise ValueError("UTI benchmark and total-return variant do not agree")
    return _base(
        value,
        heading="UTI Mid Cap Fund",
        locator="SID Highlights / performance note; benchmark plus explicit Total Return Variant",
        excerpt=f"Benchmark {base_value} | Total Return Variant {value}",
        source_kind="scheme_information_document",
        document_as_of="2021-10-29",
    )


def _parse_icici(text):
    if _norm("ICICI Prudential Midcap Fund") not in _norm(text):
        raise ValueError("ICICI abridged factsheet lacks the exact staged scheme identity")
    matches = re.findall(
        r"(Nifty\s+Midcap\s+150\s+TRI)\s*\(\s*Benchmark\s*\)",
        text,
        re.I,
    )
    values = {_norm(v): _clean(v) for v in matches}
    if len(values) != 1:
        raise ValueError("ICICI factsheet lacks one unambiguous Benchmark row")
    value = next(iter(values.values()))
    additional = []
    for match in re.findall(
        r"(Nifty\s+50\s+TRI)\s*\(\s*Additional\s+Benchmark\s*\)",
        text,
        re.I,
    ):
        cleaned = _clean(match)
        if _norm(cleaned) not in {_norm(x) for x in additional}:
            additional.append(cleaned)
    data_as_of = None
    date_match = re.search(
        r"ICICI\s+Prudential\s+Midcap\s+Fund.{0,600}?as\s+on\s+"
        r"([A-Za-z]+\s+\d{1,2},\s*20\d{2})",
        text,
        re.I | re.S,
    )
    if date_match:
        try:
            data_as_of = datetime.strptime(
                _clean(date_match.group(1)), "%B %d, %Y"
            ).date().isoformat()
        except ValueError:
            data_as_of = None
    return _base(
        value,
        heading="ICICI Prudential Midcap Fund",
        locator="Abridged factsheet performance table; explicit (Benchmark) row",
        excerpt=f"{value} (Benchmark)",
        source_kind="abridged_factsheet_pdf",
        data_as_of=data_as_of,
        additional=additional,
    )


def _parse_union(text):
    if _norm("Union Midcap Fund") not in _norm(text):
        raise ValueError("Union KIM lacks the exact staged scheme identity")
    matches = re.findall(
        r"benchmark\s+for\s+the\s+Scheme\s+is\s+"
        r"(BSE\s+150\s+Midcap\s+Index\s*\(TRI\))",
        text,
        re.I,
    )
    values = {_norm(v): _clean(v) for v in matches}
    if len(values) != 1:
        raise ValueError("Union KIM lacks one reviewed scheme benchmark value")
    value = next(iter(values.values()))
    additional = []
    for match in re.findall(
        r"(BSE\s+Sensex\s+Index\s*\(TRI\))",
        text,
        re.I,
    ):
        cleaned = _clean(match)
        if _norm(cleaned) not in {_norm(x) for x in additional}:
            additional.append(cleaned)
    data_as_of = None
    date_match = re.search(
        r"\*The\s+data\s+is\s+as\s+on\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})",
        text,
        re.I,
    )
    if date_match:
        try:
            data_as_of = datetime.strptime(
                _clean(date_match.group(1)), "%B %d, %Y"
            ).date().isoformat()
        except ValueError:
            data_as_of = None
    return _base(
        value,
        heading="Union Midcap Fund",
        locator="KIM performance disclosure; 'benchmark for the Scheme is' statement",
        excerpt=f"The benchmark for the Scheme is {value}",
        source_kind="key_information_memorandum",
        data_as_of=data_as_of,
        additional=additional,
    )


PARSERS = {
    "UTI - Mid Cap Fund": _parse_uti,
    "ICICI Prudential Mid Cap Fund": _parse_icici,
    "Union Midcap Fund": _parse_union,
}


def parse_source(family, body, *, pdf_text_fn=None):
    if family not in SOURCES:
        raise ValueError("Unregistered benchmark-document family")
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized benchmark document")
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
    if media_type != "application/pdf":
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
