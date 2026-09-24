"""Bandhan Small Cap's public monthly disclosure pages and exact attachment API.

The AMC publishes one public page per scheme/month. The page exposes its post
ID, and Bandhan's read-only finance API returns the attachment metadata for
that exact post. No filename guessing or encrypted investor/dashboard API is
needed.
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup
from . import disclosures

FAMILY = 'Bandhan Small Cap Fund'
CMS_ROOT = 'https://cmsnew.bandhanmutual.com'
API = CMS_ROOT + '/wp-json/finance-api/v1/posts/disclosures'
MEDIA_HOST = 'storage.googleapis.com'
MEDIA_BUCKET = 'nonprod-static-assets-121to59kaawfgfi7bol'
PARSER_VERSION = 'bandhan-monthly-portfolio-v1'


def closed_month_ends(today=None):
    """Newest two closed month-ends, including year rollover."""
    today = today or date.today()
    cursor = date(today.year, today.month, 1)
    for _ in range(2):
        year, month = (cursor.year - 1, 12) if cursor.month == 1 else (cursor.year, cursor.month - 1)
        yield date(year, month, calendar.monthrange(year, month)[1])
        cursor = date(year, month, 1)


def page_url(day):
    return (CMS_ROOT + '/monthly-and-half-yearly-bandhan-small-cap-fund-'
            + day.strftime('%d-%B-%Y').lower() + '/')


def expected_title(day):
    return f'Monthly and Half-Yearly - Bandhan Small Cap Fund {day.day} {day.strftime("%B %Y")}'


def post_id_from_page(raw, day):
    """Require the exact public disclosure page before trusting its post id."""
    soup = BeautifulSoup(raw, 'html.parser')
    heading = soup.select_one('h1.entry-title')
    if not heading:
        return None
    title = ' '.join(heading.get_text(' ', strip=True).replace('–', '-').replace('—', '-').split())
    if title.lower() != expected_title(day).lower():
        return None
    article = soup.select_one('article[id^="post-"]')
    if article:
        match = re.fullmatch(r'post-(\d+)', str(article.get('id') or ''))
        if match:
            return int(match.group(1))
    text = raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else str(raw)
    match = re.search(r'\bpostid-(\d+)\b', text)
    return int(match.group(1)) if match else None


def attachment_from_api(raw, post_id, day):
    """Validate exact scheme/date ownership and return one official workbook."""
    data = __import__('json').loads(raw)
    rows = data.get('data') if isinstance(data, dict) else None
    if str(data.get('status')) != '200' or not isinstance(rows, list) or len(rows) != 1:
        return None
    item = rows[0]
    if not isinstance(item, dict) or int(item.get('id') or 0) != int(post_id):
        return None
    title = ' '.join(str(item.get('title') or '').replace('–', '-').replace('—', '-').split())
    if title.lower() != expected_title(day).lower():
        return None
    acf = item.get('acf_fields') or {}
    mapping = acf.get('funds_mapping') or {}
    if not disclosures.same_fund_title(mapping.get('post_title', ''), FAMILY):
        return None
    if str(acf.get('financial_year') or '') != str(day.year):
        return None
    if str(acf.get('disclosures_type') or '').strip() != 'Monthly and Half-yearly Disclosures':
        return None
    files = acf.get('disclosure_files') or []
    candidates = []
    exact_name = f'Bandhan Small Cap Fund {day.day} {day.strftime("%B %Y")}'
    for entry in files if isinstance(files, list) else []:
        if not isinstance(entry, dict):
            continue
        if ' '.join(str(entry.get('document_name') or '').split()).lower() != exact_name.lower():
            continue
        if str(entry.get('month') or '').strip().lower() != day.strftime('%B').lower():
            continue
        link = entry.get('document_link') or {}
        target = str(link.get('url') or '').strip()
        if int(link.get('uploaded_to') or 0) != int(post_id):
            continue
        if str(link.get('mime_type') or '').strip() != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            continue
        parsed = urlparse(target)
        if parsed.scheme != 'https' or parsed.hostname != MEDIA_HOST:
            continue
        if not parsed.path.startswith('/' + MEDIA_BUCKET + '/'):
            continue
        if not parsed.path.lower().endswith('.xlsx'):
            continue
        if not re.search(r'bandhan-small-cap-fund', parsed.path, re.I):
            continue
        if not disclosures.official_publication_url(target, 'Bandhan'):
            continue
        candidates.append((FAMILY, target, exact_name))
    if len(candidates) != 1:
        return None
    return candidates[0]


def discover(read, today=None):
    """Yield the latest two closed official scheme workbooks when published."""
    found = []
    for day in closed_month_ends(today):
        try:
            page = page_url(day)
            raw, _, _ = read(page)
            post_id = post_id_from_page(raw, day)
            if not post_id:
                continue
            payload, _, _ = read(API + '?' + urlencode({'id': post_id}))
            candidate = attachment_from_api(payload, post_id, day)
            if candidate:
                found.append(candidate)
        except Exception:
            continue
    if not found:
        raise ValueError('Bandhan public monthly disclosure pages exposed no matching Small Cap workbook')
    yield from found
