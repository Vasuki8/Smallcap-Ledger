"""Axis Small Cap's public statutory monthly-portfolio CMS.

Axis exposes the statutory portfolio tree through its public website. The browser
first requests a short-lived/public CMS token, then sends that raw token in the
Authorization header to the statutory CMS endpoints. We follow that same public
read-only route; no filename guessing or investor API is used.
"""
from __future__ import annotations

import calendar
import html
import json
import re
from datetime import date, datetime
from urllib.parse import unquote, urlparse

from . import disclosures

FAMILY = "Axis Small Cap Fund"
ROOT = "https://www.axismf.com"
TOKEN_ENDPOINT = ROOT + "/cms/token"
NESTED_ENDPOINT = ROOT + "/cms/get-nested-list"
DOCUMENTS_ENDPOINT = ROOT + "/cms/get-scheme-documents"
PARENT_ID = "sdPortfolios"
MONTHLY_ID = "sdMonthSchemePortfolio"
MONTHLY_TYPE = "yearMonthSchemeDocs"
SCHEME_CODE = "SC"
PARSER_VERSION = "axis-monthly-portfolio-v1"

_TITLE = re.compile(
    r"^Monthly Portfolio\s*-\s*Axis Small Cap Fund\s*-\s*"
    r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})$",
    re.I,
)


def closed_month_ends(today=None):
    """Newest two closed month-ends, matching rolling portfolio retention."""
    today = today or date.today()
    cursor = date(today.year, today.month, 1)
    for _ in range(2):
        year, month = (
            (cursor.year - 1, 12) if cursor.month == 1
            else (cursor.year, cursor.month - 1)
        )
        yield date(year, month, calendar.monthrange(year, month)[1])
        cursor = date(year, month, 1)


def _json(raw, label):
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Axis {label} returned invalid JSON") from exc
    if (
        not isinstance(data, dict)
        or str(data.get("status")) != "success"
        or int(data.get("statusCode", -1)) != 0
        or not isinstance(data.get("data"), dict)
    ):
        raise ValueError(f"Axis {label} returned an unexpected payload")
    return data["data"]


def cms_token(read):
    """Obtain Axis's public browser CMS token without archiving the token payload."""
    raw, _, _ = read(TOKEN_ENDPOINT, body={}, archive=False)
    data = _json(raw, "CMS token endpoint")
    token = str(data.get("token") or "").strip()
    if not token or len(token) > 4096:
        raise ValueError("Axis CMS token endpoint returned no usable public token")
    return token


def validate_monthly_branch(raw):
    """Require one exact Monthly Scheme Portfolios child under Portfolios."""
    data = _json(raw, "portfolio nested-list endpoint")
    rows = data.get("sdNestedList")
    if not isinstance(rows, list):
        raise ValueError("Axis portfolio nested-list response changed format")
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and str(row.get("parentId") or "") == PARENT_ID
        and str(row.get("sdNestedId") or "") == MONTHLY_ID
        and str(row.get("sdNestedType") or "") == MONTHLY_TYPE
        and " ".join(str(row.get("sdNestedTitle") or "").split()).lower()
            == "monthly scheme portfolios"
        and not bool(row.get("isHavingRedirectionUrl"))
        and not row.get("redirectionUrl")
    ]
    if len(matches) != 1:
        raise ValueError("Axis statutory Portfolios tree exposed no unique monthly branch")
    return matches[0]


def document_candidates(raw, today=None):
    """Return exact Small Cap monthly workbooks for the newest two closed months."""
    today = today or date.today()
    data = _json(raw, "monthly scheme documents endpoint")

    schemes = data.get("schemeCategories")
    if not isinstance(schemes, list):
        raise ValueError("Axis monthly documents response has no scheme categories")
    matches = [
        row for row in schemes
        if isinstance(row, dict)
        and " ".join(str(row.get("schemeName") or "").split()).lower()
            == FAMILY.lower()
        and str(row.get("schemeCode") or "").strip() == SCHEME_CODE
    ]
    if len(matches) != 1:
        raise ValueError("Axis monthly documents response has ambiguous Small Cap identity")

    wanted = set(closed_month_ends(today))
    years = {str(x).strip() for x in data.get("years") or []}
    months = {str(x).strip().lower() for x in data.get("months") or []}
    for day in wanted:
        if str(day.year) not in years or day.strftime("%B").lower() not in months:
            raise ValueError("Axis monthly documents response omitted a requested period")

    found = {}
    rows = data.get("documentList")
    if not isinstance(rows, list):
        raise ValueError("Axis monthly documents response has no document list")

    for item in rows:
        if not isinstance(item, dict):
            continue
        title = " ".join(
            html.unescape(str(item.get("documentName") or ""))
            .replace("–", "-").replace("—", "-").split()
        )
        match = _TITLE.fullmatch(title)
        if not match:
            continue
        try:
            day = datetime.strptime(
                f"{match.group(1)} {match.group(2)} {match.group(3)}",
                "%d %B %Y",
            ).date()
        except ValueError:
            continue
        if day not in wanted or day > today:
            continue

        posted_raw = str(item.get("documentPostedDate") or "").strip()
        try:
            posted = date.fromisoformat(posted_raw)
        except ValueError:
            continue
        if posted > today or (posted.year, posted.month) != (day.year, day.month):
            continue

        target = str(item.get("docuementURL") or "").strip()
        parsed = urlparse(target)
        decoded = unquote(parsed.path)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() not in ("www.axismf.com", "axismf.com")
            or not re.search(r"\.xlsx?(?:$)",parsed.path,re.I)
            or not re.search(
                r"Monthly[_ ]Portfolio[_ ]Axis[_ ]Small[_ ]Cap[_ ]Fund[_ ]"
                + re.escape(day.strftime("%d_%B_%Y")),
                decoded,
                re.I,
            )
            or not disclosures.official_publication_url(target, "Axis")
            or item.get("redirectionUrl")
        ):
            continue

        found.setdefault(day, set()).add((target, title))

    candidates = []
    for day in sorted(wanted, reverse=True):
        rows = found.get(day, set())
        if len(rows) > 1:
            raise ValueError(f"Axis exposed multiple exact Small Cap workbooks for {day}")
        if rows:
            target, title = next(iter(rows))
            candidates.append((day, target, title))

    if not candidates:
        raise ValueError("Axis public CMS exposed no current Small Cap monthly workbook")
    return candidates


def discover(read, today=None):
    """Follow the public statutory tree and yield exact monthly Small Cap files."""
    token = cms_token(read)
    headers = {"Authorization": token}
    nested, _, _ = read(
        NESTED_ENDPOINT,
        body={"sdParentID": PARENT_ID},
        headers=headers,
    )
    validate_monthly_branch(nested)
    docs, _, _ = read(
        DOCUMENTS_ENDPOINT,
        body={"sdType": MONTHLY_TYPE, "sdID": MONTHLY_ID},
        headers=headers,
    )
    for _, target, title in document_candidates(docs, today=today):
        yield FAMILY, target, title
