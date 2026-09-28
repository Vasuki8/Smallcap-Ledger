"""Read-only structured current portfolio recovery for staged Mid Cap batch 4."""
from __future__ import annotations

import calendar
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import db, disclosures, providers
from .coverage import expected_portfolio_as_of
from .midcap_portfolio_structured import _parse_workbook


ABSL_FAMILY="Aditya Birla Sun Life Midcap Fund"
ABSL_PAGE="https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio"
PGIM_FAMILY="PGIM India Midcap Fund"
PGIM_API="https://www.pgimindia.com/api/v1/brochure/published/disclosure"
MIRAE_FAMILY="Mirae Asset Midcap Fund"
MIRAE_API="https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData"


def _safe_zip(content,label):
    try:
        archive=zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{label} source is not a valid ZIP") from exc
    entries=archive.infolist()
    if len(entries)>250 or sum(x.file_size for x in entries)>150*1024*1024:
        archive.close();raise ValueError(f"{label} ZIP exceeds safety bounds")
    for entry in entries:
        path=PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits&1:
            archive.close();raise ValueError(f"{label} ZIP contains an unsafe entry")
    return archive


def _scan_zip(content,family,expected,label):
    matches=[]
    with _safe_zip(content,label) as archive:
        for entry in archive.infolist():
            path=PurePosixPath(entry.filename)
            if path.suffix.lower() not in (".xls",".xlsx") or not 0<entry.file_size<=30*1024*1024:
                continue
            with archive.open(entry) as handle:
                workbook=handle.read()
            if not workbook.startswith((b"PK",b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")):
                continue
            try:parsed=_parse_workbook(workbook,family,expected)
            except ValueError:continue
            matches.append((entry.filename,workbook,parsed))
    if not matches:
        raise ValueError(f"{label} ZIP contains no exact current {family} workbook")
    matches.sort(key=lambda x:(bool(x[2].get("complete")),int(x[2].get("positions_observed") or 0)),reverse=True)
    best=matches[0];strength=(bool(best[2].get("complete")),int(best[2].get("positions_observed") or 0))
    peers=[x for x in matches if (bool(x[2].get("complete")),int(x[2].get("positions_observed") or 0))==strength]
    if len(peers)>1:
        raise ValueError(f"{label} ZIP contains multiple equally strong exact {family} workbooks")
    return best


def _absl(expected,fetch_fn):
    page_body,_,_=fetch_fn(ABSL_PAGE,archive=False,max_bytes=10*1024*1024)
    soup=BeautifulSoup(page_body,"html.parser")
    item=next((li for li in soup.select("li[data-accordian-api]")
               if re.search(r"Monthly\s+Portfolio",li.get_text(" ",strip=True),re.I)),None)
    if item is None:
        raise ValueError("ABSL monthly portfolio accordion endpoint is missing")
    endpoint=urljoin(ABSL_PAGE,str(item.get("data-accordian-api") or ""))+"&month=%20&year=0"
    raw,_,_=fetch_fn(endpoint,archive=False,max_bytes=10*1024*1024)
    payload=json.loads(raw)
    if str(payload.get("ReturnCode"))!="1":
        raise ValueError("ABSL monthly portfolio API returned no successful response")
    d=date.fromisoformat(expected);rows=[]
    for row in payload.get("AccordionList") or []:
        if not isinstance(row,dict):continue
        title=str(row.get("ResourceLink") or row.get("shareTitle") or "").strip()
        target=str(row.get("pdfUrl") or "").strip()
        m=re.search(r"Monthly\s+Portfolios?\s+as\s+on\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})",title,re.I)
        if not m or not target:continue
        try:day=datetime.strptime(re.sub(r"\s+"," ",m.group(1)).strip(),"%B %d, %Y").date()
        except ValueError:continue
        if day!=d or not re.search(r"\.zip(?:[?#]|$)",target,re.I):continue
        parsed=urlparse(target)
        origin=parsed._replace(scheme="https",netloc="mutualfund.adityabirlacapital.com").geturl()
        candidates=[origin,target] if origin!=target else [target]
        rows.append((title,candidates))
    if len(rows)!=1:
        raise ValueError(f"ABSL API exposed {len(rows)} exact current monthly portfolio ZIPs")
    title,candidates=rows[0]
    errors=[]
    for source in candidates:
        try:
            if not disclosures.official_publication_url(source,"Aditya Birla"):
                continue
            content,_,typ=fetch_fn(source,archive=False,max_bytes=120*1024*1024)
            entry,workbook,parsed=_scan_zip(content,ABSL_FAMILY,expected,"ABSL monthly portfolio")
            return {
                "family":ABSL_FAMILY,"amc":"Aditya Birla Sun Life Mutual Fund","status":"recovered",
                **parsed,"scope":"structured_monthly_portfolio",
                "source":source,"source_title":title,"zip_entry":entry,
                "source_sha256":hashlib.sha256(content).hexdigest(),
                "workbook_sha256":hashlib.sha256(workbook).hexdigest(),
                "source_content_type":typ,
            }
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__)[:220])
    raise ValueError("ABSL current ZIP candidates failed: "+"; ".join(errors))


def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from _walk(child)
    elif isinstance(value,list):
        for child in value:yield from _walk(child)


def _pgim(expected,fetch_fn):
    raw,_,_=fetch_fn(
        PGIM_API,body={"headerId":2,"sectionId":"SECTION_747960037"},
        archive=False,max_bytes=12*1024*1024)
    data=json.loads(raw);d=date.fromisoformat(expected);rows=[]
    target_norm=re.sub(r"[^a-z0-9]+","",PGIM_FAMILY.casefold())
    for item in _walk(data):
        title=str(item.get("title") or "").strip()
        source=str(item.get("pdfPath") or "").strip()
        if str(item.get("disclosureSection") or "")!="SECTION_747960037" or str(item.get("disclosureTab") or "")!="12":
            continue
        if target_norm not in re.sub(r"[^a-z0-9]+","",title.casefold()):
            continue
        if not re.search(r"\.xlsx?(?:[?#]|$)",source,re.I) or not disclosures.official_publication_url(source,"PGIM"):
            continue
        try:day=datetime.strptime(str(item.get("dateMonthYear") or "").strip(),"%d %B %Y").date()
        except ValueError:continue
        if day==d:rows.append((source,title))
    rows=list(dict.fromkeys(rows))
    if len(rows)!=1:
        raise ValueError(f"PGIM API exposed {len(rows)} exact current Midcap workbooks")
    source,title=rows[0]
    content,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    parsed=_parse_workbook(content,PGIM_FAMILY,expected)
    return {
        "family":PGIM_FAMILY,"amc":"PGIM India Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":hashlib.sha256(content).hexdigest(),"source_content_type":typ,
    }


def _mirae(expected,fetch_fn):
    target_norm=re.sub(r"[^a-z0-9]+","",MIRAE_FAMILY.casefold())
    candidates=[]
    for pgno in range(1,6):
        raw,_,_=fetch_fn(
            MIRAE_API,body={"request":{"modulename":"portfolio_tab1","pgno":pgno,"pgsize":100}},
            archive=False,max_bytes=12*1024*1024)
        data=json.loads(raw);rows=data.get("Data")
        if str(data.get("ReturnCode"))!="0" or not isinstance(rows,list):
            if pgno==1:raise ValueError("Mirae portfolio API returned no usable list")
            break
        for row in rows:
            if not isinstance(row,dict):continue
            title=str(row.get("Title") or "").strip()
            if target_norm not in re.sub(r"[^a-z0-9]+","",title.casefold()):continue
            source=urljoin("https://www.miraeassetmf.co.in/",str(row.get("URL") or "").strip())
            if not source or not disclosures.official_publication_url(source,"Mirae"):continue
            if not re.search(r"\.xlsx?(?:[?#]|$)",source,re.I):continue
            explicit=disclosures.report_date(title)
            rank=int(explicit.replace("-","")) if explicit else 0
            publish=str(row.get("PublishDate") or "");pm=re.search(r"/Date\((\d{10,13})",publish)
            candidates.append((rank,int(pm.group(1)) if pm else 0,source,title))
        if candidates:break
        if not rows:break
    if not candidates:raise ValueError("Mirae API exposed no exact Midcap XLSX candidate")
    errors=[]
    for _,_,source,title in sorted(candidates,reverse=True)[:4]:
        try:
            content,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
            parsed=_parse_workbook(content,MIRAE_FAMILY,expected)
            return {
                "family":MIRAE_FAMILY,"amc":"Mirae Asset Mutual Fund","status":"recovered",
                **parsed,"scope":"structured_monthly_portfolio",
                "source":source,"source_title":title,
                "source_sha256":hashlib.sha256(content).hexdigest(),"source_content_type":typ,
            }
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__)[:180])
    raise ValueError("Mirae exact Midcap candidates did not prove the current portfolio: "+"; ".join(errors))


COLLECTORS=((ABSL_FAMILY,_absl),(PGIM_FAMILY,_pgim),(MIRAE_FAMILY,_mirae))


def collect(fetch_fn=providers.fetch,today=None):
    today=today or date.today();expected=expected_portfolio_as_of(today)
    staged={x["family"] for x in db.rows("SELECT DISTINCT family FROM category_staged_schemes WHERE category='mid-cap'")}
    results=[];errors=[]
    for family,collector in COLLECTORS:
        if family not in staged:
            errors.append({"family":family,"error":"staged family identity missing"});continue
        try:
            row=collector(expected,fetch_fn);row["observed_at"]=db.now();results.append(row)
        except Exception as exc:
            errors.append({"family":family,"error":(str(exc) or type(exc).__name__)[:500]})
    return {
        "built_at":db.now(),"staged_category":"mid-cap","portfolio_expected_as_of":expected,
        "targets":len(COLLECTORS),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,"production_writes":0,"public_export_enabled":False,
        "notes":[
            "Batch 4 reuses only proven first-party transport/schema logic and exact staged Mid Cap identity.",
            "Every source is current-month validated and parsed in memory; no live holdings or metrics are written.",
            "Completeness is whatever the existing structured parser proves; partial evidence is never promoted.",
        ],
    }
