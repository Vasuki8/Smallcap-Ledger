"""Exact Bandhan Mid Cap monthly portfolio discovery.

Bandhan publishes one public disclosure page per scheme/month. The page exposes
its post ID, and the AMC's read-only finance API returns the attachment metadata
for that exact post. This module accepts only the exact staged Mid Cap family,
the required regulatory month-end, and an official Bandhan workbook URL.
"""
from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup

from . import disclosures

FAMILY = "BANDHAN MID CAP FUND"
AMC = "Bandhan Mutual Fund"
DISPLAY_FAMILY = "Bandhan Mid cap Fund"
CMS_ROOT = "https://cmsnew.bandhanmutual.com"
API = CMS_ROOT + "/wp-json/finance-api/v1/posts/disclosures"
MEDIA_HOST = "storage.googleapis.com"
MEDIA_BUCKET = "nonprod-static-assets-121to59kaawfgfi7bol"
PARSER_VERSION = "bandhan-midcap-monthly-portfolio-v1"


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def expected_title(day: date):
    return f"Monthly and Half-yearly - {DISPLAY_FAMILY} {day.day} {day.strftime('%B %Y')}"


def page_url(day: date):
    return (
        CMS_ROOT
        + "/monthly-and-half-yearly-bandhan-mid-cap-fund-"
        + day.strftime("%d-%B-%Y").lower()
        + "/"
    )


def post_id_from_page(raw, day: date):
    soup = BeautifulSoup(raw, "html.parser")
    heading = soup.select_one("h1.entry-title") or soup.find("h1")
    if not heading:
        return None
    title = " ".join(
        heading.get_text(" ", strip=True).replace("–", "-").replace("—", "-").split()
    )
    if _norm(title) != _norm(expected_title(day)):
        return None
    article = soup.select_one('article[id^="post-"]')
    if article:
        match = re.fullmatch(r"post-(\d+)", str(article.get("id") or ""))
        if match:
            return int(match.group(1))
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    match = re.search(r"\bpostid-(\d+)\b", text)
    return int(match.group(1)) if match else None


def attachment_from_api(raw, post_id: int, day: date):
    data = json.loads(raw)
    rows = data.get("data") if isinstance(data, dict) else None
    if str(data.get("status")) != "200" or not isinstance(rows, list) or len(rows) != 1:
        return None
    item = rows[0]
    if not isinstance(item, dict) or int(item.get("id") or 0) != int(post_id):
        return None

    title = " ".join(
        str(item.get("title") or "").replace("–", "-").replace("—", "-").split()
    )
    if _norm(title) != _norm(expected_title(day)):
        return None

    acf = item.get("acf_fields") or {}
    mapping = acf.get("funds_mapping") or {}
    if not disclosures.same_fund_title(mapping.get("post_title", ""), FAMILY):
        return None
    if str(acf.get("financial_year") or "") != str(day.year):
        return None
    if (
        str(acf.get("disclosures_type") or "").strip()
        != "Monthly and Half-yearly Disclosures"
    ):
        return None

    candidates = []
    for entry in acf.get("disclosure_files") or []:
        if not isinstance(entry, dict):
            continue
        document_name = " ".join(str(entry.get("document_name") or "").split())
        if _norm(document_name) != _norm(
            f"{DISPLAY_FAMILY} {day.day} {day.strftime('%B %Y')}"
        ):
            continue
        if str(entry.get("month") or "").strip().casefold() != day.strftime("%B").casefold():
            continue
        link = entry.get("document_link") or {}
        target = str(link.get("url") or "").strip()
        if int(link.get("uploaded_to") or 0) != int(post_id):
            continue
        if (
            str(link.get("mime_type") or "").strip()
            != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            continue
        parsed = urlparse(target)
        if parsed.scheme != "https" or parsed.hostname != MEDIA_HOST:
            continue
        if not parsed.path.startswith("/" + MEDIA_BUCKET + "/"):
            continue
        if not parsed.path.casefold().endswith(".xlsx"):
            continue
        if not re.search(r"bandhan-mid-cap-fund", parsed.path, re.I):
            continue
        if not disclosures.official_publication_url(target, "Bandhan"):
            continue
        candidates.append(
            {
                "source": target,
                "source_title": document_name,
                "post_id": int(post_id),
                "page": page_url(day),
            }
        )
    if len(candidates) != 1:
        return None
    return candidates[0]


def discover_source(fetch_fn, expected: str):
    day = date.fromisoformat(expected)
    page = page_url(day)
    raw, _, content_type = fetch_fn(page, archive=False, max_bytes=4 * 1024 * 1024)
    media = str(content_type or "").split(";", 1)[0].strip().casefold()
    if media not in ("text/html", "application/xhtml+xml"):
        raise ValueError("Bandhan Mid Cap disclosure page did not return HTML")
    post_id = post_id_from_page(raw, day)
    if not post_id:
        raise ValueError("Bandhan Mid Cap disclosure page did not expose the exact post ID")

    payload, _, api_type = fetch_fn(
        API + "?" + urlencode({"id": post_id}),
        archive=False,
        max_bytes=4 * 1024 * 1024,
    )
    api_media = str(api_type or "").split(";", 1)[0].strip().casefold()
    if api_media not in ("application/json", "text/json", "text/plain"):
        raise ValueError("Bandhan Mid Cap disclosure API did not return JSON")
    candidate = attachment_from_api(payload, post_id, day)
    if not candidate:
        raise ValueError(
            "Bandhan Mid Cap disclosure API exposed no single exact current workbook"
        )
    candidate["page_content_type"] = content_type
    candidate["api_content_type"] = api_type
    return candidate
