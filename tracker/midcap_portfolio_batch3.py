"""Read-only structured current portfolio recovery for staged Mid Cap batch 3."""
from __future__ import annotations

import calendar
import html
import io
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import axis_portfolios, db, disclosures, icici_portfolios, providers, sbi_portfolios
from .coverage import expected_portfolio_as_of
from .midcap_portfolio_structured import _parse_workbook


TARGETS=(
    "ICICI Prudential Mid Cap Fund",
    "Axis Midcap Fund",
    "SBI MIDCAP FUND",
    "Tata Mid Cap Fund",
    "UTI - Mid Cap Fund",
)

TATA_API="https://prod-dist-api.tatamfdev.com/cms-data/api/CMSDATA_portfolio?type=monthly"
UTI_API="https://www.utimf.com/api/get-consolidate-portfolio-disclosure"


def _read(fetch_fn,url,body=None,**kwargs):
    return fetch_fn(url,body=body,**kwargs)


def _month_end_label(day):
    d=date.fromisoformat(day)
    return d.year,d.month,calendar.month_name[d.month]


def _safe_zip(content,label,max_entries=250,max_total=160*1024*1024):
    try:
        archive=zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{label} source is not a valid ZIP") from exc
    entries=archive.infolist()
    if len(entries)>max_entries or sum(x.file_size for x in entries)>max_total:
        archive.close()
        raise ValueError(f"{label} ZIP exceeds safety bounds")
    for entry in entries:
        path=PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits&1:
            archive.close()
            raise ValueError(f"{label} ZIP contains an unsafe entry")
    return archive


def _scan_zip_for_family(content,family,expected,label):
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
            try:
                parsed=_parse_workbook(workbook,family,expected)
            except ValueError:
                continue
            matches.append((entry.filename,workbook,parsed))
    if not matches:
        raise ValueError(f"{label} ZIP has no exact current {family} workbook")
    matches.sort(key=lambda x:(bool(x[2].get("complete")),int(x[2].get("positions_observed") or 0)),reverse=True)
    best=matches[0]
    strength=(bool(best[2].get("complete")),int(best[2].get("positions_observed") or 0))
    peers=[x for x in matches if (bool(x[2].get("complete")),int(x[2].get("positions_observed") or 0))==strength]
    if len(peers)>1:
        raise ValueError(f"{label} ZIP has multiple equally strong exact {family} workbooks")
    return best


def _icici(expected,fetch_fn):
    def read(url,body=None,**kwargs):
        return _read(fetch_fn,url,body,**kwargs)
    candidates=list(icici_portfolios.discover(read,today=date.fromisoformat(expected)+__import__("datetime").timedelta(days=27)))
    # discover() returns newest/prior closed months. Require the expected month by title.
    month=date.fromisoformat(expected).strftime("%B %Y")
    current=[x for x in candidates if month.casefold() in str(x[2]).casefold()]
    if len(current)!=1:
        raise ValueError(f"ICICI API exposed {len(current)} candidate ZIPs for {month}")
    _,source,title=current[0]
    content,_,typ=fetch_fn(source,archive=False,max_bytes=100*1024*1024)
    entry,workbook,parsed=_scan_zip_for_family(
        content,"ICICI Prudential Mid Cap Fund",expected,"ICICI monthly portfolio")
    return {
        "family":"ICICI Prudential Mid Cap Fund","amc":"ICICI Prudential Mutual Fund",
        "status":"recovered",**parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,"zip_entry":entry,
        "source_sha256":__import__("hashlib").sha256(content).hexdigest(),
        "workbook_sha256":__import__("hashlib").sha256(workbook).hexdigest(),
        "source_content_type":typ,
    }


def _axis_source(expected,fetch_fn):
    token=axis_portfolios.cms_token(lambda url,body=None,**kwargs:_read(fetch_fn,url,body,**kwargs))
    headers={"Authorization":token}
    nested,_,_=fetch_fn(
        axis_portfolios.NESTED_ENDPOINT,
        body={"sdParentID":axis_portfolios.PARENT_ID},
        headers=headers,archive=False,max_bytes=4*1024*1024)
    axis_portfolios.validate_monthly_branch(nested)
    docs,_,_=fetch_fn(
        axis_portfolios.DOCUMENTS_ENDPOINT,
        body={"sdType":axis_portfolios.MONTHLY_TYPE,"sdID":axis_portfolios.MONTHLY_ID},
        headers=headers,archive=False,max_bytes=10*1024*1024)
    data=axis_portfolios._json(docs,"monthly scheme documents endpoint")
    schemes=[
        x for x in data.get("schemeCategories") or []
        if isinstance(x,dict)
        and " ".join(str(x.get("schemeName") or "").split()).casefold()=="axis mid cap fund"
        and str(x.get("schemeCode") or "").strip()=="MC"
    ]
    if len(schemes)!=1:
        raise ValueError("Axis Mid Cap scheme code MC is not uniquely present")
    d=date.fromisoformat(expected)
    found={}
    for item in data.get("documentList") or []:
        if not isinstance(item,dict):continue
        title=" ".join(html.unescape(str(item.get("documentName") or "")).replace("–","-").replace("—","-").split())
        compact=re.sub(r"[^a-z0-9]+","",title.casefold())
        if "axismidcapfund" not in compact or "monthlyportfolio" not in compact:
            continue
        if "large" in compact or "nifty" in compact:
            continue
        dates=[
            d.strftime("%d%B%Y").lstrip("0").casefold(),
            d.strftime("%d%b%Y").lstrip("0").casefold(),
        ]
        if not any(x in compact for x in dates):
            continue
        target=str(item.get("docuementURL") or "").strip()
        parsed=urlparse(target)
        if (parsed.scheme!="https" or (parsed.hostname or "").casefold() not in ("www.axismf.com","axismf.com")
            or not re.search(r"\.xlsx?(?:$|\?)",target,re.I)
            or item.get("redirectionUrl")):
            continue
        found[target]=title
    if len(found)!=1:
        raise ValueError(f"Axis CMS exposed {len(found)} exact current Mid Cap workbooks")
    return next(iter(found.items()))


def _axis(expected,fetch_fn):
    source,title=_axis_source(expected,fetch_fn)
    content,_,typ=fetch_fn(source,archive=False,max_bytes=20*1024*1024)
    parsed=_parse_workbook(content,"Axis Midcap Fund",expected)
    return {
        "family":"Axis Midcap Fund","amc":"Axis Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":__import__("hashlib").sha256(content).hexdigest(),
        "source_content_type":typ,
    }


def _sbi_source(expected,fetch_fn):
    d=date.fromisoformat(expected)
    payload={"FundId":0,"PSYear":str(d.year),"PSMonth":calendar.month_name[d.month],"PSFrequency":"Monthly"}
    raw,_,_=fetch_fn(sbi_portfolios.ENDPOINT,body=payload,archive=False,max_bytes=8*1024*1024)
    found={}
    for anchor in BeautifulSoup(raw,"html.parser").select("a[href]"):
        title=" ".join(anchor.get_text(" ",strip=True).split())
        target=urljoin(sbi_portfolios.ENDPOINT,anchor.get("href"))
        combined=(title+" "+target).casefold()
        if "sbi-midcap-fund-monthly-portfolio" not in target.casefold() and not re.fullmatch(
            rf"SBI\s+MIDCAP\s+FUND\s+MONTHLY\s+PORTFOLIO\s*[-–—]\s*{calendar.month_name[d.month]}\s+{d.year}",
            title,re.I):
            continue
        if any(x in combined for x in ("large-midcap","nifty-midcap","momentum","etf")):
            continue
        if not disclosures.official_publication_url(target,"SBI"):
            continue
        if not urlparse(target).path.lower().endswith((".xls",".xlsx")):
            continue
        found[target]=title or f"SBI MIDCAP FUND MONTHLY PORTFOLIO - {calendar.month_name[d.month]} {d.year}"
    if len(found)!=1:
        raise ValueError(f"SBI listing exposed {len(found)} exact current Midcap workbooks")
    return next(iter(found.items()))


def _sbi(expected,fetch_fn):
    source,title=_sbi_source(expected,fetch_fn)
    content,_,typ=fetch_fn(source,archive=False,max_bytes=20*1024*1024)
    parsed=_parse_workbook(content,"SBI MIDCAP FUND",expected)
    return {
        "family":"SBI MIDCAP FUND","amc":"SBI Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":__import__("hashlib").sha256(content).hexdigest(),
        "source_content_type":typ,
    }


def _tata(expected,fetch_fn):
    raw,_,_=fetch_fn(TATA_API,archive=False,max_bytes=8*1024*1024)
    data=json.loads(raw)
    d=date.fromisoformat(expected)
    candidates=[]
    for item in data if isinstance(data,list) else []:
        if not isinstance(item,dict):continue
        title=str(item.get("field_document_title") or "").strip()
        target=str(item.get("field_media_document") or "").strip()
        if str(item.get("field_section_flag") or "On").strip().casefold() not in ("on","1","true"):
            continue
        m=re.fullmatch(r"Portfolio\s+as\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d{2})",title,re.I)
        if not m:continue
        parsed=None
        for fmt in ("%d %B %Y","%d %b %Y"):
            try:parsed=datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",fmt).date();break
            except ValueError:pass
        if parsed!=d:continue
        if not target or not disclosures.official_publication_url(target,"Tata"):
            continue
        if not re.search(r"\.xlsx?(?:[?#]|$)",target,re.I):
            continue
        candidates.append((target,title))
    candidates=list(dict.fromkeys(candidates))
    if len(candidates)!=1:
        raise ValueError(f"Tata CMS exposed {len(candidates)} current monthly workbooks")
    source,title=candidates[0]
    content,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    parsed=_parse_workbook(content,"Tata Mid Cap Fund",expected)
    return {
        "family":"Tata Mid Cap Fund","amc":"Tata Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":__import__("hashlib").sha256(content).hexdigest(),
        "source_content_type":typ,
    }


def _uti_midcap_rows(rows,expected):
    """Parse the UTI all-scheme SEBI Exposure block for the staged Mid Cap fund."""
    target=re.sub(r"[^a-z0-9]+","", "UTI - Mid Cap Fund".casefold())
    begin=None
    published_name=None
    for i,row in enumerate(rows):
        label=str(row[0] or "").strip() if row else ""
        if not re.match(r"^SCHEME\s*:",label,re.I):
            continue
        candidate=re.sub(r"^SCHEME\s*:\s*","",label,flags=re.I).strip()
        if re.sub(r"[^a-z0-9]+","",candidate.casefold())==target:
            begin=i;published_name=candidate;break
    if begin is None:
        return None

    block=[];total=None
    for row in rows[begin+1:]:
        label=str(row[0] or "").strip() if row else ""
        normalized=re.sub(r"[^a-z0-9]+","",label.casefold())
        if normalized==re.sub(r"[^a-z0-9]+","",("TOTAL : "+published_name).casefold()):
            try:total=providers.number(row[3])
            except (ValueError,IndexError):return None
            break
        if re.match(r"^SCHEME(?:\s*:|\s+CODE)",label,re.I):
            return None
        block.append(row)
    if total is None or not 0<total/100<10_000_000:
        return None

    prefix=" ".join(str(v) for row in block[:5] for v in row if v)
    if not re.search(r"Market\s+value\s+in\s+Lacs",prefix,re.I):
        return None
    day=disclosures.report_date(prefix)
    if day!=expected:
        return None

    header=next((r for r in block[:8] if len(r)>7 and str(r[7] or "").strip().upper()=="ISIN"),None)
    if header is None or "% TO NAV" not in str(header[4] or "").upper():
        return None

    positions=[]
    for row in block:
        if len(row)<=7:continue
        isin=str(row[7] or "").strip()
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}",isin):
            continue
        try:weight=providers.number(row[4])
        except ValueError:continue
        if not 0<=weight<=100:return None
        name=re.sub(r"^EQ\s*-\s*","",str(row[0] or "").strip())
        asset="Equity" if str(row[0] or "").strip().upper().startswith("EQ -") else "Unclassified"
        positions.append({
            "isin":isin,"name":name,"sector":str(row[1] or "").strip() or None,
            "weight":weight,"asset_type":asset,
        })
    if len(positions)<5 or sum(x["weight"] for x in positions)>100.5:
        return None
    return {
        "as_of":day,
        "positions_observed":len(positions),
        "positions":positions,
        "complete":False,
        "unknown_rows":[],
        "aum":round(total/100,6),
        "published_scheme_name":published_name,
    }


def _uti(expected,fetch_fn):
    d=date.fromisoformat(expected)
    api=f"{UTI_API}?year={d.year}&month={calendar.month_name[d.month]}"
    raw,_,_=fetch_fn(api,archive=False,max_bytes=8*1024*1024)
    rows=json.loads(raw).get("rows") or []
    candidates=[
        (str(row.get("url") or "").strip(),str(row.get("name") or "").strip())
        for row in rows if isinstance(row,dict) and str(row.get("type") or "").strip().casefold()=="zip"
        and str(row.get("url") or "").strip()
    ]
    candidates=list(dict.fromkeys(candidates))
    if len(candidates)!=1:
        raise ValueError(f"UTI API exposed {len(candidates)} consolidated portfolio ZIPs for {calendar.month_name[d.month]} {d.year}")
    source,title=candidates[0]
    if urlparse(source).scheme!="https":
        raise ValueError("UTI API returned a non-HTTPS portfolio URL")
    content,_,typ=fetch_fn(source,archive=False,max_bytes=120*1024*1024)
    import openpyxl
    parsed=[]
    workbook_bytes=None
    entry_name=None
    with _safe_zip(content,"UTI consolidated portfolio",max_entries=100,max_total=120*1024*1024) as archive:
        spreadsheet_entries=[
            entry for entry in archive.infolist()
            if PurePosixPath(entry.filename).suffix.lower()==".xlsx"
            and 0<entry.file_size<=30*1024*1024
        ]
        if not spreadsheet_entries:
            raise ValueError("UTI consolidated ZIP exposed no supported XLSX workbooks")
        for entry in spreadsheet_entries:
            with archive.open(entry) as handle:
                candidate=handle.read()
            if not candidate.startswith(b"PK"):
                continue
            try:
                book=openpyxl.load_workbook(io.BytesIO(candidate),data_only=True,read_only=True)
            except Exception:
                continue
            try:
                for sheet in book.worksheets:
                    row=_uti_midcap_rows(list(sheet.values),expected)
                    if row:
                        row["sheet"]=sheet.title
                        parsed.append((entry.filename,candidate,row))
            finally:
                book.close()
    if len(parsed)!=1:
        raise ValueError(
            f"UTI consolidated ZIP exposed {len(parsed)} exact current Mid Cap blocks "
            f"across {len(spreadsheet_entries)} XLSX workbooks")
    entry_name,workbook_bytes,row=parsed[0]
    return {
        "family":"UTI - Mid Cap Fund","amc":"UTI Mutual Fund","status":"recovered",
        **row,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,"zip_entry":entry_name,
        "source_sha256":__import__("hashlib").sha256(content).hexdigest(),
        "workbook_sha256":__import__("hashlib").sha256(workbook_bytes).hexdigest(),
        "source_content_type":typ,
    }


COLLECTORS=(
    ("ICICI Prudential Mid Cap Fund",_icici),
    ("Axis Midcap Fund",_axis),
    ("SBI MIDCAP FUND",_sbi),
    ("Tata Mid Cap Fund",_tata),
    ("UTI - Mid Cap Fund",_uti),
)


def collect(fetch_fn=providers.fetch,today=None):
    today=today or date.today()
    expected=expected_portfolio_as_of(today)
    staged={x["family"] for x in db.rows(
        "SELECT DISTINCT family FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    for family,collector in COLLECTORS:
        if family not in staged:
            errors.append({"family":family,"error":"staged family identity missing"})
            continue
        try:
            row=collector(expected,fetch_fn)
            row["observed_at"]=db.now()
            results.append(row)
        except Exception as exc:
            errors.append({"family":family,"error":(str(exc) or type(exc).__name__)[:500]})
    return {
        "built_at":db.now(),"staged_category":"mid-cap",
        "portfolio_expected_as_of":expected,
        "targets":len(COLLECTORS),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,
        "production_writes":0,"public_export_enabled":False,
        "notes":[
            "This batch reuses first-party transport/schema logic only; no Small Cap holding is reused.",
            "Every result is parsed in memory through the existing exact-family structured portfolio parser and must match the current regulatory month-end.",
            "No portfolio, holding, metric, document or fetch row is written by this audit.",
        ],
    }
