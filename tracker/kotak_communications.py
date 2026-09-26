"""Kotak Mutual Fund Monthly Market Update collector."""
from __future__ import annotations

import html
import json
import re
from datetime import date
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers

FAMILY="Kotak Small Cap Fund"
AMC="Kotak"
LISTING="https://www.kotakmf.com/monthly-market-update"
SOURCE_TITLE="Monthly Market Update"
DOWNLOAD_PREFIX="https://www.kotakmf.com/kotakmf/reportupload/download/Monthly/"


def _day(value):
    raw=str(value or "").strip()
    if re.match(r"^20\d{2}-\d{2}-\d{2}T",raw):
        raw=raw[:10]
    try:
        parsed=date.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.isoformat() if parsed<=date.today() else None


def _decode_state(raw):
    # Kotak SSR state uses two custom entity shorthands in addition to normal
    # HTML entities. Decode only those exact tokens, then parse JSON.
    decoded=str(raw or "").replace("&q;",'"').replace("&a;","&")
    return html.unescape(decoded)


def current_publication(content):
    """Return the exact current report identity supplied by Kotak page state."""
    soup=BeautifulSoup(content,"html.parser")
    state=None
    for script in soup.find_all("script"):
        raw=script.string or script.get_text() or ""
        if "allPdfData" not in raw or "_sfilelink" not in raw:continue
        decoded=_decode_state(raw).strip()
        start=decoded.find('{"pageData"')
        if start<0:continue
        end=decoded.rfind("}")
        if end<start:continue
        try:
            candidate=json.loads(decoded[start:end+1])
        except json.JSONDecodeError:
            continue
        data=((candidate.get("pageData") or {}).get("data") or {})
        if isinstance(data,dict) and isinstance(data.get("allPdfData"),list):
            state=data;break
    if state is None:
        raise ValueError("Kotak Monthly Market Update state was not found")

    rows=[]
    for row in state["allPdfData"]:
        if not isinstance(row,dict):continue
        if row.get("reporStatus")!=1 or str(row.get("reportName") or "")!="Monthly":
            continue
        title=str(row.get("pdfTitle") or "").strip()
        published=_day(row.get("publishedDate"))
        try:
            ident=int(row.get("id"))
            year=int(row.get("reporYear"))
            month=int(row.get("reportMonth"))
        except (TypeError,ValueError):
            continue
        if not title or not published or not (2020<=year<=date.today().year and 0<=month<=11):
            continue
        if providers.classify(title,"")!="market view":continue
        rows.append({
            "id":ident,"year":year,"month":month,
            "title":title,"published_at":published,
        })
    if not rows:
        raise ValueError("Kotak Monthly Market Update exposed no valid monthly outlook rows")
    rows.sort(key=lambda x:(x["published_at"],x["id"]),reverse=True)
    current=rows[0]

    source=str(state.get("_sfilelink") or "").strip()
    expected=DOWNLOAD_PREFIX+f'{current["id"]}/{current["year"]}/{current["month"]}'
    if source!=expected:
        raise ValueError("Kotak current download link does not match the latest published report identity")
    parsed=urlparse(source)
    if parsed.scheme!="https" or (parsed.hostname or "").lower()!="www.kotakmf.com":
        raise ValueError("Kotak current market update uses an unexpected download host")
    current["url"]=source
    return current


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    content,h,_=fetch_fn(LISTING,archive=True,max_bytes=8*1024*1024)
    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    row=current_publication(content)
    providers.can_crawl(row["url"])
    body,ch,_=fetch_fn(row["url"],archive=True,max_bytes=20*1024*1024)
    if not body.startswith(b"%PDF"):
        raise ValueError("Kotak current Monthly Market Update returned non-PDF content")
    did=providers.save_document(
        FAMILY,row["title"],row["url"],"market view","AMC",
        published=row["published_at"],origin="AMC")
    providers.doc_version(did,ch)
    return {
        "retained":1,
        "current":row,
        "detail":(
            f"1 Kotak current Monthly Market Update PDF retained; "
            f"title={row['title']}; published_at={row['published_at']}; "
            "0 download/parser gaps"
        ),
    }
