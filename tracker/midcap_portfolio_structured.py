"""Read-only current structured portfolio recovery for staged Mid Cap batch 2."""
from __future__ import annotations

from datetime import date,datetime
import hashlib
import io
import re
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urljoin,urlparse,unquote

from bs4 import BeautifulSoup
import openpyxl
import xlrd

from . import amfi_metrics,db,providers
from .coverage import expected_portfolio_as_of
from .portfolio_parser import parse_sheet


HDFC_FAMILY="HDFC Mid Cap Fund"
HDFC_PAGE="https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio"
DSP_FAMILY="DSP Midcap Fund"
DSP_PAGE="https://www.dspim.com/mandatory-disclosures/portfolio-disclosures"
DSP_AUGUST_FALLBACK="https://www.dspim.com/media/pages/mandatory-disclosures/portfolio-disclosures/8a6dbe504f-1789452169/dsp-monthend-portfolio-as-on-31-aug-2026.zip"

HOSTS={"www.hdfcfund.com","files.hdfcfund.com","www.dspim.com"}


def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").casefold())


def _page_candidates(body,page):
    text=body.decode("utf-8","replace")
    soup=BeautifulSoup(text,"html.parser")
    rows={}
    for url,label in providers.candidate_links(soup,page).items():
        rows[url]=re.sub(r"\s+"," ",str(label or "")).strip()
    # Some SPA pages retain download metadata in embedded JSON/data attributes.
    decoded=unquote(text.replace("\\/","/"))
    pattern=re.compile(
        r"""(?P<url>https?://[^"'<>\s]+\.(?:xlsx?|zip)(?:\?[^"'<>\s]*)?|/[^"'<>\s]+\.(?:xlsx?|zip)(?:\?[^"'<>\s]*)?)""",
        re.I,
    )
    for match in pattern.finditer(decoded):
        raw=match.group("url")
        absolute=urljoin(page,raw)
        context=re.sub(r"\s+"," ",decoded[max(0,match.start()-350):min(len(decoded),match.end()+450)]).strip()
        rows.setdefault(absolute,context[:900])
    return rows


def _expected_words(day):
    d=date.fromisoformat(day)
    return (
        d.strftime("%d %B %Y").lstrip("0"),
        d.strftime("%B %d, %Y").replace(" 0"," "),
        d.strftime("%d-%b-%Y").lstrip("0"),
    )


def _discover_hdfc(expected,fetch_fn):
    body,_,_=fetch_fn(HDFC_PAGE,archive=False,max_bytes=12*1024*1024)
    candidates=_page_candidates(body,HDFC_PAGE)
    target=_norm(HDFC_FAMILY)
    date_words=_expected_words(expected)
    matches=[]
    for url,label in candidates.items():
        combined=unquote(url+" "+label)
        if not re.search(r"\.xlsx?(?:[?#]|$)",url,re.I):continue
        if target not in _norm(combined):continue
        if not any(word.casefold() in combined.casefold() for word in date_words):continue
        matches.append(url)
    if len(set(matches))!=1:
        raise ValueError(f"HDFC monthly page did not expose exactly one current Mid Cap workbook; found {len(set(matches))}")
    return next(iter(set(matches)))


def _discover_dsp(expected,fetch_fn):
    body,_,_=fetch_fn(DSP_PAGE,archive=False,max_bytes=12*1024*1024)
    candidates=_page_candidates(body,DSP_PAGE)
    d=date.fromisoformat(expected)
    labels=(d.strftime("%B %d, %Y").replace(" 0"," "),d.strftime("%B %-d, %Y") if hasattr(d,'strftime') else "")
    matches=[]
    for url,label in candidates.items():
        combined=unquote(url+" "+label)
        if not re.search(r"\.zip(?:[?#]|$)",url,re.I):continue
        if not re.search(r"Portfolio\s+Details\s+as\s+on",combined,re.I):continue
        if expected=="2026-08-31" and re.search(r"August\s+31,\s*2026|31[-_ ]aug[-_ ]2026",combined,re.I):
            matches.append(url)
        elif any(x and x.casefold() in combined.casefold() for x in labels):
            matches.append(url)
    matches=list(dict.fromkeys(matches))
    if len(matches)==1:return matches[0]
    # Reviewed first-party fallback for the current regulatory month-end only.
    if expected=="2026-08-31":
        return DSP_AUGUST_FALLBACK
    raise ValueError(f"DSP portfolio page did not expose exactly one current month-end ZIP; found {len(matches)}")


def _sheets(content):
    if content.startswith(b"PK"):
        book=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        try:
            out=[]
            for sheet in book.worksheets:
                cells=list(sheet.iter_rows())
                out.append((
                    sheet.title,
                    [[c.value for c in row] for row in cells],
                    [[c.number_format or "" for c in row] for row in cells],
                ))
            return out
        finally:
            book.close()
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        book=xlrd.open_workbook(file_contents=content,formatting_info=True)
        try:
            return [
                (
                    sheet.name,
                    [sheet.row_values(i) for i in range(sheet.nrows)],
                    [[book.format_map[book.xf_list[sheet.cell_xf_index(i,j)].format_key].format_str
                      for j in range(sheet.ncols)] for i in range(sheet.nrows)],
                )
                for sheet in book.sheets()
            ]
        finally:
            book.release_resources()
    raise ValueError("Portfolio source is not a supported spreadsheet")


def _parse_workbook(content,family,expected):
    found=[]
    for sheet,rows,formats in _sheets(content):
        snapshot=parse_sheet(rows,formats,family)
        if not snapshot:continue
        if snapshot.get("day")!=expected:continue
        positions=snapshot.get("positions") or []
        if len(positions)<5:continue
        found.append({
            "sheet":sheet,
            "as_of":snapshot["day"],
            "positions_observed":len(positions),
            "complete":bool(snapshot.get("complete")),
            "unknown_rows":list(snapshot.get("unknown_rows") or []),
            "aum":snapshot.get("aum"),
        })
    if not found:
        raise ValueError("No exact current Mid Cap portfolio sheet passed the existing structured parser")
    found.sort(key=lambda x:(x["complete"],x["positions_observed"]),reverse=True)
    best=found[0]
    # Multiple sheets are acceptable only when the strongest result is unique.
    peers=[x for x in found if (x["complete"],x["positions_observed"])==(best["complete"],best["positions_observed"])]
    if len(peers)>1:
        raise ValueError("Multiple equally strong exact Mid Cap portfolio sheets were found")
    return best


def _inspect_hdfc(expected,fetch_fn):
    source=_discover_hdfc(expected,fetch_fn)
    if urlparse(source).hostname not in HOSTS:
        raise ValueError("HDFC portfolio file is not on an approved first-party host")
    content,_,typ=fetch_fn(source,archive=False,max_bytes=15*1024*1024)
    parsed=_parse_workbook(content,HDFC_FAMILY,expected)
    return {
        "family":HDFC_FAMILY,"amc":"HDFC Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_sha256":hashlib.sha256(content).hexdigest(),
        "source_content_type":typ,
    }


def _inspect_dsp(expected,fetch_fn):
    source=_discover_dsp(expected,fetch_fn)
    if urlparse(source).hostname not in HOSTS:
        raise ValueError("DSP portfolio file is not on an approved first-party host")
    content,_,typ=fetch_fn(source,archive=False,max_bytes=80*1024*1024)
    try:
        archive=zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("DSP current portfolio source is not a valid ZIP") from exc
    candidates=[]
    with archive:
        entries=archive.infolist()
        if len(entries)>250 or sum(x.file_size for x in entries)>150*1024*1024:
            raise ValueError("DSP portfolio ZIP exceeds safety bounds")
        for entry in entries:
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits&1:
                raise ValueError("Unsupported DSP ZIP entry")
            if path.suffix.lower() not in (".xls",".xlsx") or not 0<entry.file_size<=30*1024*1024:
                continue
            with archive.open(entry) as handle:
                workbook=handle.read()
            try:
                parsed=_parse_workbook(workbook,DSP_FAMILY,expected)
            except ValueError:
                continue
            candidates.append((entry.filename,workbook,parsed))
    if len(candidates)!=1:
        raise ValueError(f"DSP ZIP did not contain exactly one parseable Mid Cap workbook; found {len(candidates)}")
    entry,workbook,parsed=candidates[0]
    return {
        "family":DSP_FAMILY,"amc":"DSP Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "zip_entry":entry,
        "source":source,
        "source_sha256":hashlib.sha256(content).hexdigest(),
        "workbook_sha256":hashlib.sha256(workbook).hexdigest(),
        "source_content_type":typ,
    }


def collect(fetch_fn=providers.fetch,today=None):
    from .midcap_helios_portfolio import FAMILY as HELIOS_FAMILY, inspect as inspect_helios

    today=today or date.today()
    expected=expected_portfolio_as_of(today)
    staged={x["family"] for x in db.rows(
        "SELECT DISTINCT family FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    collectors=((HDFC_FAMILY,_inspect_hdfc),(DSP_FAMILY,_inspect_dsp),(HELIOS_FAMILY,inspect_helios))
    for family,collector in collectors:
        if family not in staged:
            errors.append({"family":family,"error":"staged family identity missing"})
            continue
        try:
            row=collector(expected,fetch_fn)
            row["observed_at"]=db.now()
            results.append(row)
        except Exception as exc:
            errors.append({"family":family,"error":(str(exc) or type(exc).__name__)[:400]})
    return {
        "built_at":db.now(),"staged_category":"mid-cap",
        "portfolio_expected_as_of":expected,
        "targets":len(collectors),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,
        "production_writes":0,"public_export_enabled":False,
        "notes":[
            "This audit downloads official current month-end disclosure files but performs no portfolio, holding, metric, document or fetch writes.",
            "All sources are parsed through the existing exact-family structured portfolio parser in memory.",
            "Completeness is reported exactly as the parser proves it; no balancing cash or missing rows are invented.",
        ],
    }
