"""Category-aware readiness summary without mutating retained data."""
from __future__ import annotations

from copy import deepcopy

from .categories import REGISTRY,identity_issues


def _coverage_counts(rows):
    return {
        "funds":len(rows),
        "aum":sum(bool(r.get("aum")) for r in rows),
        "fee":sum(bool(r.get("fee")) for r in rows),
        "ter":sum(bool(r.get("ter")) for r in rows),
        "base_expense_ratio":sum(bool(r.get("base_expense_ratio")) for r in rows),
        "portfolio":sum(bool(r.get("portfolio")) for r in rows),
        "portfolio_complete":sum(bool(r.get("portfolio_complete")) for r in rows),
        "portfolio_fresh":sum(bool(r.get("portfolio_fresh")) for r in rows),
        "portfolio_fresh_complete":sum(bool(r.get("portfolio_complete")) and bool(r.get("portfolio_fresh")) for r in rows),
        "benchmark_identity":sum(bool(r.get("benchmark")) for r in rows),
    }


def report(records,coverage):
    schemes=[dict(x) for x in records]
    coverage=deepcopy(coverage or {"funds":[],"counts":{}})
    issues=identity_issues(schemes)
    mapping={}
    for row in schemes:
        family=str(row.get("family") or "").strip()
        category=row.get("category")
        amc=str(row.get("amc") or "").strip()
        if not family or category not in REGISTRY or not amc:
            continue
        value=(category,amc)
        if family in mapping and mapping[family]!=value:
            continue
        mapping[family]=value

    unmatched=[]
    rows_by_category={key:[] for key in REGISTRY}
    for row in coverage.get("funds",[]):
        family=str(row.get("family") or "").strip()
        mapped=mapping.get(family)
        if not mapped:
            unmatched.append(family)
            continue
        rows_by_category[mapped[0]].append(row)
    for family in unmatched:
        issues.append({"code":"coverage_family_unmapped","family":family})

    by_category={}
    for category,spec in REGISTRY.items():
        category_schemes=[r for r in schemes if r.get("category")==category]
        by_category[category]={
            "label":spec.label,
            "stage":spec.stage,
            "publication_enabled":spec.stage=="live",
            "schemes":len(category_schemes),
            "families":len({(r.get("amc"),r.get("family")) for r in category_schemes}),
            "counts":_coverage_counts(rows_by_category[category]),
        }

    gates=[]
    mid=by_category["mid-cap"]
    if mid["stage"]!="live":
        gates.append("mid_cap_registry_stage_is_staged")
    if mid["schemes"]==0:
        gates.append("mid_cap_not_imported")
    if issues:
        gates.append("category_identity_or_coverage_mapping_issues")
    return {
        "built_at":coverage.get("built_at"),
        "global_counts":deepcopy(coverage.get("counts",{})),
        "by_category":by_category,
        "identity_issues":issues,
        "remaining_expansion_gates":gates,
        "mid_cap_launch_ready":not gates,
        "notes":[
            "Category readiness is read-only and does not import schemes or alter public URLs.",
            "Coverage is assigned only through retained scheme identity, never inferred from fund names.",
            "A staged category is never eligible for public export.",
        ],
    }
