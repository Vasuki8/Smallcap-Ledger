"""JM Financial's public monthly portfolio disclosure API.

The live Downloads SPA uses the public API below and decrypts its response in
the browser with the published application AES key/IV. We mirror that public
client behavior, then accept only exact JM Small Cap monthly workbooks for the
two newest closed calendar months.
"""
from __future__ import annotations

import base64
import calendar
import json
import re
import shutil
import subprocess
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlparse

from . import disclosures

FAMILY = 'Jm Small Cap Fund'
AMC = 'JM Financial'
API_BASE = 'https://jmmfapi.jmfinancialmf.com/api/'
DROP_ENDPOINT = urljoin(API_BASE, 'GetDownloadDrop')
FILES_ENDPOINT = urljoin(API_BASE, 'GetDownloadNew')
PUBLIC_BASE = 'https://www.jmfinancialmf.com/'
CATEGORY_ID = 2
MONTHLY_NAME = 'Monthly Portfolio of Schemes'

# Public constants embedded in JM's production browser bundle. These protect
# transport presentation only; they are not account credentials or secrets.
_AES_KEY = b'6fa979f20126cb08aa645a8f495f6d85'
_AES_IV = b'I8zyA4lVhMCaJ5Kg'

_TITLE = re.compile(
    r'Monthly\s+Portfolio\s*-\s*JM\s+Small\s+Cap\s+Fund\s*-\s*'
    r'([A-Za-z]+)\s+(\d{1,2}),?\s+(20\d{2})', re.I)


def closed_months(today=None):
    """The two month-ends that belong in the rolling holdings window."""
    today = today or date.today()
    for offset in (1, 2):
        year, month = divmod(today.year * 12 + today.month - 1 - offset, 12)
        month += 1
        yield date(year, month, calendar.monthrange(year, month)[1])


def _decrypt(raw):
    """Decode the same public AES-CBC response that JM's browser decodes."""
    try:
        outer = json.loads(raw)
        value = outer.get('data')
        if int(outer.get('statusCode', -1)) != 0 or not isinstance(value, str) or not value:
            raise ValueError('JM public API returned no decryptable data')
        ciphertext = base64.b64decode(value, validate=True)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError('JM public API returned an invalid encrypted response') from exc
    if len(ciphertext) > 8 * 1024 * 1024:
        raise ValueError('JM public API response is unexpectedly large')
    openssl = shutil.which('openssl')
    if not openssl:
        raise ValueError('OpenSSL is required to decode JM public browser API data')
    result = subprocess.run(
        [openssl, 'enc', '-d', '-aes-256-cbc',
         '-K', _AES_KEY.hex(), '-iv', _AES_IV.hex()],
        input=ciphertext, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=False)
    if result.returncode:
        raise ValueError('JM public API response could not be decoded')
    try:
        return json.loads(result.stdout.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('JM public API decrypted to invalid JSON') from exc


def _monthly_subcategory(raw):
    rows = _decrypt(raw)
    if not isinstance(rows, list):
        raise ValueError('JM portfolio category response is not a list')
    matches = {
        int(row.get('DownloadSubCategoryID'))
        for row in rows if isinstance(row, dict)
        and int(row.get('DownloadCategoryID') or -1) == CATEGORY_ID
        and str(row.get('SubCategoryName') or '').strip() == MONTHLY_NAME
        and str(row.get('DownloadSubCategoryID') or '').isdigit()
    }
    if len(matches) != 1:
        raise ValueError('JM monthly portfolio subcategory was not uniquely identified')
    return matches.pop()


def listing_candidates(raw, subcategory_id, today=None):
    """Filter the decrypted listing to exact scheme/month/host/workbook rows."""
    rows = _decrypt(raw)
    if not isinstance(rows, list):
        raise ValueError('JM monthly portfolio response is not a list')
    wanted = set(closed_months(today))
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            category = int(row.get('CategoryID'))
            subcategory = int(row.get('SubCategoryID'))
        except (TypeError, ValueError):
            continue
        if category != CATEGORY_ID or subcategory != subcategory_id:
            continue
        if str(row.get('SubCategoryName') or '').strip() != MONTHLY_NAME:
            continue
        title = ' '.join(str(row.get('Title') or '').split())
        match = _TITLE.fullmatch(title)
        if not match:
            continue
        try:
            day = datetime.strptime(
                f'{match.group(1)} {match.group(2)} {match.group(3)}',
                '%B %d %Y').date()
        except ValueError:
            try:
                day = datetime.strptime(
                    f'{match.group(1)} {match.group(2)} {match.group(3)}',
                    '%b %d %Y').date()
            except ValueError:
                continue
        if day not in wanted:
            continue
        path = str(row.get('FileName') or '').strip()
        if str(row.get('FileEXT') or '').lower() not in ('.xls', '.xlsx'):
            continue
        if not path or not urlparse(path).path.lower().endswith(('.xls', '.xlsx')):
            continue
        url = urljoin(PUBLIC_BASE, quote(path, safe='/:,()-'))
        if not disclosures.official_publication_url(url, AMC):
            continue
        existing = found.get(day)
        candidate = (FAMILY, url, title)
        if existing and existing != candidate:
            raise ValueError(f'JM exposed multiple Small Cap monthly workbooks for {day}')
        found[day] = candidate
    return [found[day] for day in sorted(wanted, reverse=True) if day in found]


def discover(read, today=None):
    """Use JM's public SPA API; fail closed if either rolling month is absent."""
    drop_raw, _, _ = read(DROP_ENDPOINT, body={'IICategoryID': str(CATEGORY_ID)})
    subcategory = _monthly_subcategory(drop_raw)
    listing_raw, _, _ = read(FILES_ENDPOINT, body={
        'IICategoryID': str(CATEGORY_ID),
        'IISubCategoryID': str(subcategory),
        'IVsearch': '',
    })
    rows = listing_candidates(listing_raw, subcategory, today=today)
    if len(rows) != 2:
        raise ValueError('JM official monthly portfolio API did not expose both closed-month Small Cap workbooks')
    yield from rows
