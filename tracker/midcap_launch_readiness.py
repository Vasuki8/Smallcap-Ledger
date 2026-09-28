"""Explicit launch-readiness policy for the staged Mid Cap category."""
from __future__ import annotations

import math


POLICY={
    "aum_ratio":1.0,
    "direct_ter_ratio":0.90,
    "benchmark_ratio":0.90,
    "current_portfolio_ratio":0.80,
}


def _need(total,ratio):
    return int(math.ceil(total*ratio))


def evaluate(source_audit,ter_readiness,benchmark_readiness,portfolio_readiness,history_status,
             public_surface_ready=False):
    families=int(source_audit.get("counts",{}).get("families") or 0)
    if families<=0:
        raise ValueError("Mid Cap launch gate has no staged family count")

    required={
        "aum":_need(families,POLICY["aum_ratio"]),
        "direct_ter":_need(families,POLICY["direct_ter_ratio"]),
        "benchmark_identity":_need(families,POLICY["benchmark_ratio"]),
        "current_portfolio_evidence":_need(families,POLICY["current_portfolio_ratio"]),
    }
    actual={
        "aum":int(source_audit.get("counts",{}).get("aum") or 0),
        "direct_ter":int(ter_readiness.get("counts",{}).get("direct_ter") or 0),
        "benchmark_identity":int(benchmark_readiness.get("benchmark_identity") or 0),
        "current_portfolio_evidence":int(portfolio_readiness.get("current_portfolio_evidence") or 0),
        "current_complete_portfolios":int(portfolio_readiness.get("current_complete_portfolios") or 0),
    }
    nav_codes=int(history_status.get("nav_scheme_codes") or 0)
    scheme_codes=int(history_status.get("scheme_codes") or 0)
    history_failures=int(history_status.get("history_failed") or 0)
    nav_ready=scheme_codes>0 and nav_codes==scheme_codes and history_failures==0

    gates={
        "scheme_nav_identity":nav_ready,
        "aum":actual["aum"]>=required["aum"],
        "direct_ter":actual["direct_ter"]>=required["direct_ter"],
        "benchmark_identity":actual["benchmark_identity"]>=required["benchmark_identity"],
        "current_portfolio_evidence":actual["current_portfolio_evidence"]>=required["current_portfolio_evidence"],
        "source_fetch_health":not bool(source_audit.get("source_errors")),
        "category_aware_public_surface":bool(public_surface_ready),
    }
    data_gate_names=(
        "scheme_nav_identity","aum","direct_ter","benchmark_identity",
        "current_portfolio_evidence","source_fetch_health",
    )
    data_ready=all(gates[x] for x in data_gate_names)
    remaining={
        key:max(0,required[key]-actual[key])
        for key in ("aum","direct_ter","benchmark_identity","current_portfolio_evidence")
    }
    blockers=[name for name,value in gates.items() if not value]
    return {
        "staged_category":"mid-cap",
        "families":families,
        "policy":{
            "aum":"100% of staged families",
            "direct_ter":"at least 90% of staged families; remaining gaps must stay explicit",
            "benchmark_identity":"at least 90% exact first-party reported benchmark identity",
            "current_portfolio_evidence":"at least 80% current regulatory month-end evidence",
            "portfolio_completeness":"tracked separately; not a launch gate when partial coverage is explicitly labelled",
            "public_surface":"category-aware exporter/API/UI dry run must pass before the switch is enabled",
        },
        "required":required,
        "actual":actual,
        "remaining_to_data_gate":remaining,
        "history":{"scheme_codes":scheme_codes,"nav_scheme_codes":nav_codes,"history_failed":history_failures},
        "gates":gates,
        "data_ready":data_ready,
        "launch_ready":data_ready and bool(public_surface_ready),
        "blockers":blockers,
        "recommended_action":(
            "prepare_category_aware_public_surface_dry_run"
            if data_ready and not public_surface_ready
            else "continue_source_coverage"
            if not data_ready
            else "eligible_for_deliberate_launch"
        ),
        "public_export_enabled":False,
        "production_writes":0,
        "notes":[
            "These thresholds are a product-quality launch policy for this tracker, not a regulatory rule.",
            "Missing data remains visibly unavailable; thresholds never authorize inferred or third-party substitutions.",
            "The launch gate cannot itself enable Mid Cap. Publication requires a separate reviewed category-aware exporter/API/UI change.",
        ],
    }


def markdown(result):
    lines=[
        "# Mid Cap launch readiness","",
        f"Data ready: **{str(result['data_ready']).lower()}** · launch ready: **{str(result['launch_ready']).lower()}**.",'',
        "| Gate | Actual | Required | Pass? | Remaining |",
        "| --- | ---: | ---: | --- | ---: |",
    ]
    labels=(
        ("aum","AUM"),
        ("direct_ter","Direct TER"),
        ("benchmark_identity","Reported benchmark identity"),
        ("current_portfolio_evidence","Current portfolio evidence"),
    )
    for key,label in labels:
        lines.append(
            f"| {label} | {result['actual'][key]} | {result['required'][key]} | "
            f"{str(result['gates'][key]).lower()} | {result['remaining_to_data_gate'][key]} |"
        )
    lines.extend([
        "",
        f"- Scheme/NAV identity history gate: **{str(result['gates']['scheme_nav_identity']).lower()}** "
        f"({result['history']['nav_scheme_codes']} / {result['history']['scheme_codes']} codes; "
        f"{result['history']['history_failed']} history failures).",
        f"- Source-fetch health: **{str(result['gates']['source_fetch_health']).lower()}**.",
        f"- Category-aware public surface dry run: **{str(result['gates']['category_aware_public_surface']).lower()}**.",
        f"- Complete current portfolios (tracked, not a hard launch threshold): **{result['actual']['current_complete_portfolios']}**.",
        "",
        "## Current blockers","",
    ])
    lines.extend("- "+x for x in result["blockers"])
    lines.extend(["","## Policy",""])
    lines.extend(f"- {k}: {v}" for k,v in result["policy"].items())
    return "\n".join(lines)+"\n"
