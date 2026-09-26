"""HSBC Mutual Fund India Local Market Commentary collector."""
from __future__ import annotations

import re
from datetime import date,datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers

FAMILY="HSBC Small Cap Fund"
AMC="HSBC"
LISTING=("https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights"
         "?categories=%5B%27local-market-commentary%27%5D")
HOST="www.assetmanagement.hsbc.co.in"
ARTICLE_PREFIX="/en/mutual-funds/news-and-insights/"
SOURCE_TITLE="Local Market Commentary"

_DATE=re.compile(r"\b(\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b")


def _day(value):
    raw=str(value or "").strip()
    for fmt in ("%d %B %Y","%d %b %Y"):
        try:
            parsed=datetime.strptime(raw,fmt).date()
            return parsed.isoformat() if parsed<=date.today() else None
        except ValueError:
            pass
    return None


def candidates(content):
    soup=BeautifulSoup(content,"html.parser")
    found=[]
    for target,label in providers.candidate_links(soup,LISTING).items():
        parsed=urlparse(target)
        if ((parsed.hostname or "").lower()!=HOST
            or not parsed.path.startswith(ARTICLE_PREFIX)
            or parsed.path.rstrip("/")==ARTICLE_PREFIX.rstrip("/")):
            continue
        key=(target,str(label or "").strip())
        if key not in found:found.append(key)
    if not found:
        raise ValueError("HSBC Local Market Commentary page exposed no article links")
    return found


def parse_article(content,url,title_hint=""):
    soup=BeautifulSoup(content,"html.parser")
    text=" ".join(soup.stripped_strings)
    if "Local Market Commentary" not in text:
        return None
    heading=soup.find("h1")
    title=(heading.get_text(" ",strip=True) if heading else str(title_hint or "").strip())
    if not title:return None

    # HSBC prints the article date directly beneath the in-page H1/subtitle.
    # Walk forward from that H1 (not the HTML <title>) so dates cited later in
    # the commentary body cannot be mistaken for publication dates.
    nearby=" ".join(
        str(node).strip()
        for node in heading.find_all_next(string=True,limit=40)
        if str(node).strip()
    )[:1600]
    match=_DATE.search(nearby)
    day=_day(match.group(1)) if match else None
    if not day:
        return None
    parsed=urlparse(url)
    if ((parsed.hostname or "").lower()!=HOST
        or not parsed.path.startswith(ARTICLE_PREFIX)):
        return None
    return {"title":title,"published_at":day,"url":url}


def _archive_validated(url,body,media_type):
    h=db.archive(body,media_type)
    with db.connect() as c:
        c.execute("INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",
                  (url,db.now(),"ok",h))
    return h


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    listing,h,_=fetch_fn(LISTING,archive=True,max_bytes=8*1024*1024)
    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    retained=0;errors=[];accepted=[]
    for target,title_hint in candidates(listing)[:20]:
        try:
            providers.can_crawl(target)
            body,_,typ=fetch_fn(target,archive=False,max_bytes=8*1024*1024)
            row=parse_article(body,target,title_hint)
            if not row:continue
            ch=_archive_validated(target,body,typ)
            did=providers.save_document(
                FAMILY,row["title"],target,"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;accepted.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    gaps=len(errors)
    return {
        "retained":retained,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} HSBC Local Market Commentary articles retained; "
            f"{gaps} download/parser gaps"
        ),
    }
