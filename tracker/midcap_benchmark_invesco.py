"""Read-only Invesco Mid Cap primary benchmark from a dated AMC factsheet.

The cover proves the document month. A unique scheme-detail page must prove
both the Tier-I panel and Key Facts value. Performance comparisons do not
supply either role. This does not import index series or financial records.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import re

from pypdf import PdfReader

FAMILY = 'Invesco India Mid Cap Fund'
AMC = 'Invesco Mutual Fund'
MAX_BYTES = 16 * 1024 * 1024
MAX_PAGES = 120
MAX_PAGE_TEXT = 200_000
PARSER_VERSION = 'invesco-midcap-benchmark-factsheet-v1'
ROOT = 'https://www.invescomutualfund.com/docs/default-source/factsheet/'
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')
DESCRIPTION = '(An open ended equity scheme predominantly investing in mid cap stocks)'
RISK_HEADER = 'SCHEME RISKOMETER SCHEME BENCHMARK BENCHMARK RISKOMETER'
# Bounded recognition, never a default. The complete publisher value must match.
INDEX = re.compile(
    r'(?:BSE\s+(?:150\s+Midcap|Midcap\s+150)|Nifty\s+Midcap\s+(?:100|150))'
    r'(?:\s+Index)?(?:\s+(?:TRI|PRI))?', re.I)


def _clean(value):
    return re.sub(r'\s+', ' ', value).strip()


def _clock(now=None):
    if now is not None and (not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None):
        raise ValueError('Observation clock must be timezone-aware')
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _period(now):
    return (now.date().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')


def sources(now=None):
    """Resolve the latest closed month at call time; do not freeze it at import."""
    period = _period(_clock(now))
    year, month = map(int, period.split('-'))
    return {FAMILY: f'{ROOT}invesco-mf-factsheet-{MONTHS[month-1].lower()}-{year}.pdf'}


def _one_line(lines, label):
    indices = [i for i, line in enumerate(lines) if line.casefold() == label.casefold()]
    if len(indices) != 1:
        raise ValueError(f'Missing or ambiguous Invesco {label} boundary')
    return indices[0]


def _index(value):
    value = _clean(value)
    if not INDEX.fullmatch(value):
        raise ValueError('Missing, unknown or composite Invesco primary benchmark value')
    return value


def parse_pages(pages, expected_period):
    """Parse extracted PDF pages with strict scheme/role scope; no database access."""
    if not isinstance(pages, (tuple, list)) or not 2 <= len(pages) <= MAX_PAGES:
        raise ValueError('Invalid or oversized Invesco factsheet page set')
    if any(not isinstance(p, str) or len(p) > MAX_PAGE_TEXT for p in pages):
        raise ValueError('Invalid or oversized extracted Invesco page')
    cover = [_clean(line) for line in pages[0].splitlines() if _clean(line)]
    if not cover:
        raise ValueError('Invesco factsheet cover is empty')
    match = re.fullmatch(r'Fact Sheet\s*[-–]\s*([A-Za-z]+)\s+(20\d{2})', cover[0], re.I)
    if not match or match[1].title() not in MONTHS:
        raise ValueError('Invesco cover lacks an explicit document period')
    period = f'{match[2]}-{MONTHS.index(match[1].title())+1:02d}'
    if period != expected_period or sum('fact sheet' in line.casefold() for line in cover) != 1:
        raise ValueError('Invesco factsheet document period is stale, conflicting or unexpected')

    candidates = []
    for page_number, text in enumerate(pages[1:], 2):
        lines = [_clean(line) for line in text.splitlines() if _clean(line)]
        if len(lines) >= 2 and lines[0].casefold() == FAMILY.casefold() and lines[1].casefold() == DESCRIPTION.casefold():
            candidates.append((page_number, lines))
    if len(candidates) != 1:
        raise ValueError('No unique exact Invesco Mid Cap scheme-detail page')
    page_number, lines = candidates[0]
    scheme_headings = [line for line in lines if re.fullmatch(r'Invesco India .+ Fund', line, re.I)]
    if len(scheme_headings) != 1:
        raise ValueError('Conflicting or repeated scheme headings on Invesco detail page')
    risk_start = _one_line(lines, RISK_HEADER)
    risk_end = _one_line(lines, 'Investment Objective')
    facts_start = _one_line(lines, 'Key Facts')
    facts_end = _one_line(lines, 'Asset Allocation')
    if not 1 < risk_start < risk_end < facts_start < facts_end:
        raise ValueError('Invesco primary role sections are out of order')
    panel = _clean(' '.join(lines[risk_start+1:risk_end]))
    match = re.fullmatch(r'As per AMFI Tier I\s+Benchmark i\.e\.\s+(.+)', panel, re.I)
    if not match:
        raise ValueError('Invesco scheme benchmark lacks a single complete Tier-I role')
    primary = _index(match[1])
    facts = lines[facts_start+1:facts_end]
    label = _one_line(facts, 'Benchmark Index')
    end = _one_line(facts, 'AAuM for the month of')
    if end <= label:
        raise ValueError('Invesco benchmark fact boundary is out of order')
    fact_value = _index(' '.join(facts[label+1:end]))
    if primary.casefold() != fact_value.casefold():
        raise ValueError('Invesco Tier-I panel and Benchmark Index fact conflict')
    variant = 'total_return' if primary.upper().endswith(' TRI') else (
        'price_return' if primary.upper().endswith(' PRI') else 'unspecified')
    return {
        'primary_benchmark': primary, 'reported_benchmarks': [primary],
        'additional_benchmarks': [], 'benchmark_role': 'primary', 'return_variant': variant,
        'source_heading': lines[0], 'source_page': page_number,
        'source_document_period': period, 'source_data_as_of': None,
        'benchmark_effective_as_of': None, 'benchmark_series_verified': False,
        'source_kind': 'monthly_factsheet_pdf', 'parser_version': PARSER_VERSION,
        'source_locator': 'scheme-detail page; Scheme Benchmark Tier I panel and Key Facts Benchmark Index',
        'evidence_excerpt': f'{panel} | Benchmark Index: {fact_value}',
    }


def inspect_family(family, url, *, fetch_fn=None, now=None):
    requested = _clock(now)
    if family != FAMILY or url != sources(requested)[FAMILY]:
        raise ValueError('Invesco benchmark requires the exact registered current-month source URL and family')
    if fetch_fn is None:
        from .providers import fetch
        fetch_fn = fetch
    body, _, content_type = fetch_fn(url, archive=False, max_bytes=MAX_BYTES)
    if str(content_type).split(';', 1)[0].strip().lower() != 'application/pdf':
        raise ValueError('Invesco factsheet response is not PDF')
    if not isinstance(body, bytes) or not body.startswith(b'%PDF-') or len(body) > MAX_BYTES:
        raise ValueError('Invalid or oversized Invesco PDF bytes')
    try:
        reader = PdfReader(BytesIO(body))
        if not 2 <= len(reader.pages) <= MAX_PAGES:
            raise ValueError('Invesco PDF page limit exceeded')
        pages = [page.extract_text() or '' for page in reader.pages]
    except Exception as exc:
        raise ValueError('Invesco factsheet PDF extraction failed') from exc
    parsed = parse_pages(pages, _period(requested))
    observed = _clock(now)
    if _period(observed) != _period(requested):
        raise ValueError('Invesco source month changed during collection; retry the current month')
    return {
        'family': FAMILY, 'amc': AMC, 'status': 'recovered', **parsed,
        'source': url, 'source_sha256': hashlib.sha256(body).hexdigest(),
        'source_content_type': content_type, 'observed_at': observed.isoformat(),
    }
