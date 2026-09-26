"""First-party SBI and Sundaram AMC communication collectors."""
from __future__ import annotations

import calendar
import re
from datetime import date,datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from . import providers

SBI_FAMILY="SBI Small Cap Fund"
SBI_LISTING="https://www.sbimf.com/monthly-outlook-videos"
SBI_SOURCE_TITLE="Monthly Market Outlook / Annual Outlook"

SUNDARAM_FAMILY="Sundaram Small Cap Fund"
SUNDARAM_HUB="https://www.sundarammutual.com/knowledge-hub"
SUNDARAM_HOME="https://www.sundarammutual.com/"
SUNDARAM_SOURCE_TITLE="Market Outlook / Knowledge Hub"
SUNDARAM_PDF_PREFIX="https://blog.sundarammutual.com/Documents/outlook-"

_PUBLISHED=re.compile(
    r"\bPublished\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b",
    re.I,
)
_OUTLOOK_CARD=re.compile(
    r"\bOutlook\s+("
    + "|".join(calendar.month_name[1:])
    + r")\s+(20\d{2})\b",
    re.I,
)


def sbi_outlook_url(year):
    return f"https://www.sbimf.com/learn-about-mutual-funds/{int(year)}-outlook"


def sundaram_outlook_url(month,year):
    month_name=str(month).strip().lower()
    if month_name not in {m.lower() for m in calendar.month_name[1:]}:
        raise ValueError("Unknown month")
    return f"{SUNDARAM_PDF_PREFIX}{month_name}-{int(year)}.pdf"


def _published_day(text):
    match=_PUBLISHED.search(text or "")
    if not match:return None
    raw=f"{match.group(1)} {match.group(2)} {match.group(3)}"
    for fmt in ("%d %B %Y","%d %b %Y"):
        try:
            day=datetime.strptime(raw,fmt).date()
            return day.isoformat() if day<=date.today() else None
        except ValueError:
            pass
    return None


def parse_sbi_outlook(content,url):
    parsed=urlparse(url)
    match=re.fullmatch(
        r"/learn-about-mutual-funds/(20\d{2})-outlook/?",
        parsed.path,
        re.I,
    )
    if ((parsed.hostname or "").lower() not in ("www.sbimf.com","sbimf.com")
        or not match):
        raise ValueError("SBI Outlook URL escaped reviewed first-party pattern")
    year=int(match.group(1))
    soup=BeautifulSoup(content,"html.parser")
    heading=soup.find("h1")
    title=heading.get_text(" ",strip=True) if heading else ""
    text=" ".join(soup.stripped_strings)
    if title!=f"{year} Outlook":
        raise ValueError("SBI annual Outlook page identity changed")
    if "SBI Mutual Fund" not in text:
        raise ValueError("SBI annual Outlook ownership marker missing")
    if "Equity Outlook" not in text or "Fixed Income Outlook" not in text:
        raise ValueError("SBI annual Outlook market sections missing")
    published=_published_day(text)
    if not published:
        raise ValueError("SBI annual Outlook explicit publication date missing")
    return {"title":title,"url":url,"published_at":published}


def _sbi_years(today=None):
    today=today or date.today()
    return (today.year,today.year-1)


def ingest_sbi(fetch_fn=providers.fetch,today=None):
    today=today or date.today()
    providers.can_crawl(SBI_LISTING)
    listing,h,_=fetch_fn(SBI_LISTING,archive=True,max_bytes=10*1024*1024)
    listing_text=" ".join(BeautifulSoup(listing,"html.parser").stripped_strings)
    if "Monthly Outlook Videos" not in listing_text or "Monthly Market Outlook" not in listing_text:
        raise ValueError("SBI monthly-outlook source identity changed")
    source=providers.save_document(
        SBI_FAMILY,SBI_SOURCE_TITLE,SBI_LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    retained=0;missing=0;errors=[];rows=[]
    for year in _sbi_years(today):
        target=sbi_outlook_url(year)
        try:
            providers.can_crawl(target)
            body,ch,_=fetch_fn(target,archive=True,max_bytes=12*1024*1024)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code==404:
                missing+=1
                continue
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        try:
            row=parse_sbi_outlook(body,target)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        did=providers.save_document(
            SBI_FAMILY,row["title"],target,"market view","AMC",
            published=row["published_at"],origin="AMC")
        providers.doc_version(did,ch)
        retained+=1;rows.append(row)

    if not retained:
        raise ValueError("SBI annual Outlook source yielded no retained first-party communication")
    return {
        "retained":retained,
        "expected_absent":missing,
        "rows":rows,
        "errors":errors,
        "detail":(
            f"{retained} SBI annual Outlook article(s) retained; "
            f"{missing} expected year URL(s) absent; {len(errors)} download/parser gaps"
        ),
    }


def sundaram_candidates(content):
    """Use Outlook month/year labels when Sundaram visibly publishes them."""
    text=" ".join(BeautifulSoup(content,"html.parser").stripped_strings)
    rows=[];seen=set()
    for match in _OUTLOOK_CARD.finditer(text):
        month=match.group(1).title();year=int(match.group(2))
        key=(year,list(calendar.month_name).index(month))
        if key in seen:continue
        seen.add(key)
        rows.append({
            "title":f"Outlook {month} {year}",
            "url":sundaram_outlook_url(month,year),
            "published_at":None,
            "_key":key,
        })
    rows.sort(key=lambda r:r["_key"],reverse=True)
    for row in rows:row.pop("_key",None)
    return rows


def _shift_month(year,month,delta):
    value=(year*12+(month-1))+delta
    return value//12,(value%12)+1


def recent_sundaram_outlooks(today=None,months=6):
    """Recent reviewed month-pattern URLs for Sundaram's official blog PDF archive."""
    today=today or date.today()
    rows=[]
    for delta in range(0,-months,-1):
        year,month=_shift_month(today.year,today.month,delta)
        month_name=calendar.month_name[month]
        rows.append({
            "title":f"Outlook {month_name} {year}",
            "url":sundaram_outlook_url(month_name,year),
            "published_at":None,
        })
    return rows


def ingest_sundaram(fetch_fn=providers.fetch,today=None):
    providers.can_crawl(SUNDARAM_HUB)
    hub,h,_=fetch_fn(SUNDARAM_HUB,archive=True,max_bytes=10*1024*1024)
    hub_text=" ".join(BeautifulSoup(hub,"html.parser").stripped_strings)
    if "Knowledge Hub" not in hub_text or "Sundaram" not in hub_text:
        raise ValueError("Sundaram Knowledge Hub identity changed")
    source=providers.save_document(
        SUNDARAM_FAMILY,SUNDARAM_SOURCE_TITLE,SUNDARAM_HUB,
        "source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    rows=[]
    try:
        providers.can_crawl(SUNDARAM_HOME)
        home,_,_=fetch_fn(SUNDARAM_HOME,archive=False,max_bytes=10*1024*1024)
        rows=sundaram_candidates(home)
    except Exception:
        rows=[]
    if not rows:
        # Production HTML is currently a JS shell, while the first-party blog
        # continues to publish a stable /Documents/outlook-<month>-<year>.pdf
        # archive. That exact pattern was verified across multiple 2026 months.
        rows=recent_sundaram_outlooks(today=today)

    retained=0;missing=0;errors=[];accepted=[]
    for row in rows[:6]:
        target=row["url"]
        parsed=urlparse(target)
        if ((parsed.hostname or "").lower()!="blog.sundarammutual.com"
            or not re.fullmatch(r"/Documents/outlook-[a-z]+-20\d{2}\.pdf",parsed.path,re.I)):
            raise ValueError("Sundaram Outlook URL escaped reviewed first-party pattern")
        try:
            providers.can_crawl(target)
            body,ch,_=fetch_fn(target,archive=True,max_bytes=12*1024*1024)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code==404:
                missing+=1
                continue
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        if not body.startswith(b"%PDF"):
            errors.append(f"Non-PDF Sundaram Outlook response: {target}")
            continue
        did=providers.save_document(
            SUNDARAM_FAMILY,row["title"],target,"market view","AMC",
            published=None,origin="AMC")
        providers.doc_version(did,ch)
        retained+=1;accepted.append(row)

    if not retained:
        raise ValueError("Sundaram Outlook source yielded no retained first-party PDFs")
    return {
        "retained":retained,
        "expected_absent":missing,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} Sundaram recent Outlook PDFs retained; "
            f"{missing} card-linked month URL(s) absent; {len(errors)} download/parser gaps"
        ),
    }
