"""Read-only source coverage audit for the staged Mid Cap category."""
from __future__ import annotations

from collections import defaultdict
from datetime import date,timedelta
import hashlib
import json
import re
import time
from urllib.parse import urlencode

import httpx

from . import amfi_metrics,db,providers
from .categories import REGISTRY
from .coverage import expected_portfolio_as_of


def _is_mid_cap_category(value):
    text=re.sub(r"\s+"," ",str(value or "").strip())
    return bool(re.fullmatch(r"(?:Equity Scheme\s*-\s*)?Mid\s*Cap\s*Fund",text,re.I))


def _family_map():
    rows=db.rows("""SELECT code,family,amc,plan,option,history_checked,history_status
      FROM category_staged_schemes WHERE category='mid-cap' ORDER BY amc,family,code""")
    groups={}
    for row in rows:
        key=(row["amc"],row["family"])
        item=groups.setdefault(key,{
            "family":row["family"],"amc":row["amc"],"codes":[],
            "plans":set(),"options":set(),"history_checked":[],
        })
        item["codes"].append(int(row["code"]))
        item["plans"].add(row["plan"]);item["options"].add(row["option"])
        if row.get("history_checked"):
            item["history_checked"].append(row["history_checked"])
    result=[]
    for item in groups.values():
        item["codes"]=sorted(item["codes"])
        item["plans"]=sorted(item["plans"])
        item["options"]=sorted(item["options"])
        item["nav_history_checked"]=max(item.pop("history_checked"),default=None)
        result.append(item)
    return sorted(result,key=lambda x:(x["amc"].casefold(),x["family"].casefold()))


def _match_aum(rows,families,today=None):
    today=today or date.today()
    lookup={amfi_metrics.normalized(x["family"]):x["family"] for x in families}
    matched={};unmatched=set()
    for row in rows or []:
        name=str(row.get("schemeName") or "").strip()
        family=lookup.get(amfi_metrics.normalized(name))
        if not family:
            if name:unmatched.add(name)
            continue
        try:
            value=providers.number(row.get("dailyAUM"))
            day=providers.iso(row.get("navDate",""))
        except (TypeError,ValueError):
            continue
        if value<=0 or day>today.isoformat():
            continue
        current=matched.get(family)
        evidence={
            "as_of":day,"value":value,"unit":"₹ crore · daily scheme AUM",
            "scheme_name":name,"source":amfi_metrics.PERFORMANCE_PAGE,
        }
        if current is None or day>current["as_of"]:
            matched[family]=evidence
    return matched,sorted(unmatched)


def _match_ter(rows,families,today=None):
    today=today or date.today()
    lookup={amfi_metrics.normalized(x["family"]):x["family"] for x in families}
    matched={};unmatched=set()
    for row in rows or []:
        if not _is_mid_cap_category(row.get("SchemeCat_Desc")):
            continue
        name=str(row.get("Scheme_Name") or "").strip()
        family=lookup.get(amfi_metrics.normalized(name))
        if not family:
            if name:unmatched.add(name)
            continue
        raw_day=str(row.get("TER_Date") or "").strip()
        day=None
        for candidate in (raw_day,raw_day[:10]):
            if not candidate:continue
            try:
                day=providers.iso(candidate)
                break
            except ValueError:
                pass
        if not day:continue
        if day>today.isoformat():continue
        evidence={
            "as_of":day,"scheme_name":name,"category":row.get("SchemeCat_Desc"),
            "source":amfi_metrics.TER_PAGE,"direct":None,"regular":None,
        }
        for prefix,key in (("D","direct"),("R","regular")):
            raw=row.get(prefix+"_TER")
            if raw is None or str(raw).strip() in ("","-","NA","N/A"):continue
            try:value=providers.number(raw)
            except (TypeError,ValueError):continue
            if 0<=value<=10:
                evidence[key]={"value":value,"unit":"% p.a. · AMC-reported via AMFI"}
        if not evidence["direct"] and not evidence["regular"]:
            continue
        current=matched.get(family)
        if current is None or day>current["as_of"]:
            matched[family]=evidence
    return matched,sorted(unmatched)


def _source_pages_for(amc,source_pages):
    a=str(amc or "").casefold()
    result=[]
    for row in source_pages:
        m=str(row.get("amc_match") or "").casefold()
        if not m or not (m in a or a in m):
            continue
        result.append({
            "label":row.get("label"),"url":row.get("url"),
            "status":row.get("status"),"last_checked":row.get("last_checked"),
        })
    return result


def report(aum_rows=None,ter_rows=None,source_checks=None,source_errors=None,today=None):
    """Build the audit strictly from staged identity plus supplied/read-only evidence."""
    today=today or date.today()
    families=_family_map()
    if not families:
        raise ValueError("No staged Mid Cap families are available")
    aum,unmatched_aum=_match_aum(aum_rows,families,today=today)
    ter,unmatched_ter=_match_ter(ter_rows,families,today=today)
    expected=expected_portfolio_as_of(today)
    live_amcs={row["amc"] for row in db.rows("SELECT DISTINCT amc FROM schemes")}
    source_pages=db.rows("""SELECT amc_match,url,label,status,last_checked
      FROM source_pages WHERE enabled=1 ORDER BY amc_match,url""")

    rows=[]
    for item in families:
        family=item["family"];amc=item["amc"]
        benchmark=db.one("""SELECT as_of,value,unit,plan,source FROM metrics
          WHERE family=? AND metric='benchmark'
          ORDER BY as_of DESC,observed_at DESC LIMIT 1""",(family,))
        portfolio=db.one("""SELECT p.as_of,p.source,p.hash,p.complete,COUNT(h.id) positions
          FROM portfolios p JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id
          ORDER BY p.as_of DESC,p.complete DESC,COUNT(h.id) DESC LIMIT 1""",(family,))
        documents=db.one("""SELECT COUNT(*) n FROM documents
          WHERE family=? AND origin='AMC'""",(family,))["n"]
        portfolio_current=bool(portfolio and portfolio["as_of"]>=expected)
        pages=_source_pages_for(amc,source_pages)
        row={
            **item,
            "aum":aum.get(family),
            "ter":ter.get(family),
            "direct_ter_available":bool(ter.get(family) and ter[family].get("direct")),
            "benchmark_identity":benchmark,
            "portfolio":portfolio,
            "portfolio_current":portfolio_current,
            "exact_amc_documents":documents,
            "shared_live_amc":amc in live_amcs,
            "amc_source_candidates":pages,
        }
        blockers=[]
        if not row["aum"]:blockers.append("aum")
        if not row["direct_ter_available"]:blockers.append("direct_ter")
        if not row["benchmark_identity"]:blockers.append("benchmark_identity")
        if not row["portfolio_current"]:blockers.append("current_portfolio")
        row["coverage_gaps"]=blockers
        row["all_required_source_evidence"]=not blockers
        rows.append(row)

    counts={
        "families":len(rows),
        "scheme_codes":sum(len(r["codes"]) for r in rows),
        "aum":sum(bool(r["aum"]) for r in rows),
        "ter_any":sum(bool(r["ter"]) for r in rows),
        "direct_ter":sum(r["direct_ter_available"] for r in rows),
        "benchmark_identity":sum(bool(r["benchmark_identity"]) for r in rows),
        "portfolio":sum(bool(r["portfolio"]) for r in rows),
        "portfolio_current":sum(r["portfolio_current"] for r in rows),
        "all_required_source_evidence":sum(r["all_required_source_evidence"] for r in rows),
        "shared_live_amcs":len({r["amc"] for r in rows if r["shared_live_amc"]}),
        "amcs_with_source_candidates":len({r["amc"] for r in rows if r["amc_source_candidates"]}),
    }
    gates=[]
    if REGISTRY["mid-cap"].stage!="live":gates.append("mid_cap_registry_stage_is_staged")
    for key in ("aum","direct_ter","benchmark_identity","portfolio_current"):
        if counts[key]<counts["families"]:gates.append("mid_cap_"+key+"_coverage_incomplete")
    errors=list(source_errors or [])
    if errors:gates.append("mid_cap_source_audit_fetch_errors")
    return {
        "built_at":db.now(),
        "staged_category":"mid-cap",
        "stage":REGISTRY["mid-cap"].stage,
        "public_export_enabled":False,
        "production_writes":0,
        "portfolio_expected_as_of":expected,
        "counts":counts,
        "source_checks":list(source_checks or []),
        "source_errors":errors,
        "unmatched_mid_cap_aum_names":unmatched_aum,
        "unmatched_mid_cap_ter_names":unmatched_ter,
        "families":rows,
        "remaining_gates":gates,
        "source_coverage_ready":counts["all_required_source_evidence"]==counts["families"] and not errors,
        "mid_cap_launch_ready":False,
        "notes":[
            "This audit is read-only: it does not insert Mid Cap metrics, portfolios, documents, schemes, or NAVs.",
            "AUM and TER are matched only to the exact staged Mid Cap family identity; TER rows must also carry the exact Mid Cap category.",
            "Benchmark and portfolio coverage require exact retained family evidence. Shared-AMC collectors are reported only as operational candidates, never as proof of Mid Cap data coverage.",
            "Direct TER is the expense-ratio gate because the current public Small Cap experience uses a Direct-plan fee figure.",
            "Portfolio freshness uses the same regulatory month-end expectation as the live coverage report.",
            "A staged category remains ineligible for public export regardless of source coverage.",
        ],
    }


def _fetch_midcap_aum(families,lookback_days=12):
    headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept":"application/json, text/plain, */*",
        "Referer":amfi_metrics.PERFORMANCE_PAGE,
    }
    lookup={amfi_metrics.normalized(x["family"]) for x in families}
    checks=[]
    with httpx.Client(base_url=amfi_metrics.POLLING_BASE,headers=headers,timeout=60,follow_redirects=True) as client:
        response,filters=amfi_metrics._performance_json(client,amfi_metrics.PERFORMANCE_FILTERS,{})
        checks.append({"kind":"aum_filters","source":str(response.url),"sha256":hashlib.sha256(response.content).hexdigest()})
        if not isinstance(filters,dict):raise ValueError("AMFI fund-performance filters changed format")
        maturity=next((x for x in filters.get("maturityTypeList",[]) if "open" in str(x.get("name","")).lower()),None)
        equity=next((x for x in filters.get("investmentTypeList",[]) if str(x.get("name","")).strip().lower()=="equity"),None)
        if not maturity or not equity:raise ValueError("AMFI filters no longer identify open-ended equity")
        response,subs=amfi_metrics._performance_json(client,amfi_metrics.PERFORMANCE_SUBCATEGORY,{"category":equity.get("id")})
        checks.append({"kind":"aum_subcategories","source":str(response.url),"sha256":hashlib.sha256(response.content).hexdigest()})
        if not isinstance(subs,list):raise ValueError("AMFI subcategory response changed format")
        mid=next((x for x in subs if amfi_metrics.normalized(x.get("name","")) in ("midcap","midcapfund")),None)
        if not mid:raise ValueError("AMFI filters no longer identify Mid Cap")
        minimum=max(10,len(families)//2)
        for offset in range(lookback_days):
            day=date.today()-timedelta(days=offset)
            if day.weekday()>=5:continue
            label=day.strftime("%d-%b-%Y")
            request={"maturityType":maturity.get("id"),"category":equity.get("id"),
                     "subCategory":mid.get("id"),"mfid":0,"reportDate":label}
            response,rows=amfi_metrics._performance_json(client,amfi_metrics.PERFORMANCE_DATA,request)
            if not isinstance(rows,list):continue
            matched=set()
            for row in rows:
                if not isinstance(row,dict):continue
                if amfi_metrics.normalized(row.get("schemeName","")) not in lookup:continue
                try:value=providers.number(row.get("dailyAUM"))
                except (TypeError,ValueError):continue
                if value>0:matched.add(amfi_metrics.normalized(row.get("schemeName","")))
            checks.append({
                "kind":"aum_mid_cap","source":str(response.url),"request":request,
                "sha256":hashlib.sha256(response.content).hexdigest(),"matched_families":len(matched),
            })
            if len(matched)>=minimum:return rows,checks
    raise ValueError("AMFI returned no plausible recent Mid Cap AUM response")


def _month_label(today,offset):
    n=today.year*12+today.month-1-offset
    year,month=divmod(n,12);month+=1
    return f"{month:02d}-{year}"


def _fetch_midcap_ter(families,months=3,fetch_fn=providers.fetch,sleep_fn=time.sleep):
    """Read AMFI TER by AMC×month; never sweep the full industry in one query."""
    def get_json(url):
        last=None
        for attempt in range(3):
            try:
                body,_,_=fetch_fn(url,archive=False,max_bytes=16*1024*1024)
                return body,json.loads(body)
            except (json.JSONDecodeError,UnicodeDecodeError) as exc:
                last=exc
                if attempt<2:sleep_fn(2**attempt)
        raise ValueError("AMFI TER response was not valid JSON after bounded retries") from last

    rows=[];checks=[];errors=[];today=date.today()
    amc_families=defaultdict(set)
    for item in families:
        amc_families[item["amc"]].add(item["family"])

    mf_url=amfi_metrics.BASE+"/api/populate-mf"
    body,payload=get_json(mf_url)
    mf_rows=payload.get("data",payload) if isinstance(payload,dict) else payload
    if not isinstance(mf_rows,list):
        raise ValueError("AMFI mutual-fund selector response changed format")
    mf_by_name={}
    for row in mf_rows:
        if not isinstance(row,dict):continue
        name=str(row.get("mfName") or "").strip()
        mfid=str(row.get("mfId") or "").strip()
        if name and mfid:
            mf_by_name[amfi_metrics.normalized(name)]={"name":name,"id":mfid}
    checks.append({
        "kind":"ter_mutual_fund_selector","source":mf_url,
        "sha256":hashlib.sha256(body).hexdigest(),"amcs":len(mf_by_name),
    })

    resolved={}
    for amc in amc_families:
        match=mf_by_name.get(amfi_metrics.normalized(amc))
        if match:resolved[amc]=match
        else:errors.append({"source":"AMFI TER selector","error":"No exact AMC selector match for "+amc})

    unresolved={family for values in amc_families.values() for family in values}
    for offset in range(months):
        if not unresolved:break
        label=_month_label(today,offset)
        for amc in sorted(resolved):
            wanted=amc_families[amc]&unresolved
            if not wanted:continue
            mf=resolved[amc]
            try:
                matched=set();page=1;pages=None;page_checks=[]
                while pages is None or page<=pages:
                    if page>30:
                        raise ValueError("AMFI AMC TER response exceeded 30-page safety bound")
                    url=amfi_metrics.BASE+"/api/populate-te-rdata-revised?"+urlencode({
                        "MF_ID":mf["id"],"Month":label,"strCat":"-1","strType":"1",
                        "page":page,"pageSize":10000,
                    })
                    body,payload=get_json(url)
                    records=payload.get("data",[]) if isinstance(payload,dict) else payload
                    if not isinstance(records,list):
                        raise ValueError("AMFI expense response changed format")
                    meta=payload.get("meta",{}) if isinstance(payload,dict) else {}
                    if pages is None:
                        pages=int(meta.get("totalPages") or meta.get("pageCount") or 1)
                        if pages<1:pages=1
                    mid=[r for r in records if isinstance(r,dict) and _is_mid_cap_category(r.get("SchemeCat_Desc"))]
                    rows.extend(mid)
                    found={
                        family for family in wanted
                        if any(amfi_metrics.normalized(r.get("Scheme_Name",""))==amfi_metrics.normalized(family)
                               for r in mid)
                    }
                    matched|=found
                    page_checks.append({
                        "page":page,"rows":len(records),"mid_cap_rows":len(mid),
                        "sha256":hashlib.sha256(body).hexdigest(),
                    })
                    if matched==wanted or not records:
                        break
                    page+=1
                unresolved-=matched
                checks.append({
                    "kind":"ter_mid_cap_by_amc","source":amfi_metrics.TER_PAGE,
                    "month":label,"amc":amc,"amfi_mf_name":mf["name"],
                    "reported_pages":pages,"pages_checked":page_checks,
                    "matched_families":sorted(matched),
                })
            except Exception as exc:
                errors.append({
                    "source":"AMFI TER · "+amc+" · "+label,
                    "error":(str(exc) or type(exc).__name__)[:300],
                })
            sleep_fn(0.25)

    checks.append({
        "kind":"ter_mid_cap_contract_summary",
        "queried_amcs":len(resolved),"target_families":len(unresolved)+len({
            family for values in amc_families.values() for family in values
        }-unresolved),
        "matched_families":len({
            family for values in amc_families.values() for family in values
        }-unresolved),
        "unmatched_families":sorted(unresolved),
        "contract":"one AMC x month; strCat=-1; strType=1; follow reported pagination with 30-page bound and stop after exact family match",
    })
    return rows,checks,errors


def collect(today=None):
    families=_family_map()
    errors=[];checks=[];aum_rows=[];ter_rows=[]
    try:
        aum_rows,aum_checks=_fetch_midcap_aum(families);checks.extend(aum_checks)
    except Exception as exc:
        errors.append({"source":"AMFI daily AUM","error":(str(exc) or type(exc).__name__)[:300]})
    try:
        ter_rows,ter_checks,ter_errors=_fetch_midcap_ter(families)
        checks.extend(ter_checks);errors.extend(ter_errors)
    except Exception as exc:
        errors.append({"source":"AMFI TER","error":(str(exc) or type(exc).__name__)[:300]})
    return report(aum_rows,ter_rows,source_checks=checks,source_errors=errors,today=today)
