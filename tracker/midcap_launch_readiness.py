"""Explicit launch policy backed by current, independently checked audit inputs."""
from __future__ import annotations

import math
from .midcap_audit_inputs import clock
from .midcap_portfolio_readiness import reconcile

POLICY = {"aum_ratio": 1.0, "direct_ter_ratio": 0.90,
          "benchmark_ratio": 0.90, "current_portfolio_ratio": 0.80}
# Every producing batch must be checked, not just its newly generated summary.
UPSTREAM_FILES = {
    "ter": tuple(f"MIDCAP-TER-FIRST-PARTY-BATCH{i}.json" for i in (1, 2)),
    "benchmark": tuple(f"MIDCAP-BENCHMARK-BATCH{i}.json" for i in (1, 2)),
    "portfolio": tuple(f"MIDCAP-PORTFOLIO-BATCH{i}.json" for i in range(1, 6)),
}
REQUIRED_INPUTS = ("source_audit", "ter", "benchmark", "portfolio", "history") + tuple(
    name for names in UPSTREAM_FILES.values() for name in names
)


def _need(total, ratio):
    return int(math.ceil(total * ratio))


def evaluate(source_audit, ter_readiness, benchmark_readiness, portfolio_readiness,
             history_status, public_surface_ready=False, *, now=None, input_health=None):
    now = clock(now)
    issues = []
    inputs = {}
    for name, value in zip(REQUIRED_INPUTS[:5], (
        source_audit, ter_readiness, benchmark_readiness, portfolio_readiness, history_status
    )):
        if not isinstance(value, dict):
            issues.append(name + ": invalid_report_shape")
            value = {}
        inputs[name] = value
    source, ter, benchmark, portfolio, history = (inputs[name] for name in REQUIRED_INPUTS[:5])

    def count(value, label, limit=None):
        if type(value) is not int or value < 0 or (limit is not None and value > limit):
            issues.append(label + ": invalid_count")
            return 0
        return value

    sc = source.get("counts") if isinstance(source.get("counts"), dict) else {}
    tc = ter.get("counts") if isinstance(ter.get("counts"), dict) else {}
    families = count(sc.get("families"), "families")
    staged = {}
    source_rows = source.get("families")
    if isinstance(source_rows, list):
        for row in source_rows:
            if not isinstance(row, dict) or not isinstance(row.get("family"), str) or not isinstance(row.get("amc"), str) or not row["family"].strip() or not row["amc"].strip():
                issues.append("source_audit: invalid_family")
                continue
            if row["family"] in staged:
                issues.append("source_audit: duplicate_family")
            staged[row["family"]] = row["amc"]
    universe_ok = families > 0 and len(staged) == families
    if not universe_ok:
        issues.append("source_audit: missing_or_mismatched_universe")
    for name, reported in (("ter", tc.get("families")), ("benchmark", benchmark.get("families")),
                           ("portfolio", portfolio.get("families"))):
        if type(reported) is not int or reported != families:
            issues.append(name + ": mismatched_universe")

    # Re-evaluate source dates rather than trust retained counts/current flags.
    fresh = None
    details = portfolio.get("families_detail")
    if portfolio.get("schema_version") != 2 or portfolio.get("inputs_healthy") is not True:
        issues.append("portfolio: unverified_reconciliation")
    if isinstance(details, list) and universe_ok:
        names = [row.get("family") if isinstance(row, dict) else None for row in details]
        if len(names) != families or any(not isinstance(name, str) for name in names) or set(names) != set(staged):
            issues.append("portfolio: duplicate_or_mismatched_families")
        else:
            for row in details:
                if row.get("amc") != staged[row["family"]] or row.get("status") not in ("recovered", "unavailable"):
                    issues.append("portfolio: invalid_family_status")
            batch = {"staged_category": "mid-cap", "built_at": portfolio.get("built_at"),
                     "results": [row for row in details if row.get("status") == "recovered"], "errors": []}
            fresh = reconcile(staged, batch, now=now)
            if not fresh["inputs_healthy"]:
                issues.append("portfolio: invalid_source_evidence")
            if portfolio.get("portfolio_expected_as_of") != fresh["portfolio_expected_as_of"]:
                issues.append("portfolio: reporting_period_changed")
    else:
        issues.append("portfolio: missing_source_rows")
    current = fresh["current_portfolio_evidence"] if fresh else 0
    complete = fresh["current_complete_portfolios"] if fresh else 0
    if portfolio.get("current_portfolio_evidence") != current or portfolio.get("current_complete_portfolios") != complete:
        issues.append("portfolio: summary_counts_do_not_match_current_rows")

    actual = {
        "aum": count(sc.get("aum"), "aum", families),
        "direct_ter": count(tc.get("direct_ter"), "direct_ter", families),
        "benchmark_identity": count(benchmark.get("benchmark_identity"), "benchmark_identity", families),
        "current_portfolio_evidence": current, "current_complete_portfolios": complete,
    }
    required = {
        "aum": _need(families, POLICY["aum_ratio"]),
        "direct_ter": _need(families, POLICY["direct_ter_ratio"]),
        "benchmark_identity": _need(families, POLICY["benchmark_ratio"]),
        "current_portfolio_evidence": _need(families, POLICY["current_portfolio_ratio"]),
    }
    nav_codes = count(history.get("nav_scheme_codes"), "nav_scheme_codes")
    scheme_codes = count(history.get("scheme_codes"), "scheme_codes")
    failures = count(history.get("history_failed"), "history_failed")
    if sc.get("scheme_codes") != scheme_codes:
        issues.append("history: mismatched_scheme_universe")
    checks = input_health if isinstance(input_health, list) else []
    names = [row.get("name") for row in checks if isinstance(row, dict)]
    verified = (len(names) == len(REQUIRED_INPUTS) and all(isinstance(name,str) for name in names) and set(names) == set(REQUIRED_INPUTS)
                and all(isinstance(row, dict) and row.get("ok") is True for row in checks))
    if not verified:
        issues.append("audit_inputs: missing_failed_or_retained_artifact")
    source_errors = source.get("source_errors")
    if not isinstance(source_errors, list):
        issues.append("source_audit: missing_source_health")
    gates = {
        "scheme_nav_identity": universe_ok and scheme_codes > 0 and nav_codes == scheme_codes and failures == 0,
        **{key: universe_ok and actual[key] >= target for key, target in required.items()},
        "source_fetch_health": isinstance(source_errors, list) and not source_errors,
        "audit_input_integrity": verified and not issues,
        "category_aware_public_surface": public_surface_ready is True,
    }
    data_ready = all(value for key, value in gates.items() if key != "category_aware_public_surface")
    return {
        "schema_version": 2, "built_at": now.isoformat(), "evaluated_at": now.isoformat(),
        "staged_category": "mid-cap", "families": families,
        "portfolio_expected_as_of": fresh["portfolio_expected_as_of"] if fresh else None,
        "policy": {
            "aum": "100% of staged families",
            "direct_ter": "at least 90% of staged families; remaining gaps stay explicit",
            "benchmark_identity": "at least 90% exact first-party reported benchmark identity",
            "current_portfolio_evidence": "at least 80% current regulatory month-end evidence",
            "portfolio_completeness": "tracked separately; partial records are not relabelled",
            "public_surface": "category-aware exporter/API/UI dry run must pass separately",
        },
        "required": required, "actual": actual,
        "remaining_to_data_gate": {key: max(0, target - actual[key]) for key, target in required.items()},
        "history": {"scheme_codes": scheme_codes, "nav_scheme_codes": nav_codes, "history_failed": failures},
        "input_health": checks, "input_issues": list(dict.fromkeys(issues)), "gates": gates,
        "data_ready": data_ready, "launch_ready": data_ready and public_surface_ready is True,
        "blockers": [key for key, passed in gates.items() if not passed],
        "recommended_action": "repair_audit_inputs" if issues else (
            "continue_source_coverage" if not data_ready else
            "prepare_category_aware_public_surface_dry_run" if public_surface_ready is not True else
            "eligible_for_deliberate_launch"),
        "public_export_enabled": False, "production_writes": 0,
        "notes": [
            "Thresholds are product-quality policy, not regulatory rules, and are unchanged.",
            "Current portfolio counts are independently re-evaluated from source evidence at this clock.",
            "Benchmark identity is not benchmark-series availability; the dry run must show the correct series or its absence.",
            "No silent Small Cap comparator, inferred values or automatic public-category promotion is authorized.",
        ],
    }


def markdown(result):
    lines = ["# Mid Cap launch readiness", "", f"Evaluated: {result['evaluated_at']}", "",
             f"Data ready: **{str(result['data_ready']).lower()}** · launch ready: **{str(result['launch_ready']).lower()}**.", "",
             "| Gate | Actual | Required | Pass? | Remaining |", "| --- | ---: | ---: | --- | ---: |"]
    for key, label in (("aum", "AUM"), ("direct_ter", "Direct TER"),
                       ("benchmark_identity", "Reported benchmark identity"),
                       ("current_portfolio_evidence", "Current portfolio evidence")):
        lines.append(f"| {label} | {result['actual'][key]} | {result['required'][key]} | {str(result['gates'][key]).lower()} | {result['remaining_to_data_gate'][key]} |")
    lines += ["", "## Current blockers", ""] + ["- " + key for key in result["blockers"]]
    lines += ["", "## Input integrity", ""] + ["- " + issue for issue in result["input_issues"]]
    lines += ["", "## Policy", ""] + [f"- {k}: {v}" for k, v in result["policy"].items()]
    lines += ["", "## Notes", ""] + ["- " + note for note in result["notes"]]
    return "\n".join(lines) + "\n"
