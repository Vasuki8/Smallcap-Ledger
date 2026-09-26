"""Groww Mutual Fund first-party Reports & Newsletter collector."""
from __future__ import annotations

import json
from datetime import date
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers

FAMILY="Groww Small Cap Fund"
AMC="Groww"
LISTING="https://www.growwmf.in/distributor/knowledge-hub/publications"
ASSET_HOST="cms-resources.growwmf.in"
SOURCE_TITLE="Reports and Newsletter"


def _day(value):
    try:
        day=date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None
    return day.isoformat() if day.isoformat()<=date.today().isoformat() else None


def parse(content):
    """Parse the structured Next.js publication payload embedded by Groww."""
    soup=BeautifulSoup(content,"html.parser")
    scripts=[]
    primary=soup.find("script",id="__NEXT_DATA__")
    if primary:scripts.append(primary)
    scripts.extend(x for x in soup.find_all("script") if x is not primary)

    obj=None
    for script in scripts:
        raw=script.string or script.get_text() or ""
        if "pageProps" not in raw or "publications" not in raw:continue
        try:
            candidate=json.loads(raw)
        except (TypeError,json.JSONDecodeError):
            continue
        if candidate.get("page")!="/distributor/knowledge-hub/publications":continue
        obj=candidate;break
    if obj is None:
        raise ValueError("Groww publications structured payload was not found")

    data=((obj.get("props") or {}).get("pageProps") or {}).get("data")
    if not isinstance(data,list):
        raise ValueError("Groww publications payload changed format")

    rows=[];seen=set()
    for item in data:
        attrs=item.get("attributes") if isinstance(item,dict) else None
        if not isinstance(attrs,dict):continue
        title=str(attrs.get("heading") or "").strip()
        report_type=str(attrs.get("report_type") or "").strip()
        day=_day(attrs.get("date"))
        file_data=(((attrs.get("file") or {}).get("data") or {}).get("attributes")
                   if isinstance(attrs.get("file"),dict) else None)
        if not title or not report_type or not day or not isinstance(file_data,dict):
            continue
        target=str(file_data.get("url") or "").strip()
        parsed=urlparse(target)
        if (parsed.scheme!="https" or (parsed.hostname or "").lower()!=ASSET_HOST
            or not parsed.path.startswith("/uploads/")
            or str(file_data.get("mime") or "").lower()!="application/pdf"
            or not parsed.path.lower().endswith(".pdf")):
            raise ValueError("Groww publication payload returned an unexpected file identity")
        key=(title,target,day)
        if key in seen:continue
        seen.add(key)
        rows.append({
            "title":title,
            "report_type":report_type,
            "published_at":day,
            "url":target,
        })
    rows.sort(key=lambda x:(x["published_at"],x["title"]),reverse=True)
    if not rows:
        raise ValueError("Groww publications page exposed no dated reports")
    return rows


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    content,h,typ=fetch_fn(LISTING,archive=True,max_bytes=8*1024*1024)
    rows=parse(content)

    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    retained=0;errors=[]
    for row in rows[:12]:
        target=row["url"]
        try:
            providers.can_crawl(target)
            body,ch,_=fetch_fn(target,archive=True,max_bytes=8*1024*1024)
            if not body.startswith(b"%PDF"):
                raise ValueError("Groww report returned non-PDF content")
            did=providers.save_document(
                FAMILY,row["title"],target,"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    gaps=len(errors)
    return {
        "retained":retained,
        "rows":rows,
        "errors":errors,
        "detail":(
            f"{retained} Groww Reports & Newsletter market-intelligence PDFs retained; "
            f"{gaps} download/parser gaps"
        ),
    }
