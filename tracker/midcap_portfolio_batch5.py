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
from .coverage import expected_portfolio_as_of
from .midcap_factsheet_equities import equity_positions, validate_factsheet_context
from .midcap_portfolio_structured import _parse_workbook


KOTAK_FAMILY="Kotak Mid Cap Fund"
KOTAK_URL="https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html"
JM_FAMILY="JM Mid Cap Fund"
MAHINDRA_FAMILY="Mahindra Manulife Mid Cap Fund"
MAHINDRA_URL="https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html"
INVESCO_FAMILY="Invesco India Mid Cap Fund"
INVESCO_ROOT="https://www.invescomutualfund.com"
SUNDARAM_FAMILY="Sundaram Mid Cap Fund"
SUNDARAM_CARD="https://www.sundarammutual.com/Upload/JSON/Fund_Card_data.json"


def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").casefold())


def _require_html_identity_date(body,family,expected):
    soup=BeautifulSoup(body,"html.parser")
    validate_factsheet_context(soup,family,expected)
    return soup,soup.get_text("\n",strip=True)


def _mahindra_positions(soup):
    return equity_positions(soup)


def _html_result(family,amc,url,parser,fetch_fn,expected):
    body,_,typ=fetch_fn(url,archive=False,max_bytes=12*1024*1024)
    soup,_=_require_html_identity_date(body,family,expected)
    positions=parser(soup)
    if len(positions)<5:
        raise ValueError(f"Only {len(positions)} named current holdings were visible; need at least 5")
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
        KOTAK_FAMILY,"Kotak Mahindra Mutual Fund",KOTAK_URL,equity_positions,fetch_fn,expected)


def _mahindra_result(fetch_fn,expected):
    return _html_result(
        MAHINDRA_FAMILY,"Mahindra Manulife Mutual Fund",MAHINDRA_URL,
        _mahindra_positions,fetch_fn,expected)


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
            errors.append({"family":family,"error":(str(exc) or type(exc).__name__)[:500]})
    return {
        "built_at":db.now(),"staged_category":"mid-cap","portfolio_expected_as_of":expected,
        "targets":len(COLLECTORS),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,"production_writes":0,"public_export_enabled":False,
        "notes":[
            "Structured monthly workbooks are preferred for JM, Invesco and Sundaram where available.",
            "Kotak and Mahindra retain sector-reconciled equity-only evidence, explicitly partial.",
            "Portfolio dates come from their own disclosure, never from unrelated AUM or NAV dates.",
            "Every result requires exact staged family identity and the current regulatory month-end; no live records are written.",
        ],
    }
