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
PARSER_VERSION = "explicit-benchmark-documents-v2"


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
    expected = _norm("Aditya Birla Sun Life Midcap Fund")
    headings = [tag for tag in soup.find_all(("h1", "h2"))
                if _norm(tag.get_text(" ", strip=True)) == expected]
    other_funds = [tag for tag in soup.find_all(("h1", "h2"))
                   if _norm(tag.get_text()).startswith("adityabirlasunlife")
                   and _norm(tag.get_text()) != expected]
    if len(headings) != 1 or other_funds:
        raise ValueError("ABSL page lacks one unambiguous exact staged scheme heading")

    # Read the full value from the designated table, not an expected-name
    # substring anywhere near the word 'Benchmark'. Unknown duplicates matter.
    headers = [cell for cell in soup.find_all("td")
               if _clean(cell.get_text(" ", strip=True)).casefold() == "fund snapshot"]
    if len(headers) != 1 or headers[0].find_parent("table") is None:
        raise ValueError("ABSL requires one Fund Snapshot table")
    table = headers[0].find_parent("table")
    values, excerpts = [], []
    for cell in table.find_all("td"):
        if cell.find_parent("table") is not table:
            continue
        text = _clean(cell.get_text(" ", strip=True))
        match = re.fullmatch(r"Benchmark\s*:\s*(.*)", text, re.I)
        if not match:
            continue
        value = _clean(match[1])
        if not re.fullmatch(r"Nifty\s+Midcap\s+150\s+TRI", value, re.I):
            raise ValueError("ABSL primary value is missing or outside the reviewed contract")
        values.append(value)
        excerpts.append(text)
    primary = _one(values, "ABSL Fund Snapshot primary label")

    # A month printed in the scheme banner is a document period, not an
    # invented effective date or a date borrowed from the NAV/AUM table.
    periods = []
    banner = headings[0].parent
    paragraphs = banner.find_all("p", recursive=False) if banner.name == "div" else []
    for paragraph in paragraphs:
        label = _clean(paragraph.get_text(" ", strip=True))
        if re.fullmatch(r"[A-Za-z]+ 20\d{2}", label):
            try:
                periods.append(datetime.strptime(label, "%B %Y").strftime("%Y-%m"))
            except ValueError as exc:
                raise ValueError("ABSL scheme-banner period is malformed") from exc
    period = _one(periods, "ABSL scheme-banner period") if periods else None
    return {
        "primary_benchmark": primary,
        "reported_benchmarks": [primary],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": _clean(headings[0].get_text(" ", strip=True)),
        "source_locator": "Fund Snapshot table; complete Benchmark: cell",
        "evidence_excerpt": " | ".join(dict.fromkeys(excerpts)),
        "source_document_period": period,
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
    if not isinstance(text, str) or not text.strip():
        raise ValueError("SBI benchmark PDF first page has no extractable text")
    return text.strip()


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
    if not isinstance(text, str) or not text.strip():
        raise ValueError("SBI KIM has no extractable first-page text")
    headers = [_clean(line) for line in text.splitlines()
               if re.match(r"KIM\s*[-–—]", _clean(line), re.I)]
    if len(headers) != 1 or not re.fullmatch(r"KIM\s*[-–—]\s*SBI Midcap Fund", headers[0], re.I):
        raise ValueError("SBI KIM requires one exact full scheme heading")
    if not re.search(r"\bKEY\s+INFORMATION\s+MEMORANDUM\b", text, re.I):
        raise ValueError("SBI source is not identified as the Key Information Memorandum")

    # Bound the primary value by the actual first-page riskometer and investor
    # footnote. Count every Tier-I label before looking at any index value.
    roles = list(re.finditer(r"\bTier\s+I\s+Benchmark\b", text, re.I))
    if len(roles) != 1:
        raise ValueError("SBI KIM requires exactly one Tier-I benchmark block")
    role = roles[0]
    line_start = text.rfind("\n", 0, role.start()) + 1
    if text[line_start:role.start()].strip():
        raise ValueError("SBI Tier-I role has an unreviewed prefix")
    if not re.search(r"Benchmark\s+Riskometer\b", text[:role.start()], re.I):
        raise ValueError("SBI Tier-I block lacks its Benchmark Riskometer scope")
    tail = text[role.end():]
    end = re.search(r"\*Investors\s+should\s+consult\b", tail, re.I)
    if end is None:
        raise ValueError("SBI Tier-I block lacks the reviewed investor-footnote boundary")
    block = _clean(tail[:end.start()])
    value_match = re.fullmatch(r"i\.?\s*e\.?\s+(.*)", block, re.I)
    primary = _clean(value_match[1]) if value_match else ""
    if not re.fullmatch(r"Nifty\s+Midcap\s+150\s+Index\s+TRI", primary, re.I):
        raise ValueError("SBI full Tier-I value is missing or outside the reviewed contract")
    document_date = _sbi_document_date(text)
    return {
        "primary_benchmark": primary,
        "reported_benchmarks": [primary],
        "additional_benchmarks": [],
        "benchmark_role": "primary",
        "return_variant": "total_return",
        "source_heading": headers[0],
        "source_page": 1,
        "source_locator": "KIM page 1; Benchmark Riskometer Tier I; investor-footnote boundary",
        "evidence_excerpt": _clean(text[role.start():role.end()] + " " + block),
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
