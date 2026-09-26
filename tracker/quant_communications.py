"""quant Mutual Fund first-party Investment Outlook collector."""
from __future__ import annotations

import re
from urllib.parse import quote,unquote,urljoin,urlparse,urlunparse

from bs4 import BeautifulSoup

from . import db,providers

FAMILY="Quant Small Cap Fund"
AMC="quant Mutual"
LISTING="https://www.quantmutual.com/downloads/investment_outlook"
SOURCE_TITLE="Investment Outlook"
PDF_PREFIX="/Admin/Pdf/"
_KEEP=re.compile(r"(?:predictive[ _-]*analytics|vlrt[ _-]*outlook|investment[ _-]*outlook)",re.I)


def canonical(url):
    parsed=urlparse(url)
    path=quote(unquote(parsed.path),safe="/._-()")
    return urlunparse((parsed.scheme,parsed.netloc,path,parsed.params,parsed.query,parsed.fragment))


def candidates(content):
    soup=BeautifulSoup(content,"html.parser")
    rows=[];seen=set()
    for anchor in soup.select("a[href]"):
        target=canonical(urljoin(LISTING,anchor.get("href","").strip()))
        parsed=urlparse(target)
        filename=unquote(parsed.path.rsplit("/",1)[-1])
        if ((parsed.hostname or "").lower() not in ("www.quantmutual.com","quantmutual.com")
            or not parsed.path.lower().startswith(PDF_PREFIX.lower())
            or not parsed.path.lower().endswith(".pdf")):
            continue
        identity=filename.rsplit(".",1)[0]
        if not _KEEP.search(identity):continue
        if re.search(r"(?:returns|explanation)",identity,re.I):continue
        parent=anchor.find_parent("tr")
        parent_text=" ".join(parent.stripped_strings) if parent else ""
        title=parent_text if _KEEP.search(parent_text) else re.sub(r"[_-]+"," ",identity)
        title=re.sub(r"\s+"," ",title).strip(" |")
        if not title or target in seen:continue
        seen.add(target);rows.append({"title":title,"url":target})
    if not rows:
        raise ValueError("quant Investment Outlook page exposed no eligible outlook PDFs")
    return rows


def ingest(fetch_fn=providers.fetch):
    providers.can_crawl(LISTING)
    listing,h,_=fetch_fn(LISTING,archive=True,max_bytes=8*1024*1024)
    source=providers.save_document(
        FAMILY,SOURCE_TITLE,LISTING,"source page","AMC",origin="AMC")
    providers.doc_version(source,h)

    retained=0;errors=[];rows=[]
    for row in candidates(listing)[:12]:
        try:
            providers.can_crawl(row["url"])
            body,ch,_=fetch_fn(row["url"],archive=True,max_bytes=20*1024*1024)
            if not body.startswith(b"%PDF"):
                raise ValueError("quant Investment Outlook returned non-PDF content")
            did=providers.save_document(
                FAMILY,row["title"],row["url"],"market view","AMC",
                published=None,origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;rows.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])

    if not retained:
        raise ValueError("quant Investment Outlook source yielded no retained outlook PDFs")
    return {
        "retained":retained,
        "rows":rows,
        "errors":errors,
        "detail":(
            f"{retained} quant Investment Outlook PDFs retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
