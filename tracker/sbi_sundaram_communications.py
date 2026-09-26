"""First-party SBI and Sundaram AMC communication collectors."""
from __future__ import annotations

import calendar
import re
from datetime import date,datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from . import db,providers

SBI_FAMILY="SBI Small Cap Fund"
SBI_OUTLOOK="https://www.sbimf.com/learn-about-mutual-funds/2026-outlook"
SBI_SOURCE_TITLE="Market Outlook - SBI 2026 Outlook"

SUNDARAM_FAMILY="Sundaram Small Cap Fund"
SUNDARAM_HUB="https://www.sundarammutual.com/knowledge-hub"
SUNDARAM_SOURCE_TITLE="Market Outlook / Knowledge Hub"
SUNDARAM_PDF_PREFIX="https://blog.sundarammutual.com/Documents/outlook-"

_PUBLISHED=re.compile(
    r"\bPublished\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b",
    re.I,
)


def _sbi_date(text):
    match=_PUBLISHED.search(text or "")
    if not match:return None
    raw=f"{match.group(1)} {match.group(2)} {match.group(3)}"
    try:
        day=datetime.strptime(raw,"%d %B %Y").date()
    except ValueError:
        try:day=datetime.strptime(raw,"%d %b %Y").date()
        except ValueError:return None
    return day.isoformat() if day<=date.today() else None


def parse_sbi(content):
    soup=BeautifulSoup(content,"html.parser")
    heading=soup.find("h1")
    title=heading.get_text(" ",strip=True) if heading else ""
    text=" ".join(soup.stripped_strings)
    if title!="2026 Outlook":
        raise ValueError("SBI 2026 Outlook page identity changed")
    if "SBI Mutual Fund" not in text:
        raise ValueError("SBI 2026 Outlook ownership marker missing")
    if "Equity Outlook" not in text or "Fixed Income Outlook" not in text:
        raise ValueError("SBI 2026 Outlook market sections missing")
    published=_sbi_date(text)
    if not published:
        raise ValueError("SBI 2026 Outlook explicit publication date missing")
    return {"title":title,"published_at":published}


def ingest_sbi(fetch_fn=providers.fetch):
    providers.can_crawl(SBI_OUTLOOK)
    body,h,typ=fetch_fn(SBI_OUTLOOK,archive=True,max_bytes=8*1024*1024)
    row=parse_sbi(body)
    did=providers.save_document(
        SBI_FAMILY,row["title"],SBI_OUTLOOK,"market view","AMC",
        published=row["published_at"],origin="AMC")
    providers.doc_version(did,h)
    return {
        "retained":1,
        "published_at":row["published_at"],
        "detail":"1 SBI 2026 Outlook article retained; 0 download/parser gaps",
    }


def _shift_month(year,month,delta):
    value=(year*12+(month-1))+delta
    return value//12,(value%12)+1


def recent_sundaram_outlooks(today=None,months=4):
    """Current/recent month URLs using the four-month pattern verified in production."""
    today=today or date.today()
    start=0 if today.day>=15 else -1
    rows=[]
    for offset in range(start,start-months,-1):
        year,month=_shift_month(today.year,today.month,offset)
        month_name=calendar.month_name[month]
        rows.append({
            "title":f"Outlook {month_name} {year}",
            "url":f"{SUNDARAM_PDF_PREFIX}{month_name.lower()}-{year}.pdf",
            "month":f"{year:04d}-{month:02d}",
        })
    return rows


def ingest_sundaram(fetch_fn=providers.fetch,today=None):
    providers.can_crawl(SUNDARAM_HUB)
    hub,h,_=fetch_fn(SUNDARAM_HUB,archive=True,max_bytes=8*1024*1024)
    soup=BeautifulSoup(hub,"html.parser")
    text=" ".join(soup.stripped_strings)
    if "Knowledge Hub" not in text or "Sundaram" not in text:
        raise ValueError("Sundaram Knowledge Hub identity changed")
    sid=providers.save_document(
        SUNDARAM_FAMILY,SUNDARAM_SOURCE_TITLE,SUNDARAM_HUB,
        "source page","AMC",origin="AMC")
    providers.doc_version(sid,h)

    retained=0;missing=0;errors=[]
    for row in recent_sundaram_outlooks(today=today):
        target=row["url"]
        parsed=urlparse(target)
        if ((parsed.hostname or "").lower()!="blog.sundarammutual.com"
            or not re.fullmatch(r"/Documents/outlook-[a-z]+-20\d{2}\.pdf",parsed.path,re.I)):
            raise ValueError("Sundaram Outlook URL escaped reviewed pattern")
        try:
            providers.can_crawl(target)
            body,ch,typ=fetch_fn(target,archive=True,max_bytes=8*1024*1024)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code==404:
                missing+=1
                continue
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        if not body.startswith(b"%PDF") or "pdf" not in str(typ).lower():
            errors.append(f"Non-PDF Sundaram Outlook response: {target}")
            continue
        did=providers.save_document(
            SUNDARAM_FAMILY,row["title"],target,"market view","AMC",
            published=None,origin="AMC")
        providers.doc_version(did,ch)
        retained+=1

    return {
        "retained":retained,
        "expected_absent":missing,
        "errors":errors,
        "detail":(
            f"{retained} Sundaram recent Outlook PDFs retained; "
            f"{missing} expected month URLs absent; {len(errors)} download/parser gaps"
        ),
    }
