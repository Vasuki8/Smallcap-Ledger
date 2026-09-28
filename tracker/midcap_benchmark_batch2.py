"""Read-only first-party benchmark identity audit for staged Mid Cap batch 2."""
from __future__ import annotations

from . import db
from . import midcap_benchmark_documents as documents
from . import midcap_benchmark_labels as labeled
from .midcap_benchmark_first_party import inspect_family


SOURCES={
    "Mahindra Manulife Mid Cap Fund":"https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html",
    "Tata Mid Cap Fund":"https://www.tatamutualfund.com/mutual-funds/tata-mid-cap-fund-direct-growth",
    "Sundaram Mid Cap Fund":"https://www.sundarammutual.com/Sundaram-Mid-Cap-Fund",
    "JM Mid Cap Fund":"https://www.jmfinancialmf.com/products/Equity/JM-Midcap-Fund/J644/Regular-Growth-Option",
    "Baroda BNP Paribas Mid Cap Fund":"https://www.barodabnpparibasmf.in/mutual-fund-schemes/equity-funds/baroda-bnp-paribas-mid-cap-fund/direct-growth",
    **labeled.SOURCES,
    **documents.SOURCES,
}


def collect(fetch_fn=None):
    from . import providers
    fetch_fn=fetch_fn or providers.fetch
    staged={r["family"]:r["amc"] for r in db.rows(
        "SELECT DISTINCT family,amc FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    results=[];errors=[]
    for family,url in SOURCES.items():
        if family not in staged:
            errors.append({"family":family,"source":url,"error":"staged family identity missing"})
            continue
        try:
            registered_amc = (
                labeled.AMCS.get(family)
                if family in labeled.SOURCES
                else documents.AMCS.get(family)
                if family in documents.SOURCES
                else None
            )
            if registered_amc is not None and staged[family] != registered_amc:
                raise ValueError("Staged AMC ownership does not match the registered benchmark source")
            if family in labeled.SOURCES:
                inspector = labeled.inspect_family
            elif family in documents.SOURCES:
                inspector = documents.inspect_family
            else:
                inspector = inspect_family
            row=inspector(family,url,fetch_fn=fetch_fn)
            row["amc"]=staged[family]
            results.append(row)
        except Exception as exc:
            errors.append({"family":family,"amc":staged.get(family),"source":url,
                           "error":(str(exc) or type(exc).__name__)[:300]})
    return {
        "built_at":db.now(),"staged_category":"mid-cap","families":len(staged),
        "targets":len(SOURCES),"recovered":len(results),"failed":len(errors),
        "results":results,"errors":errors,
        "production_writes":0,"public_export_enabled":False,
        "notes":[
            "Batch 2 uses exact current first-party fund pages, factsheets or scheme documents only.",
            "No benchmark is inferred from category membership.",
            "Axis, Mirae, Aditya Birla Sun Life and SBI use reviewed fund-specific primary labels; additional comparators and effective dates remain separate.",
            "A published benchmark identity does not prove that its benchmark series is available to the tracker.",
        ],
    }
