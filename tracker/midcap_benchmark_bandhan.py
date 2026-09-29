"""Reviewed Bandhan Mid Cap benchmark evidence from an official performance table.

The reader requires:
- the exact registered Bandhan asset URL,
- the exact staged scheme identity in both Regular and Direct plan rows,
- one unambiguous benchmark value associated with those rows.

It records only the published benchmark identity. It does not claim an
importable benchmark series or invent a benchmark effective date.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re

from pypdf import PdfReader


FAMILY = "BANDHAN MID CAP FUND"
AMC = "Bandhan Mutual Fund"
SOURCE = (
    "https://assets.bandhanmutual.com/2025/03/"
    "339eeb25-bandhan-performance-table-feb-2025.pdf"
)
MAX_BYTES = 20 * 1024 * 1024
PARSER_VERSION = "bandhan-midcap-performance-table-v1"


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:.-")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _pdf_text(body):
    try:
        reader = PdfReader(BytesIO(body), strict=False)
    except Exception as exc:
        raise ValueError("Bandhan benchmark source is not a readable PDF") from exc
    if not reader.pages:
        raise ValueError("Bandhan benchmark PDF has no pages")
    pages = []
    for index, page in enumerate(reader.pages[:40], start=1):
        try:
            text = page.extract_text()
        except Exception as exc:
            raise ValueError(
                f"Bandhan benchmark PDF page {index} text could not be extracted"
            ) from exc
        if text:
            pages.append(text)
    joined = "\n".join(pages).strip()
    if not joined:
        raise ValueError("Bandhan benchmark PDF has no extractable text")
    return joined


def parse_source(body, *, pdf_text_fn=None):
    if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
        raise ValueError("Invalid or oversized Bandhan benchmark document")
    text = (pdf_text_fn or _pdf_text)(body)
    flat = _clean(text)

    if _norm("Bandhan Midcap Fund") not in _norm(flat):
        raise ValueError("Bandhan performance table lacks the exact staged scheme identity")
    if not re.search(r"Bandhan\s+Midcap\s+Fund\s*-\s*Regular\s+Plan", flat, re.I):
        raise ValueError("Bandhan performance table lacks the Regular Plan row")
    if not re.search(r"Bandhan\s+Midcap\s+Fund\s*-\s*Direct\s+Plan", flat, re.I):
        raise ValueError("Bandhan performance table lacks the Direct Plan row")

    start = re.search(r"Bandhan\s+Midcap\s+Fund\s*-\s*Regular\s+Plan", flat, re.I)
    end = re.search(
        r"Bandhan\s+Transportation\s+and\s+Logistics\s+Fund",
        flat[start.end():] if start else "",
        re.I,
    )
    if start is None:
        raise ValueError("Bandhan performance table lacks the reviewed scheme block")
    block_end = start.end() + end.start() if end else min(len(flat), start.end() + 1200)
    block = flat[start.start():block_end]

    matches = re.findall(r"\b(BSE\s+150\s+Midcap\s+TRI)\b", block, re.I)
    values = {_norm(value): _clean(value) for value in matches}
    if len(values) != 1:
        raise ValueError("Bandhan scheme block lacks one unambiguous benchmark value")
    value = next(iter(values.values()))

    inception = None
    inception_match = re.search(
        r"Bandhan\s+Midcap\s+Fund\s*-\s*Regular\s+Plan\s+"
        r"(\d{2}-\d{2}-20\d{2})",
        block,
        re.I,
    )
    if inception_match:
        raw = inception_match.group(1)
        try:
            inception = datetime.strptime(raw, "%d-%m-%Y").date().isoformat()
        except ValueError:
            inception = None

    return {
        "family": FAMILY,
        "amc": AMC,
        "status": "recovered",
        "primary_benchmark": value,
        "reported_benchmarks": [value],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": "Bandhan Midcap Fund",
        "source_locator": (
            "Official performance table; exact Bandhan Midcap Fund Regular/Direct "
            "rows and benchmark column"
        ),
        "evidence_excerpt": f"Bandhan Midcap Fund | {value}",
        "source_data_as_of": None,
        "source_document_period": None,
        "benchmark_effective_as_of": None,
        "scheme_inception_as_of": inception,
        "source_kind": "performance_disclosure_pdf",
        "benchmark_series_verified": False,
        "parser_version": PARSER_VERSION,
    }


def inspect_family(family, url, *, fetch_fn=None, now=None, pdf_text_fn=None):
    if family != FAMILY or url != SOURCE:
        raise ValueError("Bandhan benchmark audit requires the exact registered source URL")
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
        raise ValueError("Bandhan benchmark source did not return PDF")
    parsed = parse_source(body, pdf_text_fn=pdf_text_fn)
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        **parsed,
        "source": url,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_content_type": content_type,
        "observed_at": observed.isoformat(),
    }
