"""UTI Mutual Fund first-party Fund House insights collector."""
from __future__ import annotations

import re
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

from . import db,providers
from .disclosures import explicit_publication_date

FAMILY="UTI Small Cap Fund"
LISTING="https://www.utimf.com/learn"
SOURCE_TITLE="Leadership Desk / Market Insights"

_ALLOWED_PREFIXES=(
    "/leadership-desk/",
    "/investment-insights/",
    "/market-insight/",
    "/market-insights/",
)
_CATEGORY_PATHS={
    "/leadership-desk",
    "/investment-insights",
    "/market-insight",
    "/market-insights",
}
# Reviewed current first-party anchors. Dynamic discovery from /learn and any
# category links remains primary; these anchors keep recovery useful when UTI's
# JS shell temporarily omits article links from server-rendered HTML.
_SEEDS=(
    ("https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments",
     "Seeking Opportunity in Uncrowded Market Segments"),
    ("https://www.utimf.com/leadership-desk/dont-get-swayed-distractions-markets",
     "Don't Get Swayed by Distractions in Markets"),
)


def _owned(url):
    parsed=urlparse(url)
    return ((parsed.hostname or "").lower() in ("www.utimf.com","utimf.com")
            and parsed.scheme=="https")


def _article(url):
    if not _owned(url):return False
    path=urlparse(url).path.rstrip("/")
    return any(path.startswith(prefix.rstrip("/")) and path!=prefix.rstrip("/")
               for prefix in _ALLOWED_PREFIXES)


def _category(url):
    return _owned(url) and urlparse(url).path.rstrip("/").lower() in _CATEGORY_PATHS


def _candidate_links(content,base):
    soup=BeautifulSoup(content,"html.parser")
    return providers.candidate_links(soup,base)


def discover(content,fetch_fn=providers.fetch):
    """Discover UTI Fund House insight articles without following external media."""
    found={}
    category_urls=[]
    for target,label in _candidate_links(content,LISTING).items():
        if _article(target):
            found[target]=str(label or "").strip()
        elif _category(target):
            category_urls.append(target)

    for target,label in _SEEDS:
        found.setdefault(target,label)

    for category in list(dict.fromkeys(category_urls))[:6]:
        try:
            providers.can_crawl(category)
            body,_,_=fetch_fn(category,archive=False,max_bytes=8*1024*1024)
        except Exception:
            continue
        for target,label in _candidate_links(body,category).items():
            if _article(target):
                found.setdefault(target,str(label or "").strip())

    rows=[]
    for target,label in found.items():
        parsed=urlparse(target)
        title=re.sub(r"\s+"," ",str(label or "").strip())
        if not title:
            title=parsed.path.rstrip("/").rsplit("/",1)[-1].replace("-"," ").title()
        rows.append((target,title))
    rows.sort(key=lambda x:x[0])
    if not rows:
        raise ValueError("UTI Learn page exposed no first-party Fund House insight articles")
    return rows


def parse_article(content,url,title_hint=""):
    if not _article(url):
        raise ValueError("UTI insight URL escaped reviewed first-party paths")
    soup=BeautifulSoup(content,"html.parser")
    text=" ".join(soup.stripped_strings)
    heading=soup.find("h1")
    if not heading or "UTI" not in text.upper():
        raise ValueError("UTI insight article identity could not be validated")
    title=(heading.get_text(" ",strip=True) if heading else str(title_hint or "").strip())
    title=re.sub(r"\s+"," ",title)
    if not title:
        title=urlparse(url).path.rstrip("/").rsplit("/",1)[-1].replace("-"," ").title()
    published=explicit_publication_date(content,"text/html",url)
    return {"title":title,"url":url,"published_at":published}


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    listing,h,_=fetch_fn(LISTING,archive=True,max_bytes=10*1024*1024)
    text=" ".join(BeautifulSoup(listing,"html.parser").stripped_strings)
    required=("Knowledge Centre","Leadership Desk","Market Insights")
    if not all(token.lower() in text.lower() for token in required):
        raise ValueError("UTI Learn / Fund House insight source identity changed")
    sid=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(sid,h)

    retained=0;errors=[];accepted=[]
    for target,title_hint in discover(listing,fetch_fn=fetch_fn)[:20]:
        try:
            providers.can_crawl(target)
            body,ch,typ=fetch_fn(target,archive=True,max_bytes=10*1024*1024)
            if "html" not in str(typ).lower() and not body.lstrip().startswith(b"<"):
                raise ValueError("UTI insight article returned non-HTML content")
            row=parse_article(body,target,title_hint)
            did=providers.save_document(
                FAMILY,row["title"],target,"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;accepted.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    if not retained:
        raise ValueError("UTI Fund House insight source yielded no retained communications")
    return {
        "retained":retained,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} UTI Leadership/Market Insight article(s) retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
