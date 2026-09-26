"""PGIM India first-party domestic insight communication collector."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers
from .disclosures import explicit_publication_date

FAMILY="Pgim India Small Cap Fund"
AMC="PGIM"
LISTING="https://www.pgimindia.com/mutual-funds"
SOURCE_TITLE="CEO Letters / Outlooks & Economy"
ARTICLE_RE=re.compile(
    r"^/mutual-funds/domestic-insights/(?:CEO-Letters|Outlooks[^/]*)/article/[^/]+/?$",
    re.I,
)


def candidates(content):
    soup=BeautifulSoup(content,"html.parser")
    out=[];seen=set()
    for target,label in providers.candidate_links(soup,LISTING).items():
        parsed=urlparse(target)
        if ((parsed.hostname or "").lower()!="www.pgimindia.com"
            or not ARTICLE_RE.fullmatch(parsed.path)):
            continue
        if target in seen:continue
        seen.add(target)
        out.append((target,str(label or "").strip()))
    if not out:
        raise ValueError("PGIM India homepage exposed no domestic-insight article links")
    return out


def parse_article(content,url,title_hint=""):
    parsed=urlparse(url)
    if ((parsed.hostname or "").lower()!="www.pgimindia.com"
        or not ARTICLE_RE.fullmatch(parsed.path)):
        return None
    soup=BeautifulSoup(content,"html.parser")
    heading=soup.find("h1")
    title=(heading.get_text(" ",strip=True) if heading else str(title_hint or "").strip())
    text=" ".join(soup.stripped_strings)
    if not title or "PGIM India" not in text:
        return None
    # PGIM currently prints month/year (for example "Jun 2026 - 3 mins read")
    # but not an exact day on these insight pages. Keep published_at null unless
    # the page later exposes an exact date in supported metadata.
    published=explicit_publication_date(content,"text/html",url)
    return {"title":title,"url":url,"published_at":published}


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    listing,h,_=fetch_fn(LISTING,archive=True,max_bytes=10*1024*1024)
    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    retained=0;errors=[];rows=[]
    for target,title_hint in candidates(listing)[:12]:
        try:
            providers.can_crawl(target)
            body,ch,typ=fetch_fn(target,archive=True,max_bytes=8*1024*1024)
            row=parse_article(body,target,title_hint)
            if not row:
                raise ValueError("PGIM domestic insight article identity could not be validated")
            did=providers.save_document(
                FAMILY,row["title"],target,"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;rows.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    if not retained:
        raise ValueError("PGIM India domestic insight source yielded no retained communications")
    return {
        "retained":retained,
        "rows":rows,
        "errors":errors,
        "detail":(
            f"{retained} PGIM India CEO/outlook insight articles retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
