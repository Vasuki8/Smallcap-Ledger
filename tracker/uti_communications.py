"""UTI Mutual Fund first-party Fund House insights collector."""
from __future__ import annotations

import json
import re
from datetime import date,datetime
from urllib.parse import urlparse

from . import db,providers

FAMILY="UTI Small Cap Fund"
LISTING="https://www.utimf.com/learn"
SOURCE_TITLE="Leadership Desk / Market Insights"
CMS_ENDPOINTS=(
    ("https://www.utimf.com/api/homepage-market-insights","Market Insights"),
    ("https://www.utimf.com/api/homepage-from-cios-desk","From the CIOs Desk"),
)
_CDN_HOST="d3ce1o48hc5oli.cloudfront.net"
_ALLOWED_CATEGORIES={"Market Insights","From the CIOs Desk"}


def _published(value):
    raw=str(value or "").strip()
    if not raw:return None
    candidates=[raw,raw[:10]]
    for candidate in candidates:
        try:
            day=date.fromisoformat(candidate)
            return day.isoformat() if day<=date.today() else None
        except ValueError:
            pass
    for fmt in (
        "%d %B %Y","%d %b %Y","%B %d, %Y","%b %d, %Y",
        "%d-%m-%Y","%d/%m/%Y","%Y-%m-%dT%H:%M:%S",
    ):
        try:
            day=datetime.strptime(raw,fmt).date()
            return day.isoformat() if day<=date.today() else None
        except ValueError:
            pass
    return None


def _pdf_url(value):
    url=str(value or "").strip()
    parsed=urlparse(url)
    return (
        parsed.scheme=="https"
        and (parsed.hostname or "").lower()==_CDN_HOST
        and parsed.path.lower().endswith(".pdf")
    )


def cms_rows(content,expected_category=None):
    try:
        payload=json.loads(content.decode("utf-8","replace") if isinstance(content,(bytes,bytearray)) else content)
    except (TypeError,ValueError) as exc:
        raise ValueError("UTI communication CMS returned invalid JSON") from exc
    if isinstance(payload,dict):
        payload=payload.get("rows") or payload.get("data")
    if not isinstance(payload,list):
        raise ValueError("UTI communication CMS returned no row list")

    rows=[];seen=set()
    for item in payload:
        if not isinstance(item,dict):continue
        category=str(item.get("field_knowledge_hub_category") or item.get("category") or "").strip()
        if category not in _ALLOWED_CATEGORIES:continue
        if expected_category and category!=expected_category:continue
        title=re.sub(r"\s+"," ",str(item.get("title") or "").strip())
        target=str(item.get("pdf") or item.get("s3pdf") or "").strip()
        if not title or not _pdf_url(target):continue
        published=None
        for key in ("field_date_of_publication","field_kc_posted_date","field_review_date_and_time"):
            published=_published(item.get(key))
            if published:break
        key=(target,title,category)
        if key in seen:continue
        seen.add(key)
        rows.append({
            "title":title,
            "url":target,
            "published_at":published,
            "category":category,
            "nid":str(item.get("nid") or "").strip() or None,
            "view_node":str(item.get("view_node") or "").strip() or None,
        })
    if not rows:
        raise ValueError("UTI communication CMS exposed no eligible Fund House PDF rows")
    return rows


def _archive_pdf(url,body,media_type):
    if not body.startswith(b"%PDF"):
        raise ValueError("UTI Fund House communication returned non-PDF content")
    digest=db.archive(body,media_type)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",
            (url,db.now(),"ok",digest),
        )
    return digest


def ingest(fetch_fn=providers.fetch):
    accepted=[];errors=[]
    for endpoint,category in CMS_ENDPOINTS:
        try:
            providers.can_crawl(endpoint)
            body,_,typ=fetch_fn(
                endpoint,archive=False,max_bytes=2*1024*1024,
                headers={"Accept":"application/json"},
            )
            if "json" not in str(typ).lower():
                raise ValueError("UTI communication CMS returned non-JSON content")
            rows=cms_rows(body,expected_category=category)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
            continue
        for row in rows[:10]:
            try:
                providers.can_crawl(row["url"])
                pdf,_,pdf_type=fetch_fn(row["url"],archive=False,max_bytes=12*1024*1024)
                digest=_archive_pdf(row["url"],pdf,pdf_type)
                did=providers.save_document(
                    FAMILY,row["title"],row["url"],"market view","AMC",
                    published=row["published_at"],origin="AMC",
                )
                providers.doc_version(did,digest)
                accepted.append(row)
            except Exception as exc:
                errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    if not accepted:
        raise ValueError("UTI Fund House CMS yielded no retained communications")

    # Keep the registered source page as the human-facing discovery/source entry.
    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC",
    )
    # The source page itself is an Angular shell; the evidence is the CMS rows/PDFs,
    # so no shell hash is attached to the source document.
    return {
        "retained":len(accepted),
        "rows":accepted,
        "errors":errors,
        "source_document_id":source,
        "detail":(
            f"{len(accepted)} UTI Market Insight/CIO Desk PDF(s) retained from first-party CMS; "
            f"{len(errors)} download/parser gaps"
        ),
    }
