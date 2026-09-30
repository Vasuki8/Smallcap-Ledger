"""Read-only current portfolio evidence audit for staged Mid Cap batch 1."""
from __future__ import annotations

from datetime import date,datetime
import hashlib
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import amfi_metrics,db,providers
from .coverage import expected_portfolio_as_of


SOURCES={
    "Canara Robeco Mid Cap Fund":{
        "url":"https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html",
        "parser":"canara","scope":"full_page_portfolio",
    },
    "Kotak Mid Cap Fund":{
        "url":"https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html",
        "parser":"kotak","scope":"full_page_portfolio",
    },
    "DSP Midcap Fund":{
        "url":"https://www.dspim.com/invest/mutual-fund-schemes/equity-funds/mid-cap-fund/dspsm-regular-growth",
        "parser":"dsp","scope":"full_page_portfolio",
    },
    "Baroda BNP Paribas Mid Cap Fund":{
        "url":"https://www.barodabnpparibasmf.in/mutual-fund-schemes/equity-funds/baroda-bnp-paribas-mid-cap-fund/direct-growth",
        "parser":"baroda","scope":"top_5",
    },
    "HDFC Mid Cap Fund":{
        "url":"https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/regular",
        "parser":"hdfc","scope":"top_holdings",
    },
    "ITI Mid Cap Fund":{
        "url":"https://www.itiamc.com/digitalfactsheet/August2026/innerpages/Mid-Cap.html",
        "parser":"iti","scope":"digital_factsheet_named_holdings",
    },
    "BANK OF INDIA MID CAP FUND":{
        "url":"https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund",
        "parser":"boi","scope":"top_10",
    },
}

HOSTS={
    "digitalassets.canararobeco.com","www.kotakmf.com","www.dspim.com",
    "www.barodabnpparibasmf.in","www.hdfcfund.com","www.itiamc.com","www.boimf.in",
}

CORPORATE_HINT=re.compile(
    r"\b(?:Ltd\.?|Limited|Bank|Finance|Financial|Corporation|Industries|"
    r"Healthcare|Laboratories|Pharma|Technologies|Systems|Services|Enterprises|"
    r"Properties|Tyres|Cement|Forge|Beverages|Electric|Energy|Power|Telecom|"
    r"Hotels|Airtel|Biocon|Eternal|Swiggy|Lenskart|BSE|MRF|Coforge|Mphasis)\b",
    re.I,
)
EXCLUDE=re.compile(
    r"^(?:Equit(?:y|ies).*|Listed.*|Banks?|Finance|Retailing|Auto Components|"
    r"IT\s*-\s*Software|Capital Markets|Consumer Durables|Electrical Equipment|"
    r"Pharmaceuticals.*|Healthcare Services|Industrial Products|"
    r"Money Market Instruments|Net Current Assets|Grand Total.*|"
    r"Holdings|Issuer/Instrument|View All Holdings|Sector.*)$",
    re.I,
)


def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").casefold())


def _clean(value):
    return re.sub(r"\s+"," ",str(value or "")).strip()


def _percent(value):
    token=_clean(value).replace("%","").replace(",","")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?",token):
        return None
    number=float(token)
    return number if 0<=number<=100 else None


def _explicit_dates(text):
    dates=set()
    patterns=(
        (r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b","dmy"),
        (r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(20\d{2})\b","mdy"),
        (r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b","num"),
    )
    for pattern,kind in patterns:
        for m in re.finditer(pattern,text,re.I):
            try:
                if kind=="dmy":
                    d=datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}","%d %B %Y").date()
                    if not d:
                        continue
                elif kind=="mdy":
                    d=datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}","%B %d %Y").date()
                else:
                    d=date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
                if d<=date.today():dates.add(d.isoformat())
            except ValueError:
                # Also accept abbreviated English month labels.
                if kind in ("dmy","mdy"):
                    try:
                        raw=(f"{m.group(1)} {m.group(2)} {m.group(3)}" if kind=="dmy"
                             else f"{m.group(1)} {m.group(2)} {m.group(3)}")
                        fmt="%d %b %Y" if kind=="dmy" else "%b %d %Y"
                        d=datetime.strptime(raw,fmt).date()
                        if d<=date.today():dates.add(d.isoformat())
                    except ValueError:
                        pass
    return dates


def _add_position(out,name,weight):
    name=_clean(name)
    if not name or EXCLUDE.fullmatch(name):
        return
    if weight is None or weight<=0 or weight>20:
        return
    key=_norm(name)
    if key and key not in {_norm(x["name"]) for x in out}:
        out.append({"name":name,"weight":round(float(weight),8)})


def _table_rows(soup):
    for table in soup.find_all("table"):
        rows=[]
        for tr in table.find_all("tr"):
            cells=[_clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
            if cells:rows.append(cells)
        if rows:yield table,rows


def _canara(soup):
    out=[]
    for _,rows in _table_rows(soup):
        for cells in rows:
            marker=next((i for i,x in enumerate(cells) if x in ("L","M","S")),None)
            if marker is None or marker<1:continue
            weight=next((_percent(x) for x in reversed(cells[marker+1:]) if _percent(x) is not None),None)
            name=next((x for x in reversed(cells[:marker]) if x),None)
            _add_position(out,name,weight)
    return out


def _kotak(soup):
    out=[]
    for table,rows in _table_rows(soup):
        context=_clean(table.get_text(" ",strip=True))
        if "Issuer/Instrument" not in context or not re.search(r"%\s*to\s*Net\s*Assets",context,re.I):
            continue
        for cells in rows:
            if len(cells)<2:continue
            weight=next((_percent(x) for x in reversed(cells[1:]) if _percent(x) is not None),None)
            name=cells[0]
            if CORPORATE_HINT.search(name):
                _add_position(out,name,weight)
    return out


def _dsp(soup):
    out=[]
    for table,rows in _table_rows(soup):
        context=_clean(table.get_text(" ",strip=True))
        if not re.search(r"Holdings",context,re.I) or not re.search(r"Weight\s*%?",context,re.I):
            continue
        for cells in rows:
            if len(cells)<2:continue
            weight=next((_percent(x) for x in reversed(cells[1:]) if _percent(x) is not None),None)
            _add_position(out,cells[0],weight)
    return out


def _baroda(text):
    out=[]
    match=re.search(r"Holdings\s*\(\s*Top\s*5\s*\)(.*?)(?:Sector\s+Allocation|Rolling\s+Returns)",text,re.I|re.S)
    if not match:return out
    block=match.group(1)
    parts=[_clean(x) for x in re.split(r"[\r\n]+",block) if _clean(x)]
    pending=None
    for token in parts:
        p=_percent(token)
        if p is not None and pending:
            _add_position(out,pending,p);pending=None
        elif p is None and not re.search(r"See All Holdings|Holdings",token,re.I):
            pending=token
    return out


def _iti(soup):
    """Read named security rows from ITI's dated digital factsheet portfolio table.

    The publisher currently includes a leading marker column, so columns are
    located from the exact visible header rather than assumed by position.
    Sector/asset-class subtotal labels are bold in the issuer column and are
    excluded structurally. Evidence stays partial until independently reconciled.
    """
    out=[]
    for table in soup.find_all("table"):
        rows=[r for r in table.find_all("tr") if r.find_parent("table") is table]
        header_index=None
        name_col=None
        for i,row in enumerate(rows[:8]):
            cells=row.find_all(["td","th"],recursive=False)
            values=[_clean(cell.get_text(" ",strip=True)) for cell in cells]
            matches=[j for j,value in enumerate(values) if _norm(value)=="nameoftheinstrument"]
            if len(matches)==1 and any(
                re.search(r"%\s*to\s*NAV",value,re.I) for value in values[matches[0]+1:]
            ):
                header_index=i
                name_col=matches[0]
                break
        if header_index is None or name_col is None:
            continue
        for row in rows[header_index+1:]:
            cells=row.find_all(["td","th"],recursive=False)
            if len(cells)<=name_col:
                continue
            name_cell=cells[name_col]
            if name_cell.find(["b","strong"]):
                continue
            name=_clean(name_cell.get_text(" ",strip=True))
            if not CORPORATE_HINT.search(name):
                continue
            values=[_clean(cell.get_text(" ",strip=True)) for cell in cells[name_col+1:]]
            weight=next(
                (_percent(value) for value in reversed(values) if _percent(value) is not None),
                None,
            )
            _add_position(out,name,weight)
    return out


def _boi(soup):
    """Read Bank of India's explicitly labelled Top 10 portfolio table."""
    out=[]
    matches=0
    for _,rows in _table_rows(soup):
        header=None
        for i,cells in enumerate(rows[:5]):
            labels=[_norm(value) for value in cells]
            if "portfoliodetails" in labels and "tonetassets" in labels:
                header=i
                break
        if header is None:
            continue
        matches+=1
        for cells in rows[header+1:]:
            if len(cells)<2:
                continue
            weight=next((_percent(value) for value in reversed(cells[1:])
                         if _percent(value) is not None),None)
            _add_position(out,cells[0],weight)
    if matches!=1:
        raise ValueError(f"Bank of India page exposed {matches} exact Top 10 portfolio tables")
    if len(out)!=10:
        raise ValueError(f"Bank of India Top 10 table exposed {len(out)} named holdings")
    return out


def _hdfc(soup,text):
    # HDFC's public page labels the current portfolio section server-side, but
    # holdings may remain client-rendered. Count evidence only if named rows are
    # actually present in the fetched source.
    out=[]
    for table,rows in _table_rows(soup):
        context=_clean(table.get_text(" ",strip=True))
        if not re.search(r"(?:Top\s+Holdings|Portfolio)",context,re.I):
            continue
        for cells in rows:
            if len(cells)<2:continue
            weight=next((_percent(x) for x in reversed(cells[1:]) if _percent(x) is not None),None)
            if CORPORATE_HINT.search(cells[0]):
                _add_position(out,cells[0],weight)
    return out


PARSERS={"canara":_canara,"kotak":_kotak,"dsp":_dsp,"iti":_iti,"boi":_boi}


def inspect_family(family,config,fetch_fn=providers.fetch,today=None):
    today=today or date.today()
    expected=expected_portfolio_as_of(today)
    url=config["url"]
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in HOSTS:
        raise ValueError("Portfolio audit source is not an approved first-party host")
    body,_,typ=fetch_fn(url,archive=False,max_bytes=12*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    text=soup.get_text("\n",strip=True)
    if _norm(family) not in _norm(text):
        raise ValueError("First-party source does not contain the exact staged Mid Cap family identity")
    dates=_explicit_dates(text)
    if expected not in dates:
        raise ValueError(f"First-party source does not explicitly report current portfolio date {expected}")
    parser=config["parser"]
    if parser in PARSERS:
        positions=PARSERS[parser](soup)
    elif parser=="baroda":
        positions=_baroda(text)
    elif parser=="hdfc":
        positions=_hdfc(soup,text)
    else:
        raise ValueError("Unknown portfolio evidence parser")
    if len(positions)<5:
        raise ValueError(f"Only {len(positions)} named current holdings were visible; need at least 5")
    return {
        "family":family,
        "status":"recovered",
        "as_of":expected,
        "positions_observed":len(positions),
        "positions":positions,
        "scope":config["scope"],
        "complete":False,
        "source":url,
        "source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
        "observed_at":db.now(),
    }


def collect(fetch_fn=providers.fetch,today=None):
    staged={r["family"]:r["amc"] for r in db.rows(
        "SELECT DISTINCT family,amc FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    for family,config in SOURCES.items():
        if family not in staged:
            errors.append({"family":family,"source":config["url"],"error":"staged family identity missing"})
            continue
        try:
            row=inspect_family(family,config,fetch_fn=fetch_fn,today=today)
            row["amc"]=staged[family]
            results.append(row)
        except Exception as exc:
            errors.append({"family":family,"amc":staged.get(family),"source":config["url"],
                           "error":(str(exc) or type(exc).__name__)[:300]})
    return {
        "built_at":db.now(),
        "staged_category":"mid-cap",
        "families":len(staged),
        "portfolio_expected_as_of":expected_portfolio_as_of(today or date.today()),
        "targets":len(SOURCES),
        "current_portfolio_evidence":len(results),
        "failed":len(errors),
        "results":results,
        "errors":errors,
        "not_yet_audited":sorted(set(staged)-set(SOURCES)),
        "production_writes":0,
        "public_export_enabled":False,
        "notes":[
            "This is read-only source evidence and does not insert Mid Cap portfolios or holdings.",
            "A covered family requires exact staged identity, the regulatory current month-end date, and at least five named holdings with reported weights.",
            "Every batch-1 snapshot remains complete=false. Full-page source scope does not become a complete portfolio without explicit 100% reconciliation.",
        ],
    }
