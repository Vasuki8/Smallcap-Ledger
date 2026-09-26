"""ICICI Prudential monthly portfolio discovery and ZIP extraction.

The AMC's downloads API publishes a canonical /downloads/ path that currently
redirects to a retired archive host. The same first-party file is served from
/www.icicipruamc.com/blob + that exact published path. Discovery therefore
reads the API contract, validates the monthly-portfolio identity, and only
rewrites the delivery prefix; it never guesses a file name.
"""
from __future__ import annotations

import calendar
import io
import json
import re
import uuid
import zipfile
from datetime import date, datetime
from pathlib import PurePosixPath
from urllib.parse import quote

FAMILY = "ICICI Prudential Small Cap Fund"
PARSER_VERSION = "icici-portfolios-2026-09-v1"

PAGE = "https://www.icicipruamc.com/news-and-media/downloads"
API_BASE = "https://apimf.icicipruamc.com"
CATEGORIES_API = API_BASE + "/nms/v1/downloads/categories?userType=Investor"
FILES_API = API_BASE + "/nms/v1/downloads/files"
FILE_BASE = "https://www.icicipruamc.com/blob"

CATEGORY_TITLE = "Other Scheme Disclosures"
CATEGORY_CODE = "OTHERS"
SUBCATEGORY_TITLE = "Monthly Portfolio Disclosures"
SUBCATEGORY_CODE = "MONTHLY_PORTFOLIO_DISCSLO_DWND"
SUBCATEGORY_INTERNAL = "monthly-portfolio-disclosures"
WORKBOOK_NAME = "ICICI Prudential Small Cap Fund.xlsx"

_TITLE = re.compile(r"^Monthly Portfolio Disclosure ([A-Za-z]+) (20\d{2})$")
_FILENAME = re.compile(r"^Monthly-Portfolio-Disclosure-([A-Za-z]+)-(20\d{2})\.zip$", re.I)


def _headers():
    return {
        "Accept": "application/json,text/plain,*/*",
        "Content-Type": "application/json",
        "Origin": "https://www.icicipruamc.com",
        "Referer": PAGE,
        "env": "api",
        "baggage": "",
        "requestAPIId": str(uuid.uuid4()),
    }


def _payload(raw, label):
    try:
        obj = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"ICICI {label} API returned invalid JSON") from exc
    data = obj.get("success", {}).get("data") if isinstance(obj, dict) else None
    if data is None or obj.get("error"):
        raise ValueError(f"ICICI {label} API response changed format")
    return data


def closed_month_ends(today=None, count=2):
    today = today or date.today()
    cursor = date(today.year, today.month, 1)
    for _ in range(count):
        year, month = (cursor.year - 1, 12) if cursor.month == 1 else (cursor.year, cursor.month - 1)
        yield date(year, month, calendar.monthrange(year, month)[1])
        cursor = date(year, month, 1)


def _category_ids(categories):
    if not isinstance(categories, list):
        raise ValueError("ICICI downloads categories response is not a list")
    parents = [
        row for row in categories
        if isinstance(row, dict)
        and row.get("isEnabled") is True
        and str((row.get("title") or {}).get("text") or "").strip() == CATEGORY_TITLE
        and str((row.get("title") or {}).get("code") or "").strip() == CATEGORY_CODE
    ]
    if len(parents) != 1:
        raise ValueError("ICICI Other Scheme Disclosures category is not uniquely identified")
    parent = parents[0]
    children = [
        row for row in (parent.get("subCategory") or [])
        if isinstance(row, dict)
        and row.get("isEnabled") is True
        and str((row.get("title") or {}).get("text") or "").strip() == SUBCATEGORY_TITLE
        and str((row.get("title") or {}).get("code") or "").strip() == SUBCATEGORY_CODE
        and str(row.get("internalName") or "").strip() == SUBCATEGORY_INTERNAL
    ]
    if len(children) != 1:
        raise ValueError("ICICI Monthly Portfolio Disclosures subcategory is not uniquely identified")
    return str(parent.get("id") or ""), str(children[0].get("id") or "")


def _month(value):
    for fmt in ("%B%Y", "%b%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            return parsed.year, parsed.month
        except ValueError:
            pass
    return None


def listing_candidates(files, parent_id, child_id, today=None):
    """Return the exact newest two closed-month ZIPs from the public file list."""
    today = today or date.today()
    wanted = list(closed_month_ends(today, 2))
    wanted_days = set(wanted)
    if not isinstance(files, list):
        raise ValueError("ICICI monthly portfolio file response is not a list")
    by_day = {}
    for row in files:
        if not isinstance(row, dict) or row.get("isEnabled") is not True:
            continue
        title = row.get("title") or {}
        title_text = str(title.get("text") or "").strip() if isinstance(title, dict) else ""
        title_code = str(title.get("code") or "").strip() if isinstance(title, dict) else ""
        match = _TITLE.fullmatch(title_text)
        if not match or (title_code and title_code != title_text):
            continue
        parsed = _month(match.group(1) + match.group(2))
        if parsed is None:
            continue
        year, month = parsed
        day = date(year, month, calendar.monthrange(year, month)[1])
        if day not in wanted_days:
            continue
        path = str(row.get("url") or "").strip()
        filename = PurePosixPath(path).name
        file_match = _FILENAME.fullmatch(filename)
        if not file_match or _month(file_match.group(1) + file_match.group(2)) != parsed:
            continue
        if (
            str(row.get("fileType") or "").strip() != "Document"
            or str(row.get("category") or "").strip() != SUBCATEGORY_CODE
            or str(row.get("categoryName") or "").strip() != SUBCATEGORY_TITLE
            or str(row.get("level1Id") or "").strip() != parent_id
            or str(row.get("level2Id") or "").strip() != child_id
            or str(row.get("userType") or "").strip() not in ("Both", "Investor")
            or not path.startswith("/downloads/Files/Monthly Portfolio Disclosures/")
            or f"/{year}/" not in path
        ):
            continue
        source = FILE_BASE + quote(path, safe="/")
        existing = by_day.setdefault(day, {})
        existing[source] = title_text

    missing = [d.isoformat() for d in wanted if d not in by_day]
    if missing:
        raise ValueError("ICICI API did not expose both closed-month portfolio ZIPs: " + ", ".join(missing))
    out = []
    for day in wanted:
        rows = by_day[day]
        if len(rows) != 1:
            raise ValueError(f"ICICI API exposed ambiguous portfolio ZIPs for {day.isoformat()}")
        source, title = next(iter(rows.items()))
        out.append((day, source, title))
    return out


def discover(read_fn, today=None):
    """Yield newest and prior closed-month first-party portfolio ZIPs."""
    categories_raw, _, _ = read_fn(
        CATEGORIES_API, archive=False, headers=_headers())
    parent_id, child_id = _category_ids(_payload(categories_raw, "downloads categories"))
    request = {
        "categoryId": child_id,
        "schemeCategory": "",
        "userType": "Investor",
        "fileType": "All",
        "page": "1",
        "size": "100",
        # The live UI endpoint currently exposes the current records without
        # a FINANCIAL_YEAR filter. Applying that stale filter hides them.
        "filter": [],
        "categoryName": CATEGORY_CODE,
    }
    files_raw, _, _ = read_fn(
        FILES_API, request, archive=False, headers=_headers())
    data = _payload(files_raw, "monthly portfolio files")
    files = data.get("files") if isinstance(data, dict) else data
    for _, source, title in listing_candidates(
            files or [], parent_id, child_id, today=today):
        yield FAMILY, source, title


def extract_zip(content, family, url, content_hash):
    """Read only the exact Small Cap workbook from ICICI's public monthly ZIP."""
    if family != FAMILY:
        return 0
    from . import disclosures

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("ICICI monthly portfolio source is not a valid ZIP") from exc
    with archive:
        entries = archive.infolist()
        if len(entries) > 200 or sum(entry.file_size for entry in entries) > 100 * 1024 * 1024:
            raise ValueError("Oversized ICICI monthly portfolio ZIP")
        matches = []
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits & 1:
                raise ValueError("Unsupported ICICI monthly portfolio ZIP entry")
            if path.name.casefold() == WORKBOOK_NAME.casefold():
                if path.suffix.lower() != ".xlsx" or not 0 < entry.file_size <= 5 * 1024 * 1024:
                    raise ValueError("ICICI Small Cap workbook has an unsupported file shape")
                matches.append(entry)
        if len(matches) != 1:
            raise ValueError("ICICI monthly ZIP does not contain exactly one Small Cap workbook")
        with archive.open(matches[0]) as handle:
            workbook = handle.read()
    if not workbook.startswith(b"PK"):
        raise ValueError("ICICI Small Cap workbook is not a valid XLSX package")
    return disclosures.spreadsheet(workbook, family, url, content_hash)
