"""SBI's public monthly-disclosure listing, as used by Portfolios.js.

Use the public CMS endpoint with its displayed month/year filters. Do not guess
attachment names, use investor APIs, or confuse Small Cap with passive products.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from . import disclosures

FAMILY = 'SBI Small Cap Fund'
ENDPOINT = 'https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets'
PARSER_VERSION = 'sbi-monthly-portfolio-v1'
_TITLE = re.compile(
    r'SBI\s+SMALL\s*CAP\s+FUND\s+MONTHLY\s+PORTFOLIO\s*[-\u2013\u2014]\s*'
    r'([A-Za-z]+)\s+(20\d{2})', re.I)


def closed_months(today=None):
    """Two closed calendar months, matching the rolling holdings window."""
    today = today or date.today()
    for offset in (1, 2):
        year, month = divmod(today.year * 12 + today.month - 1 - offset, 12)
        yield year, month + 1


def listing_candidates(raw, year, month):
    """Accept only an exact scheme title, requested period and official file."""
    found = {}
    for anchor in BeautifulSoup(raw, 'html.parser').select('a[href]'):
        title = ' '.join(anchor.get_text(' ', strip=True).split())
        match = _TITLE.fullmatch(title)
        if not match:
            continue
        try:
            period = datetime.strptime(' '.join(match.groups()), '%B %Y')
        except ValueError:
            continue
        if (period.year, period.month) != (year, month):
            continue
        url = urljoin(ENDPOINT, anchor['href'])
        if not disclosures.official_publication_url(url, 'SBI'):
            continue
        if not urlparse(url).path.lower().endswith(('.xls', '.xlsx')):
            continue
        found.setdefault(url, (FAMILY, url, title))
    if len(found) > 4:
        raise ValueError('Unexpectedly many SBI Small Cap monthly attachments')
    return list(found.values())


def discover(read, today=None):
    """Read two bounded CMS listings; source bytes are archived by the reader."""
    found = False
    for year, month in closed_months(today):
        payload = {'FundId': 0, 'PSYear': str(year),
                   'PSMonth': calendar.month_name[month], 'PSFrequency': 'Monthly'}
        raw, _, _ = read(ENDPOINT, body=payload)
        for candidate in listing_candidates(raw, year, month):
            found = True
            yield candidate
    if not found:
        raise ValueError('SBI official monthly listings exposed no matching Small Cap workbook')
