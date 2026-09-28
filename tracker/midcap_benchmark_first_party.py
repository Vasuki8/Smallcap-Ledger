"""Read-only first-party benchmark identity audit for staged Mid Cap batch 1."""
from __future__ import annotations

from datetime import date,datetime
import hashlib
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers


SOURCES={
    "Canara Robeco Mid Cap Fund":"https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html",
    "Kotak Mid Cap Fund":"https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html",
    "The Wealth Company Mid Cap Fund":"https://www.wealthcompanyamc.in/our-funds/fund/the-wealth-company-mid-cap-fund/154479/",
    "BANK OF INDIA MID CAP FUND":"https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund",
    "PGIM India Midcap Fund":"https://www.pgimindia.com/mutual-funds/equity-funds/midcap-fund",
    "Franklin India Mid Cap Fund":"https://www.franklintempletonindia.com/fund-details/fund-overview/4615/franklin-india-mid-cap-fund-erstwhile-franklin-india-prima-fund",
    "UTI - Mid Cap Fund":"https://www.utimf.com/mutual-funds/uti-mid-cap-fund",
    "HDFC Mid Cap Fund":"https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/regular",
    "DSP Midcap Fund":"https://www.dspim.com/invest/mutual-fund-schemes/equity-funds/mid-cap-fund/dspsm-regular-growth",
    "Helios Mid Cap Fund":"https://www.heliosmf.in/helios-mid-cap-fund/",
}

HOSTS={
    "digitalassets.canararobeco.com","www.kotakmf.com","www.wealthcompanyamc.in",
    "www.boimf.in","www.pgimindia.com","www.franklintempletonindia.com",
    "www.utimf.com","www.hdfcfund.com","www.dspim.com","www.heliosmf.in",
}

INDEX_PATTERNS=(
    re.compile(r"\bBSE\s*150\s*Mid\s*Cap\s*(?:Total\s*Returns?\s*Index|TRI)\b",re.I),
    re.compile(r"\bNIFTY\s+Midcap\s+150\s+Index\s*\(\s*Total\s+Returns?\s+Index\s*\)",re.I),
    re.compile(r"\bNIFTY\s+Midcap\s+150\s+Total\s+Returns?\s+Index(?:\s*\(TRI\))?\b",re.I),
    re.compile(r"\bNIFTY\s+Midcap\s+150\s*(?:-|\()?\s*TRI\s*\)?\b",re.I),
    re.compile(r"\bNIFTY\s+Midcap\s+150\b",re.I),
    re.compile(r"\bNIFTY\s+Midcap\s+100\s*(?:-|\()?\s*TRI\s*\)?\b",re.I),
)


def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").casefold())


def _clean(value):
    return re.sub(r"\s+"," ",str(value or "")).strip(" :-\t\r\n")


def _family_present(text,family):
    return _norm(family) in _norm(text)


def _benchmark_contexts(text):
    flat=_clean(text)
    contexts=[]
    for match in re.finditer(r"benchmark",flat,re.I):
        contexts.append(flat[max(0,match.start()-80):min(len(flat),match.end()+360)])
    return contexts


def _canonical(raw):
    value=_clean(raw)
    value=re.sub(r"\s*\(\s*TRI\s*\)\s*$"," TRI",value,flags=re.I)
    value=re.sub(r"\s+-\s+TRI\b"," TRI",value,flags=re.I)
    return _clean(value)


def extract_benchmarks(text):
    """Return ordered benchmark identities found close to explicit benchmark labels."""
    found=[]
    for context in _benchmark_contexts(text):
        for pattern in INDEX_PATTERNS:
            for match in pattern.finditer(context):
                value=_canonical(match.group(0))
                key=value.casefold()
                if key not in {x.casefold() for x in found}:
                    found.append(value)
        if found:
            # Prefer the first explicit benchmark block; it is normally Tier 1.
            break
    return found


def _source_data_as_of(text):
    candidates=[]
    for pattern,fmt in (
        (r"\bas\s+on\s+(\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b","%d %B %Y"),
        (r"\bas\s+on\s+(\d{1,2}[/-]\d{1,2}[/-]20\d{2})\b",None),
        (r"\bas\s+of\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})\b","%B %d, %Y"),
    ):
        for m in re.finditer(pattern,text,re.I):
            raw=_clean(m.group(1))
            try:
                if fmt:
                    d=datetime.strptime(raw,fmt).date()
                else:
                    d=providers.iso(raw)
                    d=date.fromisoformat(d)
                if d<=date.today():candidates.append(d)
            except Exception:
                pass
    return max(candidates).isoformat() if candidates else None


def inspect_family(family,url,fetch_fn=providers.fetch):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in HOSTS:
        raise ValueError("Benchmark audit source is not an approved first-party host")
    body,_,typ=fetch_fn(url,archive=False,max_bytes=8*1024*1024)
    text=BeautifulSoup(body,"html.parser").get_text("\n",strip=True)
    if not _family_present(text,family):
        raise ValueError("First-party page does not contain the exact staged Mid Cap family identity")
    identities=extract_benchmarks(text)
    if not identities:
        raise ValueError("No explicitly labelled Mid Cap benchmark identity was found")
    return {
        "family":family,
        "status":"recovered",
        "primary_benchmark":identities[0],
        "reported_benchmarks":identities,
        "source":url,
        "source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
        "source_data_as_of":_source_data_as_of(text),
        "observed_at":db.now(),
    }


def collect(fetch_fn=providers.fetch):
    staged={r["family"]:r["amc"] for r in db.rows(
        "SELECT DISTINCT family,amc FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    for family,url in SOURCES.items():
        if family not in staged:
            errors.append({"family":family,"source":url,"error":"staged family identity missing"})
            continue
        try:
            row=inspect_family(family,url,fetch_fn=fetch_fn)
            row["amc"]=staged[family]
            results.append(row)
        except Exception as exc:
            errors.append({"family":family,"amc":staged.get(family),"source":url,
                           "error":(str(exc) or type(exc).__name__)[:300]})
    recovered={r["family"] for r in results}
    return {
        "built_at":db.now(),
        "staged_category":"mid-cap",
        "families":len(staged),
        "targets":len(SOURCES),
        "recovered":len(results),
        "failed":len(errors),
        "benchmark_coverage_after_batch":len(recovered),
        "results":results,
        "errors":errors,
        "not_yet_audited":sorted(set(staged)-set(SOURCES)),
        "production_writes":0,
        "public_export_enabled":False,
        "notes":[
            "This is read-only source evidence; it does not insert Mid Cap benchmark metrics.",
            "Every recovered benchmark requires the exact staged family identity on the first-party page and an explicit Benchmark label nearby.",
            "The publisher's benchmark wording is retained; TRI is never inferred when the source does not state it.",
        ],
    }
