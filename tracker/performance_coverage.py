"""Read-only historical NAV and benchmark-series coverage audit.

This module audits retained evidence only. It never computes or stores replacement
returns, forward-fills benchmark values, fetches new data, or changes UI behavior.
"""
from __future__ import annotations

import bisect
import re
from collections import Counter
from datetime import date

from . import analytics, db, providers


HORIZONS=(1,3,5)
LARGE_GAP_DAYS=7
BSE_SERIES="BSE 250 SmallCap TRI"


def _compact(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())


def benchmark_identity(value):
    """Map only explicitly total-return benchmark identities to canonical series."""
    raw=str(value or "").strip()
    compact=_compact(raw)
    explicit_tri=("tri" in compact or "totalreturn" in compact)
    smallcap250=("smallcap250" in compact or "250smallcap" in compact or "smallcapindex250" in compact)
    canonical=None
    family=None
    if smallcap250 and "nifty" in compact:
        family="Nifty Smallcap 250"
        if explicit_tri:canonical=providers.BENCHMARK
    elif smallcap250 and "bse" in compact:
        family="BSE 250 SmallCap"
        if explicit_tri:canonical=BSE_SERIES
    return {
        "reported":raw or None,
        "family":family,
        "explicit_total_return":bool(explicit_tri),
        "canonical_tri_series":canonical,
    }


def _series_stats(points):
    if not points:
        return {
            "first":None,"last":None,"observations":0,
            "gap_count_gt_7d":0,"max_gap_days":None,"largest_gaps":[],
        }
    dates=[date.fromisoformat(p[0]) for p in points]
    gaps=[]
    for i in range(1,len(dates)):
        days=(dates[i]-dates[i-1]).days
        if days>LARGE_GAP_DAYS:
            gaps.append({"from":dates[i-1].isoformat(),"to":dates[i].isoformat(),"days":days})
    largest=sorted(gaps,key=lambda x:(x["days"],x["to"]),reverse=True)[:5]
    return {
        "first":points[0][0],
        "last":points[-1][0],
        "observations":len(points),
        "gap_count_gt_7d":len(gaps),
        "max_gap_days":max((x["days"] for x in gaps),default=0),
        "largest_gaps":largest,
    }


def _horizon_eligibility(points, years):
    """Mirror displayed dated-return anchor tolerance without calculating a return."""
    if not points:
        return {"eligible":False,"reason":"no_series","target":None,"anchor":None,"anchor_lag_days":None}
    dates=[date.fromisoformat(p[0]) for p in points]
    end=dates[-1]
    target=analytics.shift_years(end,years)
    i=bisect.bisect_right(dates,target)-1
    if i<0:
        return {
            "eligible":False,"reason":"history_starts_after_target",
            "target":target.isoformat(),"anchor":None,"anchor_lag_days":None,
        }
    lag=(target-dates[i]).days
    if lag>7:
        return {
            "eligible":False,"reason":"no_observation_within_7d_before_target",
            "target":target.isoformat(),"anchor":dates[i].isoformat(),"anchor_lag_days":lag,
        }
    return {
        "eligible":True,"reason":None,"target":target.isoformat(),
        "anchor":dates[i].isoformat(),"anchor_lag_days":lag,
    }


def _horizons(points):
    return {f"{years}Y":_horizon_eligibility(points,years) for years in HORIZONS}


def _overlap(nav,benchmark):
    if not nav or not benchmark:return []
    b={p[0]:p[1] for p in benchmark}
    return [[d,v,b[d]] for d,v in nav if d in b]


def _overlap_points(overlap):
    return [[p[0],1.0] for p in overlap]


def _latest_benchmark_metric(family):
    return db.one(
        """SELECT value,as_of,unit,source,observed_at
           FROM metrics WHERE family=? AND metric='benchmark'
           ORDER BY as_of DESC,observed_at DESC,id DESC LIMIT 1""",
        (family,),
    )


def _benchmark_cache():
    names=[r["name"] for r in db.rows("SELECT DISTINCT name FROM benchmark ORDER BY name")]
    return {
        name:[[r["date"],float(r["value"])] for r in db.rows(
            "SELECT date,value FROM benchmark WHERE name=? ORDER BY date",(name,))]
        for name in names
    }


def _comparison_status(identity,required_points,required_overlap):
    if not identity["reported"]:
        return "benchmark_identity_missing"
    if not identity["explicit_total_return"]:
        return "benchmark_identity_not_explicit_tri"
    if not identity["canonical_tri_series"]:
        return "benchmark_identity_unmapped"
    if not required_points:
        return "reported_tri_series_missing"
    if len(required_overlap)<2:
        return "reported_tri_overlap_insufficient"
    return "reported_tri_ready"


def _plan_issues(row):
    issues=[]
    if row["display_returns_supported"]:
        for label,info in row["nav"]["horizons"].items():
            if not info["eligible"]:issues.append("nav_"+label.lower()+"_return_unavailable")
    if row["nav"]["gap_count_gt_7d"]:
        issues.append("nav_large_gap")
    status=row["benchmark"]["status"]
    if status!="reported_tri_ready":issues.append(status)
    if row["benchmark"]["website_default_mismatch"]:
        issues.append("website_default_benchmark_mismatch")
    if row["benchmark"]["required_series"]["gap_count_gt_7d"]:
        issues.append("benchmark_series_large_gap")
    if row["display_returns_supported"] and status=="reported_tri_ready":
        for label,info in row["benchmark"]["overlap_horizons"].items():
            if not info["eligible"]:issues.append("benchmark_"+label.lower()+"_overlap_unavailable")
    return issues


def report():
    """Audit every retained NAV plan against its reported benchmark identity/history."""
    benchmark_points=_benchmark_cache()
    default_points=benchmark_points.get(providers.BENCHMARK,[])
    default_stats=_series_stats(default_points)
    plans=[]
    families={}

    schemes=db.rows("""SELECT code,name,family,amc,plan,option,history_checked,history_status
                       FROM schemes ORDER BY family,plan,option,code""")
    for scheme in schemes:
        nav=[[r["date"],float(r["value"])] for r in db.rows(
            "SELECT date,value FROM nav WHERE code=? ORDER BY date",(scheme["code"],))]
        nav_stats=_series_stats(nav)
        nav_stats["horizons"]=_horizons(nav)
        metric=_latest_benchmark_metric(scheme["family"])
        identity=benchmark_identity(metric["value"] if metric else None)
        identity.update({
            "as_of":metric["as_of"] if metric else None,
            "source":metric["source"] if metric else None,
            "unit":metric["unit"] if metric else None,
        })

        required_name=identity["canonical_tri_series"]
        required=benchmark_points.get(required_name,[]) if required_name else []
        required_overlap=_overlap(nav,required)
        default_overlap=_overlap(nav,default_points)
        required_stats=_series_stats(required)
        required_overlap_stats=_series_stats(_overlap_points(required_overlap))
        default_overlap_stats=_series_stats(_overlap_points(default_overlap))
        required_overlap_horizons=_horizons(_overlap_points(required_overlap))
        default_overlap_horizons=_horizons(_overlap_points(default_overlap))
        status=_comparison_status(identity,required,required_overlap)

        row={
            "code":scheme["code"],
            "name":scheme["name"],
            "family":scheme["family"],
            "amc":scheme["amc"],
            "plan":scheme["plan"],
            "option":scheme["option"],
            "display_returns_supported":scheme["option"]=="Growth",
            "history_checked":scheme.get("history_checked"),
            "history_status":scheme.get("history_status"),
            "nav":nav_stats,
            "benchmark":{
                "reported_identity":identity,
                "status":status,
                "required_series":{
                    "name":required_name,
                    "available":bool(required),
                    **required_stats,
                },
                "overlap":{
                    **required_overlap_stats,
                    "observations":len(required_overlap),
                },
                "overlap_horizons":required_overlap_horizons,
                "website_default_series":{
                    "name":providers.BENCHMARK,
                    "available":bool(default_points),
                    **default_stats,
                },
                "website_default_overlap":{
                    **default_overlap_stats,
                    "observations":len(default_overlap),
                },
                "website_default_overlap_horizons":default_overlap_horizons,
                "website_default_mismatch":bool(
                    required_name and required_name!=providers.BENCHMARK
                ),
            },
        }
        row["issues"]=_plan_issues(row)
        plans.append(row)

        family=families.setdefault(scheme["family"],{
            "family":scheme["family"],
            "amc":scheme["amc"],
            "reported_benchmark":identity,
            "plan_count":0,
            "growth_plan_count":0,
            "issue_codes":set(),
            "growth_horizons":{f"{y}Y":{"eligible":0,"ineligible":0} for y in HORIZONS},
            "benchmark_horizons":{f"{y}Y":{"eligible":0,"ineligible":0} for y in HORIZONS},
        })
        family["plan_count"]+=1
        family["issue_codes"].update(row["issues"])
        if row["display_returns_supported"]:
            family["growth_plan_count"]+=1
            for label,info in nav_stats["horizons"].items():
                family["growth_horizons"][label]["eligible" if info["eligible"] else "ineligible"]+=1
            for label,info in required_overlap_horizons.items():
                family["benchmark_horizons"][label]["eligible" if info["eligible"] else "ineligible"]+=1

    family_rows=[]
    for family in families.values():
        family["issue_codes"]=sorted(family["issue_codes"])
        family_rows.append(family)
    family_rows.sort(key=lambda x:x["family"].lower())

    issue_counts=Counter(issue for row in plans for issue in row["issues"])
    growth=[row for row in plans if row["display_returns_supported"]]
    explicit_tri=[row for row in growth if row["benchmark"]["reported_identity"]["explicit_total_return"]]
    relevant_ready=[row for row in growth if row["benchmark"]["status"]=="reported_tri_ready"]

    repair_priorities=[]
    bse_affected=sorted({row["family"] for row in growth
                         if row["benchmark"]["reported_identity"]["canonical_tri_series"]==BSE_SERIES
                         and not row["benchmark"]["required_series"]["available"]})
    if bse_affected:
        repair_priorities.append({
            "priority":1,
            "code":"collect_bse_250_smallcap_tri",
            "actionable":True,
            "affected_funds":bse_affected,
            "affected_growth_plans":sum(
                row["family"] in bse_affected for row in growth
            ),
            "reason":"Funds explicitly report BSE 250 SmallCap TRI, but no matching historical TRI series is retained.",
        })
    nontri=sorted({row["family"] for row in growth
                   if row["benchmark"]["status"]=="benchmark_identity_not_explicit_tri"})
    if nontri:
        repair_priorities.append({
            "priority":2,
            "code":"verify_non_tri_benchmark_identity",
            "actionable":True,
            "affected_funds":nontri,
            "affected_growth_plans":sum(row["family"] in nontri for row in growth),
            "reason":"Reported benchmark identity is present but does not explicitly establish a total-return series.",
        })
    nav_gap_funds=sorted({row["family"] for row in growth if row["nav"]["gap_count_gt_7d"]})
    if nav_gap_funds:
        repair_priorities.append({
            "priority":3,
            "code":"review_nav_history_gaps",
            "actionable":True,
            "affected_funds":nav_gap_funds,
            "affected_growth_plans":sum(bool(row["nav"]["gap_count_gt_7d"]) for row in growth),
            "reason":"Growth NAV histories contain one or more gaps longer than seven calendar days.",
        })

    return {
        "built_at":db.now(),
        "website_default_benchmark":providers.BENCHMARK,
        "benchmark_series":{
            name:_series_stats(points) for name,points in benchmark_points.items()
        },
        "summary":{
            "plans":len(plans),
            "growth_plans":len(growth),
            "families":len(family_rows),
            "reported_benchmark_identity_families":sum(bool(x["reported_benchmark"]["reported"]) for x in family_rows),
            "explicit_tri_growth_plans":len(explicit_tri),
            "reported_tri_ready_growth_plans":len(relevant_ready),
            "website_default_mismatch_growth_plans":sum(
                row["benchmark"]["website_default_mismatch"] for row in growth
            ),
            "growth_return_eligibility":{
                f"{y}Y":sum(row["nav"]["horizons"][f"{y}Y"]["eligible"] for row in growth)
                for y in HORIZONS
            },
            "reported_benchmark_overlap_eligibility":{
                f"{y}Y":sum(
                    row["benchmark"]["status"]=="reported_tri_ready"
                    and row["benchmark"]["overlap_horizons"][f"{y}Y"]["eligible"]
                    for row in growth
                ) for y in HORIZONS
            },
            "issue_counts":dict(sorted(issue_counts.items())),
        },
        "repair_priorities":repair_priorities,
        "families":family_rows,
        "plans":plans,
        "notes":[
            "Return eligibility mirrors the website's seven-day anchor tolerance but does not calculate or store a return.",
            "Benchmark overlap uses exact common dates only; no forward-fill or interpolation is performed.",
            "A reported benchmark identity is not treated as historical TRI coverage unless the retained identity explicitly establishes a total-return index.",
            "website_default_mismatch flags plans whose explicit reported TRI benchmark differs from the website's current global default comparison series.",
            "This audit is read-only and uses retained NAV, benchmark and metric evidence only.",
        ],
    }


def markdown(audit):
    def esc(value):
        return str(value or "").replace("|","\\|").replace("\n"," ")
    summary=audit["summary"]
    lines=[
        "# Historical performance and benchmark coverage audit","",
        f"Prepared: {audit['built_at']}","",
        "**Read-only:** retained NAV/benchmark evidence only; no forward-fill, return fabrication, source fetch or UI change.","",
        "## Summary","",
        f"- Plans: **{summary['plans']}**; Growth plans eligible for displayed returns: **{summary['growth_plans']}**.",
        f"- Reported benchmark identity families: **{summary['reported_benchmark_identity_families']} / {summary['families']}**.",
        f"- Explicit reported TRI identities on Growth plans: **{summary['explicit_tri_growth_plans']}**.",
        f"- Growth plans with the relevant reported TRI series and at least two exact overlapping dates: **{summary['reported_tri_ready_growth_plans']}**.",
        f"- Growth plans where the explicit reported TRI differs from the website's current default **{esc(audit['website_default_benchmark'])}**: **{summary['website_default_mismatch_growth_plans']}**.","",
        "| Horizon | NAV return eligible Growth plans | Relevant benchmark overlap eligible Growth plans |",
        "| --- | ---: | ---: |",
    ]
    for y in HORIZONS:
        label=f"{y}Y"
        lines.append(f"| {label} | {summary['growth_return_eligibility'][label]} | {summary['reported_benchmark_overlap_eligibility'][label]} |")

    if audit["repair_priorities"]:
        lines.extend(["","## Repair priorities","",
                      "| Priority | Repair | Affected funds | Affected Growth plans | Reason |",
                      "| ---: | --- | ---: | ---: | --- |"])
        for p in audit["repair_priorities"]:
            lines.append("| "+" | ".join([
                str(p["priority"]),esc(p["code"]),str(len(p["affected_funds"])),
                str(p["affected_growth_plans"]),esc(p["reason"])
            ])+" |")
        lines.extend(["","### Affected funds",""])
        for p in audit["repair_priorities"]:
            lines.append(f"- **{esc(p['code'])}:** "+", ".join(esc(x) for x in p["affected_funds"]))

    lines.extend(["","## Per-plan audit","",
                  "| Fund / plan | NAV range / obs | 1Y | 3Y | 5Y | Reported benchmark | Required TRI series | Exact overlap | Issues |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"])
    for row in audit["plans"]:
        nav=row["nav"];b=row["benchmark"];identity=b["reported_identity"]
        h=lambda label:("yes" if nav["horizons"][label]["eligible"] else "no")
        overlap=b["overlap"]
        lines.append("| "+" | ".join([
            esc(f"{row['family']} · {row['plan']} · {row['option']} · {row['code']}"),
            esc(f"{nav['first']} → {nav['last']} · {nav['observations']}"),
            h("1Y") if row["display_returns_supported"] else "n/a",
            h("3Y") if row["display_returns_supported"] else "n/a",
            h("5Y") if row["display_returns_supported"] else "n/a",
            esc(identity["reported"] or "Gap"),
            esc(identity["canonical_tri_series"] or "Not established"),
            esc(f"{overlap['first'] or 'Gap'} → {overlap['last'] or 'Gap'} · {overlap['observations']}"),
            esc(", ".join(row["issues"]) or "none"),
        ])+" |")

    lines.extend(["","## Notes",""])
    for note in audit["notes"]:lines.append("- "+esc(note))
    lines.append("")
    return "\n".join(lines)
