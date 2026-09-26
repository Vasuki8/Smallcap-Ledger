"""Franklin Templeton India latest-commentaries API collector.

The public Angular frontend uses a same-domain form-encoded article API. The
collector replays that published frontend contract and archives the JSON response
as source evidence. CDN document URLs returned by the API are retained as
metadata only when robots policy prevents automatic binary retrieval.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urljoin,urlparse

from . import db,providers

API="https://www.franklintempletonindia.com/api/articleApi"
LISTING="https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries"
FAMILY="Franklin India Small Cap Fund"
PARSER_VERSION="franklin-communications-2026-09-v1"

FILTERS=[
    {"fieldName":"documentType.exact","fieldValue":["INDVideoArticles","INDArticleDetails"]},
    {"fieldName":"pageType","fieldValue":["latest-commentaries"]},
]

_MARKET=re.compile(
    r"(?:market\s*(?:outlook|review|update)|"
    r"(?:equity|debt)\s*(?:market\s*)?(?:outlook|review|update)|"
    r"monthly\s+(?:equity|debt)\s+outlook|"
    r"rbi\s+monetary\s+policy\s+review)",
    re.I,
)
_LETTER=re.compile(r"letter\s+from\s+president\s+to\s+investors?",re.I)


def _form(start=0,number=40):
    return {
        "query":"*",
        "audience":"investor",
        "locale":"en-in-new",
        "filters":json.dumps(FILTERS,separators=(",",":")),
        "collection":"pages",
        "start":str(start),
        "number":str(number),
        "loggedIn":"n",
        "articleType":"",
        "env":"prod",
    }


def _day(value):
    raw=str(value or "").strip()
    if not raw:return None
    try:
        if re.match(r"^20\d{2}-\d{2}-\d{2}T",raw):
            return datetime.fromisoformat(raw.replace("Z","+00:00")).date().isoformat()
        return providers.iso(raw)
    except ValueError:
        return None


def _kind(title):
    if _LETTER.search(title or ""):return "unitholder letter"
    if _MARKET.search(title or ""):return "market view"
    return None


def _source(row):
    if not isinstance(row,dict):return {}
    value=row.get("_source")
    return value if isinstance(value,dict) else {}


def _url(source):
    pdf=str(source.get("pdfURL") or "").strip()
    if pdf.startswith(("https://","http://")):return pdf
    path=str(source.get("documentPath") or "").strip()
    if "site-pages" in path:path=path.split("site-pages",1)[1]
    if path.startswith("/"):return urljoin("https://www.franklintempletonindia.com/",path)
    return None


def parse(payload):
    """Return exact communication metadata from one archived API response."""
    try:data=json.loads(payload)
    except (TypeError,json.JSONDecodeError) as exc:
        raise ValueError("Franklin article API returned invalid JSON") from exc
    hits=(data.get("results",{}).get("response",{}).get("hits",{}).get("hits")
          if isinstance(data,dict) else None)
    if not isinstance(hits,list):
        raise ValueError("Franklin article API response changed format")
    out=[]
    seen=set()
    for hit in hits:
        source=_source(hit)
        title=str(source.get("pageTitle") or source.get("title") or "").strip()
        kind=_kind(title)
        url=_url(source)
        day=_day(source.get("referenceDate"))
        if not kind or not url or not day:continue
        parsed=urlparse(url)
        if parsed.scheme!="https" or not parsed.hostname:continue
        if (parsed.hostname or "").lower() not in (
            "www.franklintempletonindia.com","franklintempletonindia.com",
            "franklintempletonprod.widen.net",
        ):
            continue
        key=(title,url,day,kind)
        if key in seen:continue
        seen.add(key);out.append({
            "title":title,"url":url,"published_at":day,"kind":kind,
        })
    out.sort(key=lambda x:(x["published_at"],x["title"]),reverse=True)
    return out


def ingest(family=FAMILY):
    """Fetch/archive the public API response and retain communication metadata."""
    if family!=FAMILY:return []
    providers.can_crawl(API)
    raw,h,_=providers.fetch(
        API,form=_form(),archive=True,max_bytes=4*1024*1024,
        headers={
            "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
            "Referer":LISTING,
        })
    api_doc=providers.save_document(
        family,"Latest Commentaries API",API,"source page","AMC",origin="AMC")
    providers.doc_version(api_doc,h)
    rows=parse(raw)
    if not rows:
        raise ValueError("Franklin article API exposed no supported market communications")
    for row in rows:
        providers.save_document(
            family,row["title"],row["url"],row["kind"],"AMC",
            published=row["published_at"],origin="AMC")
    return rows
