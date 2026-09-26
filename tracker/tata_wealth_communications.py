"""First-party Tata Mutual Fund and The Wealth Company communication collectors."""
from __future__ import annotations

import re
from datetime import date,datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import providers

TATA_FAMILY="Tata Small Cap Fund"
TATA_OUTLOOK="https://info.tatamutualfund.com/combined/TATA/Equity-Marketoutlook.html"
TATA_SOURCE_TITLE="Equity Market Outlook"

WEALTH_FAMILY="The Wealth Company Small Cap Fund"
WEALTH_INSIGHTS="https://www.wealthcompanyamc.in/knowledge-center/current-insights/"
WEALTH_SOURCE_TITLE="Current Insights"

_WEALTH_TITLE=re.compile(
    r"^(Daily Wealth Recap|The NewsMaker)\s*-\s*(\d{1,2}\s+[A-Za-z]+\s+20\d{2})$",
    re.I,
)


def parse_tata(content):
    soup=BeautifulSoup(content,"html.parser")
    text=" ".join(soup.stripped_strings)
    if "MARKET OUTLOOK" not in text.upper() or "Equity market" not in text:
        raise ValueError("Tata Equity Market Outlook identity changed")
    if "Tata Mutual Fund" not in text and "tatamutualfund" not in str(soup).lower():
        # The dedicated info.tatamutualfund.com page may omit the brand from visible copy.
        # Its exact reviewed host/path is validated by ingest_tata.
        pass
    m=re.search(r"\bAs\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b",text,re.I)
    as_of=None
    if m:
        try:
            as_of=datetime.strptime(" ".join(m.groups()),"%d %B %Y").date().isoformat()
        except ValueError:
            as_of=None
    return {"title":"Equity Market Outlook","as_of":as_of,"published_at":None}


def ingest_tata(fetch_fn=providers.fetch):
    parsed=urlparse(TATA_OUTLOOK)
    if (parsed.hostname or "").lower()!="info.tatamutualfund.com":
        raise ValueError("Tata Outlook URL escaped reviewed first-party host")
    providers.can_crawl(TATA_OUTLOOK)
    body,h,_=fetch_fn(TATA_OUTLOOK,archive=True,max_bytes=10*1024*1024)
    row=parse_tata(body)
    did=providers.save_document(
        TATA_FAMILY,row["title"],TATA_OUTLOOK,"market view","AMC",
        published=None,origin="AMC")
    providers.doc_version(did,h)
    return {
        "retained":1,
        "as_of":row["as_of"],
        "detail":(
            "1 Tata Equity Market Outlook page retained"
            + (f"; source reports as on {row['as_of']}" if row["as_of"] else "")
            + "; publication day not inferred; 0 download/parser gaps"
        ),
    }


def _wealth_day(raw):
    try:
        day=datetime.strptime(str(raw).strip(),"%d %B %Y").date()
    except ValueError:
        try:day=datetime.strptime(str(raw).strip(),"%d %b %Y").date()
        except ValueError:return None
    return day.isoformat() if day<=date.today() else None


def wealth_candidates(content):
    soup=BeautifulSoup(content,"html.parser")
    links=providers.candidate_links(soup,WEALTH_INSIGHTS)
    rows=[];seen=set()
    for target,label in links.items():
        parsed=urlparse(target)
        if (parsed.hostname or "").lower() not in (
            "www.wealthcompanyamc.in","wealthcompanyamc.in"
        ):
            continue
        title=re.sub(r"\s+"," ",str(label or "").strip())
        match=_WEALTH_TITLE.fullmatch(title)
        if not match:
            # Some embedded payloads expose a generic PDF label while the report
            # title/date is in the URL or nearby metadata. Do not guess identity.
            continue
        if not parsed.path.lower().endswith(".pdf"):
            continue
        published=_wealth_day(match.group(2))
        if not published:
            continue
        key=(target,title,published)
        if key in seen:continue
        seen.add(key)
        rows.append({
            "title":title,
            "url":target,
            "published_at":published,
        })
    rows.sort(key=lambda r:(r["published_at"],r["title"]),reverse=True)
    if not rows:
        raise ValueError("The Wealth Company Current Insights exposed no eligible recap/news-maker PDFs")
    return rows


def ingest_wealth(fetch_fn=providers.fetch):
    providers.can_crawl(WEALTH_INSIGHTS)
    listing,h,_=fetch_fn(WEALTH_INSIGHTS,archive=True,max_bytes=12*1024*1024)
    text=" ".join(BeautifulSoup(listing,"html.parser").stripped_strings)
    if "Current Insights" not in text:
        raise ValueError("The Wealth Company Current Insights identity changed")
    sid=providers.save_document(
        WEALTH_FAMILY,WEALTH_SOURCE_TITLE,WEALTH_INSIGHTS,
        "source page","AMC",origin="AMC")
    providers.doc_version(sid,h)

    rows=wealth_candidates(listing)
    retained=0;errors=[];accepted=[]
    for row in rows[:20]:
        try:
            providers.can_crawl(row["url"])
            body,ch,_=fetch_fn(row["url"],archive=True,max_bytes=12*1024*1024)
            if not body.startswith(b"%PDF"):
                raise ValueError("The Wealth Company insight returned non-PDF content")
            did=providers.save_document(
                WEALTH_FAMILY,row["title"],row["url"],"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;accepted.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
    if not retained:
        raise ValueError("The Wealth Company Current Insights yielded no retained communications")
    return {
        "retained":retained,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} The Wealth Company recap/news-maker PDFs retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
