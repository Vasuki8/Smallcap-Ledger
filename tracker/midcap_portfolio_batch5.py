"""Read-only current portfolio recovery for staged Mid Cap batch 5."""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from . import db, disclosures, jm_portfolios, providers
from . import midcap_bandhan_portfolio as bandhan_midcap
from .coverage import expected_portfolio_as_of
from .midcap_factsheet_equities import equity_positions, validate_factsheet_context
from .midcap_kotak_evidence import KotakSourceRejected
from .midcap_factsheet_validation import (
    PARSER_VERSION as MAHINDRA_PARSER_VERSION,
    mahindra_positions as _mahindra_positions,
)
from .midcap_portfolio_structured import _parse_workbook


KOTAK_FAMILY="Kotak Mid Cap Fund"
KOTAK_URL="https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html"
KOTAK_REVIEWED_HEADINGS=(
    "KOTAK MID CAP FUND (ERSTWHILE KNOWN AS KOTAK MIDCAP FUND)",
)
JM_FAMILY="JM Mid Cap Fund"
MAHINDRA_FAMILY="Mahindra Manulife Mid Cap Fund"
MAHINDRA_URL="https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html"
INVESCO_FAMILY="Invesco India Mid Cap Fund"
INVESCO_ROOT="https://www.invescomutualfund.com"
SUNDARAM_FAMILY="Sundaram Mid Cap Fund"
SUNDARAM_CARD="https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json"
SAMCO_FAMILY="Samco Mid Cap Fund"
SAMCO_URL="https://www.samcomf.com/mutual-funds/samco-mid-cap-fund-direct-growth/midgg"
MOTILAL_FAMILY="Motilal Oswal Midcap Fund"
MOTILAL_PAGE="https://www.motilaloswalmf.com/mutual-funds/motilal-oswal-midcap-fund"
BANDHAN_FAMILY=bandhan_midcap.FAMILY


def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").casefold())


def _require_html_identity_date(body,family,expected,reviewed_heading_aliases=()):
    soup=BeautifulSoup(body,"html.parser")
    validate_factsheet_context(
        soup,family,expected,reviewed_heading_aliases=tuple(reviewed_heading_aliases)
    )
    return soup,soup.get_text("\n",strip=True)


def _reconciled_mahindra_positions(soup):
    # Keep the existing issuer/sector classifier and add structural subtotal
    # validation. A disagreement is a source/parser gap, not extra holdings.
    classified=_mahindra_positions(soup)
    reconciled=equity_positions(soup)
    signature=lambda rows: sorted((_norm(x["name"]),x["weight"]) for x in rows)
    if signature(classified)!=signature(reconciled):
        raise ValueError("Mahindra issuer and sector-table evidence disagree")
    return reconciled


def _html_result(family,amc,url,parser,fetch_fn,expected,reviewed_heading_aliases=()):
    body,_,typ=fetch_fn(url,archive=False,max_bytes=12*1024*1024)
    stage="factsheet_context"
    try:
        soup,_=_require_html_identity_date(
            body,family,expected,reviewed_heading_aliases=reviewed_heading_aliases
        )
        stage="equity_positions"
        positions=parser(soup)
        stage="minimum_positions"
        if len(positions)<5:
            raise ValueError(f"Only {len(positions)} named current holdings were visible; need at least 5")
    except ValueError as exc:
        if family==KOTAK_FAMILY:
            raise KotakSourceRejected(
                str(exc),source=url,content=body,content_type=typ,stage=stage
            ) from exc
        raise
    return {
        "family":family,"amc":amc,"status":"recovered","as_of":expected,
        "positions_observed":len(positions),"positions":positions,
        "complete":False,"scope":"factsheet_equity_only",
        "completeness_note":"Sector and equity subtotals reconcile; non-equity assets are excluded.",
        "equity_weight_sum":round(sum(x["weight"] for x in positions),8),
        "sectors_checked":len({x["sector"] for x in positions}),
        "source":url,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
    }


def _kotak_result(fetch_fn,expected):
    return _html_result(
        KOTAK_FAMILY,"Kotak Mahindra Mutual Fund",KOTAK_URL,equity_positions,fetch_fn,expected,
        reviewed_heading_aliases=KOTAK_REVIEWED_HEADINGS)


def _mahindra_result(fetch_fn,expected):
    result=_html_result(
        MAHINDRA_FAMILY,"Mahindra Manulife Mutual Fund",MAHINDRA_URL,
        _reconciled_mahindra_positions,fetch_fn,expected)
    result["parser_version"]=MAHINDRA_PARSER_VERSION
    result["validation_version"]="sector-equity-reconciliation-v1"
    return result


def _jm_source(fetch_fn,expected):
    drop,_,_=fetch_fn(
        jm_portfolios.DROP_ENDPOINT,
        body={"IICategoryID":str(jm_portfolios.CATEGORY_ID)},
        archive=False,max_bytes=8*1024*1024)
    subcategory=jm_portfolios._monthly_subcategory(drop)
    listing,_,_=fetch_fn(
        jm_portfolios.FILES_ENDPOINT,
        body={
            "IICategoryID":str(jm_portfolios.CATEGORY_ID),
            "IISubCategoryID":str(subcategory),
            "IVsearch":"",
        },
        archive=False,max_bytes=12*1024*1024)
    rows=jm_portfolios._decrypt(listing)
    if not isinstance(rows,list):
        raise ValueError("JM monthly portfolio response is not a list")
    found={}
    target=_norm(JM_FAMILY)
    for row in rows:
        if not isinstance(row,dict):continue
        try:
            category=int(row.get("CategoryID"));sub=int(row.get("SubCategoryID"))
        except (TypeError,ValueError):
            continue
        if category!=jm_portfolios.CATEGORY_ID or sub!=subcategory:continue
        if str(row.get("SubCategoryName") or "").strip()!=jm_portfolios.MONTHLY_NAME:continue
        title=" ".join(str(row.get("Title") or "").split())
        if target not in _norm(title):continue
        if "smallcap" in _norm(title) or "largeandmidcap" in _norm(title):continue
        explicit=None
        match=re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(20\d{2})\s*$",title,re.I)
        if match:
            for fmt in ("%B %d %Y","%b %d %Y"):
                try:
                    explicit=datetime.strptime(
                        f"{match.group(1)} {match.group(2)} {match.group(3)}",fmt
                    ).date().isoformat()
                    break
                except ValueError:
                    pass
        if explicit!=expected:continue
        path=str(row.get("FileName") or "").strip()
        ext=str(row.get("FileEXT") or "").strip().casefold()
        if ext not in (".xls",".xlsx") or not path:continue
        source=urljoin(jm_portfolios.PUBLIC_BASE,quote(path,safe="/:,()-"))
        if not disclosures.official_publication_url(source,jm_portfolios.AMC):continue
        found[source]=title
    if len(found)!=1:
        raise ValueError(f"JM API exposed {len(found)} exact current Mid Cap workbooks")
    return next(iter(found.items()))


def _jm_result(fetch_fn,expected):
    source,title=_jm_source(fetch_fn,expected)
    body,_,typ=fetch_fn(source,archive=False,max_bytes=25*1024*1024)
    parsed=_parse_workbook(body,JM_FAMILY,expected)
    return {
        "family":JM_FAMILY,"amc":"JM Financial Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":hashlib.sha256(body).hexdigest(),"source_content_type":typ,
    }


def _invesco_source(fetch_fn,expected):
    d=date.fromisoformat(expected)
    raw,_,_=fetch_fn(
        f"{INVESCO_ROOT}/api/CompleteMonthlyHoldings?year={d.year}&classification=equity",
        archive=False,max_bytes=8*1024*1024)
    rows=json.loads(raw)
    if not isinstance(rows,list):
        raise ValueError("Invesco complete-monthly-holdings API returned an unexpected payload")
    matches=[
        row for row in rows if isinstance(row,dict)
        and _norm(row.get("Name"))==_norm(INVESCO_FAMILY)
    ]
    if len(matches)!=1:
        raise ValueError(f"Invesco API exposed {len(matches)} exact Mid Cap scheme rows")
    row=matches[0]
    prefix=calendar.month_abbr[d.month]
    source=str(row.get(prefix+"Url") or "").strip()
    label=str(row.get(prefix+"Name") or "").strip()
    if label and label!=f"{d.month:02d}/{d.year%100:02d}":
        raise ValueError("Invesco current month label changed")
    if not source or not disclosures.official_publication_url(source,"Invesco"):
        raise ValueError("Invesco current Mid Cap workbook is not an approved first-party URL")
    if not re.search(r"\.xlsx?(?:[?#]|$)",source,re.I):
        raise ValueError("Invesco current Mid Cap source is not a workbook")
    return source,f"Complete monthly holdings {label or d.strftime('%m/%y')}"


def _invesco_result(fetch_fn,expected):
    source,title=_invesco_source(fetch_fn,expected)
    body,_,typ=fetch_fn(source,archive=False,max_bytes=25*1024*1024)
    parsed=_parse_workbook(body,INVESCO_FAMILY,expected)
    return {
        "family":INVESCO_FAMILY,"amc":"Invesco Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":title,
        "source_sha256":hashlib.sha256(body).hexdigest(),"source_content_type":typ,
    }


def _motilal_source(fetch_fn,expected):
    body,_,typ=fetch_fn(MOTILAL_PAGE,archive=False,max_bytes=15*1024*1024)
    media=str(typ or "").split(";",1)[0].strip().casefold()
    if media not in ("text/html","application/xhtml+xml"):
        raise ValueError("Motilal portfolio discovery source did not return HTML")
    html=body.decode("utf-8","replace")
    soup=BeautifulSoup(html,"html.parser")
    text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
    if _norm(MOTILAL_FAMILY) not in _norm(text):
        raise ValueError("Motilal source lacks the exact staged Mid Cap family identity")
    d=date.fromisoformat(expected)
    expected_labels={
        expected,
        d.strftime("%d %b %Y"),
        d.strftime("%d %B %Y"),
        d.strftime("%d-%b-%Y"),
        d.strftime("%B %d, %Y").replace(" 0"," "),
    }
    if not any(label.casefold() in text.casefold() or label.casefold() in html.casefold()
               for label in expected_labels):
        raise ValueError(f"Motilal page does not prove current portfolio date {expected}")
    decoded=html.replace("\\/","/")
    patterns=(
        r"portfolioUrl\s*[:=]?\s*[\"']?([^\"'<>\s]+\.xlsx(?:\?[^\"'<>\s]*)?)",
        r"(\/content\/dam\/motilal-mf\/sheets\/fund-csvs\/Month_End_Portfolio_[^\"'<>\s]+\.xlsx)",
    )
    candidates=[]
    for pattern in patterns:
        for match in re.finditer(pattern,decoded,re.I):
            raw=match.group(1).strip()
            source=urljoin(MOTILAL_PAGE,raw)
            parsed=urlparse(source)
            if (parsed.scheme=="https"
                    and parsed.hostname=="www.motilaloswalmf.com"
                    and re.search(r"/content/dam/motilal-mf/sheets/fund-csvs/Month_End_Portfolio_",parsed.path,re.I)
                    and parsed.path.casefold().endswith(".xlsx")):
                candidates.append(source)
    candidates=list(dict.fromkeys(candidates))
    if len(candidates)!=1:
        raise ValueError(f"Motilal page exposed {len(candidates)} exact monthly portfolio workbooks")
    return candidates[0],hashlib.sha256(body).hexdigest(),typ


def _motilal_result(fetch_fn,expected):
    source,discovery_sha,discovery_type=_motilal_source(fetch_fn,expected)
    body,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    parsed=_parse_workbook(body,MOTILAL_FAMILY,expected)
    return {
        "family":MOTILAL_FAMILY,"amc":"Motilal Oswal Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,"discovery_source":MOTILAL_PAGE,
        "discovery_source_sha256":discovery_sha,"discovery_source_content_type":discovery_type,
    }


def _bandhan_result(fetch_fn,expected):
    candidate=bandhan_midcap.discover_source(fetch_fn,expected)
    source=candidate["source"]
    body,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    parsed=_parse_workbook(body,BANDHAN_FAMILY,expected)
    return {
        "family":BANDHAN_FAMILY,"amc":bandhan_midcap.AMC,"status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_title":candidate["source_title"],
        "source_sha256":hashlib.sha256(body).hexdigest(),"source_content_type":typ,
        "discovery_page":candidate["page"],"disclosure_post_id":candidate["post_id"],
        "parser_version":bandhan_midcap.PARSER_VERSION,
    }


def _samco_result(fetch_fn,expected):
    body,_,typ=fetch_fn(SAMCO_URL,archive=False,max_bytes=12*1024*1024)
    media=str(typ or "").split(";",1)[0].strip().casefold()
    if media not in ("text/html","application/xhtml+xml"):
        raise ValueError("Samco portfolio source did not return HTML")
    soup=BeautifulSoup(body,"html.parser")
    text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
    if _norm(SAMCO_FAMILY) not in _norm(text):
        raise ValueError("Samco source lacks the exact staged Mid Cap family identity")
    d=date.fromisoformat(expected)
    date_variants={
        expected,
        d.strftime("%d-%m-%Y"),
        d.strftime("%d/%m/%Y"),
        d.strftime("%d %B %Y"),
        d.strftime("%B %d, %Y").replace(" 0"," "),
    }
    if "allholdings" not in _norm(text) or not any(token.casefold() in text.casefold() for token in date_variants):
        raise ValueError(f"Samco page does not prove current all-holdings date {expected}")
    positions=[]
    for table in soup.find_all("table"):
        rows=[]
        for tr in table.find_all("tr"):
            cells=[re.sub(r"\s+"," ",x.get_text(" ",strip=True)).strip() for x in tr.find_all(["th","td"])]
            if cells:rows.append(cells)
        if not rows:continue
        header=" ".join(rows[0]).casefold()
        if "issuer" not in header or "net assets" not in header:
            continue
        for cells in rows[1:]:
            if len(cells)<2:continue
            name=cells[0].strip()
            if not name or re.search(
                r"^(?:Indian Equity and Equity Related Total|Grand Total|TREPS,?\s*Cash|Cash\s*&|"
                r"Cash and Cash Equivalents|Net Current Assets)",
                name,re.I,
            ):
                continue
            raw=next((x for x in reversed(cells[1:]) if re.fullmatch(r"-?\d+(?:\.\d+)?%?",x.replace(",","").strip())),None)
            if raw is None:continue
            weight=float(raw.replace(",","").replace("%",""))
            if not 0<weight<=20:continue
            key=_norm(name)
            if key and key not in {_norm(x["name"]) for x in positions}:
                positions.append({"name":name,"weight":round(weight,8)})
    if len(positions)<5:
        raise ValueError(f"Only {len(positions)} named Samco holdings were visible; need at least 5")
    return {
        "family":SAMCO_FAMILY,"amc":"Samco Mutual Fund","status":"recovered",
        "as_of":expected,"positions_observed":len(positions),"positions":positions,
        "complete":False,"scope":"publisher_all_holdings_html",
        "completeness_note":"Publisher labels the table All Holdings; retained as partial until structured 100% reconciliation is independently proven.",
        "equity_weight_sum":round(sum(x["weight"] for x in positions),8),
        "source":SAMCO_URL,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
    }


def _sundaram_result(fetch_fn,expected):
    raw,_,_=fetch_fn(SUNDARAM_CARD,archive=False,max_bytes=12*1024*1024)
    rows=json.loads(raw)
    if not isinstance(rows,list):
        raise ValueError("Sundaram fund-card response is not a list")
    matches=[
        row for row in rows if isinstance(row,dict)
        and _norm(row.get("GROUP_NAME"))==_norm(SUNDARAM_FAMILY)
    ]
    if len(matches)!=1:
        raise ValueError(f"Sundaram fund-card data exposed {len(matches)} exact Mid Cap rows")
    row=matches[0]
    if str(row.get("FUNDGROUP_ID") or "").strip()!="MC" or _norm(row.get("FUND_CATEGORY"))!="midcap":
        raise ValueError("Sundaram Mid Cap fund-card scheme code/category is not verified")
    path=str(row.get("PORTFOLIO_PATH") or "").strip()
    source=urljoin("https://www.sundarammutual.com",path)
    parsed_url=urlparse(source)
    if (not path or parsed_url.scheme!="https"
        or parsed_url.hostname not in ("www.sundarammutual.com","sundarammutual.com")
        or not parsed_url.path.casefold().endswith((".xls",".xlsx"))
        or not disclosures.official_publication_url(source,"Sundaram")):
        raise ValueError("Sundaram portfolio path is not an approved first-party workbook")
    # AUMASONDATE dates a different metric. The published workbook, not the
    # card's AUM/NAV date or its URL, must prove the exact portfolio month-end.
    body,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    if body.startswith(b"%PDF"):
        raise ValueError("Sundaram source requires a dedicated PDF portfolio parser")
    if not body.startswith((b"PK",b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")):
        raise ValueError("Sundaram portfolio response is not a supported workbook")
    parsed=_parse_workbook(body,SUNDARAM_FAMILY,expected)
    if parsed.get("as_of")!=expected:
        raise ValueError("Sundaram workbook did not prove the current portfolio date")
    return {
        "family":SUNDARAM_FAMILY,"amc":"Sundaram Mutual Fund","status":"recovered",
        **parsed,"scope":"structured_monthly_portfolio",
        "source":source,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,"discovery_source":SUNDARAM_CARD,
        "discovery_source_sha256":hashlib.sha256(raw).hexdigest(),
        "publisher_scheme_code":"MC","card_aum_as_of_raw":row.get("AUMASONDATE"),
    }


COLLECTORS=(
    (KOTAK_FAMILY,_kotak_result),
    (JM_FAMILY,_jm_result),
    (MAHINDRA_FAMILY,_mahindra_result),
    (INVESCO_FAMILY,_invesco_result),
    (SUNDARAM_FAMILY,_sundaram_result),
    (SAMCO_FAMILY,_samco_result),
    (MOTILAL_FAMILY,_motilal_result),
    (BANDHAN_FAMILY,_bandhan_result),
)


def collect(fetch_fn=providers.fetch,today=None):
    today=today or date.today();expected=expected_portfolio_as_of(today)
    staged={x["family"] for x in db.rows(
        "SELECT DISTINCT family FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    for family,collector in COLLECTORS:
        if family not in staged:
            errors.append({"family":family,"error":"staged family identity missing"});continue
        try:
            row=collector(fetch_fn,expected);row["observed_at"]=db.now();results.append(row)
        except Exception as exc:
            error={"family":family,"error":(str(exc) or type(exc).__name__)[:500]}
            if isinstance(exc,KotakSourceRejected):
                error.update(exc.source_evidence)
            errors.append(error)
    return {
        "built_at":db.now(),"staged_category":"mid-cap","portfolio_expected_as_of":expected,
        "targets":len(COLLECTORS),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,"production_writes":0,"public_export_enabled":False,
        "notes":[
            "Structured monthly workbooks are preferred for JM, Invesco and Sundaram where available.",
            "Samco uses the publisher's current All Holdings table, but remains explicitly partial until structured 100% reconciliation is proven.",
            "Motilal Oswal uses the current fund page only to discover the exact dated monthly workbook, which is parsed through the existing structured parser.",
            "Bandhan uses the exact scheme/month CMS disclosure post and read-only finance API to resolve one official workbook, which is parsed through the existing structured parser.",
            "Kotak and Mahindra retain sector-reconciled equity-only evidence, explicitly partial.",
            "Portfolio dates come from their own disclosure, never from unrelated AUM or NAV dates.",
            "Every result requires exact staged family identity and the current regulatory month-end; no live records are written.",
        ],
    }
