"""Franklin Templeton India first-party commentary metadata collector.

Franklin's public Latest Commentaries page is a JavaScript shell in the
production runner. The public frontend populates it by POSTing form data to the
same-domain /api/articleApi endpoint. This module uses that exact contract.

Widen-hosted binaries returned by the API are retained as official external
links only. The tracker does not bypass Widen's robots policy and therefore does
not attach those binary bytes as document versions.
"""
from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urlparse

from . import db,providers

FAMILY="Franklin India Small Cap Fund"
AMC="Franklin"
LISTING="https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries"
ENDPOINT="https://www.franklintempletonindia.com/api/articleApi"
SOURCE_TITLE="Latest Commentaries API snapshot"
ARTICLE_PREFIX="/content/documents/global/india/sites/india/site-pages"
ARTICLE_ROOT="/knowledge-centre/quick-learn/latest-commentaries/"
DOCUMENT_TYPES={"INDArticleDetails"}
PAGE_TYPE="latest-commentaries"

_COMMUNICATION=re.compile(
    r"(?:"
    r"weekly\s+market\s+review|"
    r"market.*(?:outlook|review|perspective)|"
    r"(?:equity|debt).*outlook|"
    r"investment.*outlook|"
    r"budget.*outlook|"
    r"monetary\s+policy\s+review|"
    r"annual\s+outlook|"
    r"quarterly\s+equity\s+outlook"
    r")",
    re.I,
)


def request_form(number=40):
    filters=json.dumps([
        {"fieldName":"documentType.exact",
         "fieldValue":["INDVideoArticles","INDArticleDetails"]},
        {"fieldName":"pageType","fieldValue":[PAGE_TYPE]},
    ],separators=(",",":"))
    return {
        "query":"*",
        "audience":"investor",
        "locale":"en-in-new",
        "filters":filters,
        "collection":"pages",
        "start":"0",
        "number":str(number),
        "loggedIn":"n",
        "articleType":"",
        "env":"prod",
    }


def request_headers():
    return {
        "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
        "Referer":LISTING,
    }


def _day(value):
    raw=str(value or "").strip()
    if not raw:return None
    raw=raw[:10]
    try:
        parsed=date.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.isoformat()>date.today().isoformat():
        return None
    return parsed.isoformat()


def _article_url(document_path):
    path=str(document_path or "").strip()
    if not path.startswith(ARTICLE_PREFIX):
        return None
    suffix=path[len(ARTICLE_PREFIX):]
    if not suffix.startswith(ARTICLE_ROOT):
        return None
    if ".." in suffix or not suffix.startswith("/"):
        return None
    return "https://www.franklintempletonindia.com"+suffix


def parse(content):
    try:
        obj=json.loads(content)
    except (TypeError,json.JSONDecodeError) as exc:
        raise ValueError("Franklin article API returned invalid JSON") from exc
    hits=(((obj.get("results") or {}).get("response") or {}).get("hits") or {}).get("hits")
    if not isinstance(hits,list):
        raise ValueError("Franklin article API response changed format")

    rows=[];seen=set()
    for hit in hits:
        src=hit.get("_source") if isinstance(hit,dict) else None
        if not isinstance(src,dict):continue
        if str(src.get("pageType") or "")!=PAGE_TYPE:continue
        if str(src.get("documentType") or "") not in DOCUMENT_TYPES:continue
        title=str(src.get("pageTitle") or src.get("title") or "").strip()
        if not title or not _COMMUNICATION.search(title):continue
        published=_day(src.get("referenceDate")) or _day(src.get("publishDate"))
        if not published:continue
        url=_article_url(src.get("documentPath"))
        if not url:continue
        asset=str(src.get("pdfURL") or "").strip() or None
        if asset:
            parsed=urlparse(asset)
            if (parsed.scheme!="https"
                or (parsed.hostname or "").lower()!="franklintempletonprod.widen.net"):
                raise ValueError("Franklin article API returned an unexpected asset host")
        key=(url,published,title)
        if key in seen:continue
        seen.add(key)
        rows.append({
            "title":title,
            "url":url,
            "published_at":published,
            "asset_url":asset,
        })
    rows.sort(key=lambda x:(x["published_at"],x["title"]),reverse=True)
    if not rows:
        raise ValueError("Franklin article API exposed no recognized market commentary")
    return rows


def ingest(fetch_fn=providers.fetch):
    """Archive the API snapshot and retain communication metadata/official links."""
    providers.can_crawl(ENDPOINT)
    content,h,typ=fetch_fn(
        ENDPOINT,
        form=request_form(),
        archive=True,
        max_bytes=8*1024*1024,
        headers=request_headers(),
    )
    rows=parse(content)

    # Preserve the exact first-party API response as source evidence.
    did=providers.save_document(
        FAMILY,SOURCE_TITLE,ENDPOINT,"source page","AMC",origin="AMC")
    providers.doc_version(did,h)

    retained=0
    for row in rows:
        providers.save_document(
            FAMILY,row["title"],row["url"],"market view","AMC",
            published=row["published_at"],origin="AMC")
        retained+=1

    return {
        "retained":retained,
        "rows":rows,
        "source_hash":h,
        "media_type":typ,
        "unarchived_originals":retained,
        "detail":(
            f"{retained} Franklin market-commentary metadata records retained "
            "from first-party article API; original Widen binaries remain "
            "link-only because automatic access is disallowed by robots policy; "
            "0 download/parser gaps"
        ),
    }
