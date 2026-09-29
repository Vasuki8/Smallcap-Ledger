"""Reviewed explicit benchmark sources for five staged Mid Cap funds.

Each parser is source-specific and requires:
- the exact registered first-party URL,
- the exact staged family identity,
- an explicit publisher benchmark role/value,
- original publisher wording.

No benchmark is inferred from Mid Cap category membership and no index series is
considered available merely because the identity is published.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader


SOURCES = {
    "Quant Mid Cap Fund": "https://quantmutual.com/equity/opportunities-fund",
    "Samco Mid Cap Fund": "https://www.samcomf.com/faqs",
    "Union Midcap Fund": "https://www.unionmf.com/docs/default-source/funddetail-downloads/presentation/union-midcap-fund.pdf",
    "Edelweiss Mid Cap Fund": "https://www.edelweissmf.com/Files/downloads/Product%20Collateral/Factsheet/2026/May/published/MidcapFund_21052026_114313_AM.pdf",
    "LIC MF Mid Cap Fund": "https://www.licmf.com/assets/downloads/sai_sid_kim/2025-2026/16.%20Scheme%20Information%20Document%20-%20LIC%20MF%20Mid%20Cap%20Fund.pdf",
}
AMCS = {
    "Quant Mid Cap Fund": "quant Mutual Fund",
    "Samco Mid Cap Fund": "Samco Mutual Fund",
    "Union Midcap Fund": "Union Mutual Fund",
    "Edelweiss Mid Cap Fund": "Edelweiss Mutual Fund",
    "LIC MF Mid Cap Fund": "LIC Mutual Fund",
}
HTML_FAMILIES = {"Quant Mid Cap Fund", "Samco Mid Cap Fund"}
MAX_BYTES = 20 * 1024 * 1024
PARSER_VERSION = "explicit-midcap-benchmark-five-v1"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:.-")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _require_family(text, family):
    if _norm(family) not in _norm(text):
        raise ValueError("Source does not contain the exact staged Mid Cap family identity")


def _pdf_text(body, max_pages=3):
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


def _parse_quant(text):
    _require_family(text, "Quant Mid Cap Fund")
    match = re.search(
        r"quant\s+Mid\s+Cap\s+Fund.{0,1200}?Benchmark\s+Index\s+"
        r"(Nifty\s+Mid\s+Cap\s+150\s+TRI)\b",
        text,
        re.I | re.S,
    )
    if not match:
        raise ValueError("Quant source lacks the reviewed Benchmark Index value")
    value = _clean(match.group(1))
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "quant Mid Cap Fund",
        "source_locator": "Fund page; Benchmark Index field",
        "evidence_excerpt": f"Benchmark Index {value}",
        "source_data_as_of": None,
        "benchmark_effective_as_of": None,
        "source_kind": "current_fund_page",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_samco(text):
    _require_family(text, "Samco Mid Cap Fund")
    match = re.search(
        r"What\s+is\s+the\s+benchmark\s+for\s+Samco\s+Mid\s+Cap\s+Fund\?\s*"
        r"(?:Image\s*:\s*Arrow\s*)?"
        r"The\s+benchmark\s+for\s+this\s+scheme\s+is\s+the\s+"
        r"(Nifty\s+Midcap\s+150\s+Total\s+Returns\s+Index)\b",
        text,
        re.I | re.S,
    )
    if not match:
        raise ValueError("Samco FAQ lacks the reviewed scheme-specific benchmark answer")
    value = _clean(match.group(1))
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "Samco Mid Cap Fund",
        "source_locator": "FAQ; exact scheme benchmark question and answer",
        "evidence_excerpt": f"The benchmark for this scheme is the {value}",
        "source_data_as_of": None,
        "benchmark_effective_as_of": None,
        "source_kind": "current_faq_page",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_union(text):
    _require_family(text, "Union Midcap Fund")
    match = re.search(
        r"UNION\s+MIDCAP\s+FUND.{0,2500}?Benchmark\s+Index\s+"
        r"(BSE\s+150\s+MidCap\s+Index\s*\(TRI\))\b",
        text,
        re.I | re.S,
    )
    if not match:
        raise ValueError("Union presentation lacks the reviewed Benchmark Index value")
    value = _clean(match.group(1))
    as_of = None
    date_match = re.search(
        r"Data\s+is\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})",
        text,
        re.I,
    )
    if date_match:
        try:
            as_of = datetime.strptime(_clean(date_match.group(1)), "%B %d, %Y").date().isoformat()
        except ValueError:
            as_of = None
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "UNION MIDCAP FUND",
        "source_locator": "Fund presentation; Benchmark Index field",
        "evidence_excerpt": f"Benchmark Index {value}",
        "source_data_as_of": as_of,
        "benchmark_effective_as_of": None,
        "source_kind": "fund_presentation_pdf",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_edelweiss(text):
    _require_family(text, "Edelweiss Mid Cap Fund")
    match = re.search(
        r"Edelweiss\s+Mid\s+Cap\s+Fund.{0,1800}?\bBenchmark\s+"
        r"(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I | re.S,
    )
    if not match:
        raise ValueError("Edelweiss factsheet lacks the reviewed Benchmark value")
    value = _clean(match.group(1))
    as_of = None
    date_match = re.search(r"Data\s+as\s+on\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})", text, re.I)
    if date_match:
        try:
            as_of = datetime.strptime(_clean(date_match.group(1)), "%B %d, %Y").date().isoformat()
        except ValueError:
            as_of = None
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "Edelweiss Mid Cap Fund",
        "source_locator": "Fund factsheet; About the Scheme Benchmark field",
        "evidence_excerpt": f"Benchmark {value}",
        "source_data_as_of": as_of,
        "benchmark_effective_as_of": None,
        "source_kind": "fund_factsheet_pdf",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def _parse_lic(text):
    _require_family(text, "LIC MF Mid Cap Fund")
    match = re.search(
        r"LIC\s+MF\s+Mid\s+Cap\s+Fund.{0,3500}?"
        r"(?:As\s+per\s+AMFI\s+)?Tier\s+I\s+Benchmark\s+i\.?\s*e\.?\s+"
        r"(Nifty\s+Midcap\s+150\s+TRI)\b",
        text,
        re.I | re.S,
    )
    if not match:
        raise ValueError("LIC SID lacks the reviewed Tier I benchmark value")
    value = _clean(match.group(1))
    return {
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "LIC MF Mid Cap Fund",
        "source_locator": "SID section I; Benchmark Riskometer Tier I label",
        "evidence_excerpt": f"As per AMFI Tier I Benchmark i.e. {value}",
        "source_data_as_of": None,
        "benchmark_effective_as_of": None,
        "source_kind": "scheme_information_document",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


PARSERS = {
    "Quant Mid Cap Fund": _parse_quant,
    "Samco Mid Cap Fund": _parse_samco,
    "Union Midcap Fund": _parse_union,
    "Edelweiss Mid Cap Fund": _parse_edelweiss,
    "LIC MF Mid Cap Fund": _parse_lic,
}


def parse_source(family, body, *, pdf_text_fn=None):
    if family not in SOURCES:
        raise ValueError("Unregistered explicit benchmark family")
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
            raise ValueError("Explicit benchmark HTML source did not return HTML")
    elif media_type != "application/pdf":
        raise ValueError("Explicit benchmark document did not return PDF")
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
