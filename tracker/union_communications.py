"""Union Mutual Fund first-party Research Notes communication collector."""
from __future__ import annotations

import re
from datetime import date,datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import providers

FAMILY="Union Small Cap Fund"
LISTING="https://www.unionmf.com/knowledge-hub/fund-managers-desk/research-notes"
SOURCE_TITLE="Research Notes / Market Outlook"

_KEEP=re.compile(
    r"^(?:State of the Market\s*&\s*Outlook|From the CIO'?s Desk|Monetary Policy Note|MPC Note|Union Budget)",
    re.I,
)
_DATE_PATTERNS=(
    re.compile(r"\b([A-Za-z]+)\s+(20\d{2})\b"),
    re.compile(r"\b([A-Za-z]+)'?(\d{2})\b"),
)


def _published_from_title(title):
    text=str(title or "")
    m=_DATE_PATTERNS[0].search(text)
    if m:
        try:
            year=int(m.group(2));month=datetime.strptime(m.group(1),"%B").month
        except ValueError:
            try:month=datetime.strptime(m.group(1),"%b").month
            except ValueError:return None
        # Month-only source labels are not exact publication dates.
        return None
    return None


def candidates(content):
    soup=BeautifulSoup(content,"html.parser")
    rows=[];seen=set()
    for target,label in providers.candidate_links(soup,LISTING).items():
        title=re.sub(r"\s+"," ",str(label or "").strip())
        if not _KEEP.search(title):
            continue
        parsed=urlparse(target)
        if (parsed.hostname or "").lower() not in ("www.unionmf.com","unionmf.com"):
            continue
        if not parsed.path.lower().endswith(".pdf"):
            continue
        key=(target,title)
        if key in seen:continue
        seen.add(key)
        rows.append({"title":title,"url":target,"published_at":_published_from_title(title)})
    if not rows:
        raise ValueError("Union Research Notes exposed no qualifying first-party PDFs")
    return rows


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    listing,h,_=fetch_fn(LISTING,archive=True,max_bytes=12*1024*1024)
    text=" ".join(BeautifulSoup(listing,"html.parser").stripped_strings)
    if "Research Notes" not in text or "Fund Manager" not in text:
        raise ValueError("Union Research Notes page identity changed")
    sid=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(sid,h)

    rows=candidates(listing)
    retained=0;errors=[];accepted=[]
    for row in rows[:20]:
        try:
            providers.can_crawl(row["url"])
            body,ch,_=fetch_fn(row["url"],archive=True,max_bytes=15*1024*1024)
            if not body.startswith(b"%PDF"):
                raise ValueError("Union Research Note returned non-PDF content")
            did=providers.save_document(
                FAMILY,row["title"],row["url"],"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;accepted.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
    if not retained:
        raise ValueError("Union Research Notes yielded no retained communications")
    return {
        "retained":retained,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} Union Research Note market-view PDFs retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
