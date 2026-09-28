"""Read-only current portfolio recovery for staged Mid Cap batch 5."""
from __future__ import annotations

import calendar
import hashlib
import io
import json
import re
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from . import db, disclosures, jm_portfolios, providers
from .coverage import expected_portfolio_as_of
from .midcap_portfolio_first_party import (
    CORPORATE_HINT, _add_position, _clean, _explicit_dates, _kotak, _percent, _table_rows
)
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
    text=soup.get_text("\n",strip=True)
    if _norm(family) not in _norm(text):
        raise ValueError("First-party page does not contain the exact staged Mid Cap family identity")
    if expected not in _explicit_dates(text):
        raise ValueError(f"First-party page does not explicitly report current portfolio date {expected}")
    return soup,text


def _mahindra_positions(soup):
    out=[]
    for table,rows in _table_rows(soup):
        context=_clean(table.get_text(" ",strip=True))
        if not re.search(r"Company\s*/\s*Issuer|%\s*of\s*Net\s*Assets",context,re.I):
            continue
        for cells in rows:
            if len(cells)<2:continue
            name=next((x for x in cells if x and _percent(x) is None),None)
            weight=next((_percent(x) for x in reversed(cells) if _percent(x) is not None),None)
            if not name or not CORPORATE_HINT.search(name):continue
            _add_position(out,name,weight)
    return out


def _html_result(family,amc,url,parser,fetch_fn,expected):
    body,_,typ=fetch_fn(url,archive=False,max_bytes=12*1024*1024)
    soup,_=_require_html_identity_date(body,family,expected)
    positions=parser(soup)
    if len(positions)<5:
        raise ValueError(f"Only {len(positions)} named current holdings were visible; need at least 5")
    return {
        "family":family,"amc":amc,"status":"recovered","as_of":expected,
        "positions_observed":len(positions),"positions":positions,
        "complete":False,"scope":"first_party_current_factsheet",
        "source":url,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
    }


def _kotak_result(fetch_fn,expected):
    return _html_result(
        KOTAK_FAMILY,"Kotak Mahindra Mutual Fund",KOTAK_URL,_kotak,fetch_fn,expected)


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
    d=date.fromisoformat(expected);found={}
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
    dated_value=str(row.get("AUMASONDATE") or "").strip()
    day=disclosures.report_date(dated_value)
    if day!=expected:
        raise ValueError(f"Sundaram fund-card row is not current: {day or 'unknown'}")
    source=urljoin("https://www.sundarammutual.com",str(row.get("PORTFOLIO_PATH") or "").strip())
    if not source or not disclosures.official_publication_url(source,"Sundaram"):
        raise ValueError("Sundaram current portfolio path is not an approved first-party URL")
    body,_,typ=fetch_fn(source,archive=False,max_bytes=30*1024*1024)
    if body.startswith((b"PK",b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")):
        parsed=_parse_workbook(body,SUNDARAM_FAMILY,expected)
        return {
            "family":SUNDARAM_FAMILY,"amc":"Sundaram Mutual Fund","status":"recovered",
            **parsed,"scope":"structured_monthly_portfolio",
            "source":source,"source_sha256":hashlib.sha256(body).hexdigest(),
            "source_content_type":typ,
        }
    soup,_=_require_html_identity_date(body,SUNDARAM_FAMILY,expected)
    positions=_mahindra_positions(soup)
    if len(positions)<5:
        raise ValueError(f"Sundaram current portfolio source exposed only {len(positions)} named holdings")
    return {
        "family":SUNDARAM_FAMILY,"amc":"Sundaram Mutual Fund","status":"recovered",
        "as_of":expected,"positions_observed":len(positions),"positions":positions,
        "complete":False,"scope":"first_party_current_portfolio",
        "source":source,"source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
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
            "Kotak and Mahindra current factsheet holdings count only as partial current evidence.",
            "Every result requires exact staged family identity and the current regulatory month-end; no live records are written.",
        ],
    }
