"""Generate freshness-safe staged Mid Cap portfolio readiness."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker.midcap_audit_inputs import clock, load_audit
from tracker.midcap_portfolio_readiness import reconcile


def from_files(staged, paths, *, now=None, started_at=None):
    now = clock(now)
    batches, checks = [], []
    for path in paths:
        batch, check = load_audit(path, now=now, started_at=started_at)
        batches.append(batch)
        checks.append(check)
    return reconcile(staged, *batches, now=now, input_reports=checks)


def markdown(report):
    lines = ["# Mid Cap current portfolio readiness", "",
             f"Evaluated: {report['evaluated_at']} · expected month-end: **{report['portfolio_expected_as_of']}**.", "",
             f"Current evidence: **{report['current_portfolio_evidence']} / {report['families']}** · complete current portfolios: **{report['current_complete_portfolios']}** · remaining: **{report['remaining']}**.", "",
             "| Family | As of | Freshness | Positions | Complete? | Observed at | Source |",
             "| --- | --- | --- | ---: | --- | --- | --- |"]
    for row in report["families_detail"]:
        fields = [row["family"], row["as_of"] or "Unavailable", row["freshness_status"],
                  str(row["positions_observed"]), str(row["complete"]).lower(),
                  row.get("observed_at") or "Unavailable", row.get("source") or "Unavailable"]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in fields) + " |")
    lines += ["", "## Input integrity", "", f"All supplied inputs verified: **{str(report['inputs_healthy']).lower()}**."]
    lines += [f"- Batch {issue['batch']}: {issue['reason']}" for issue in report["input_issues"]]
    lines += ["", "Source hashes, observation times and excluded/alternate evidence remain in the JSON report."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for i in range(1, 6):
        parser.add_argument(f"--batch{i}", type=Path, required=i <= 2)
    parser.add_argument("--audit-started-at", default=os.environ.get("MIDCAP_AUDIT_STARTED_AT"))
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    from tracker import db
    db.init()
    staged = {row["family"]: row["amc"] for row in db.rows(
        "SELECT DISTINCT family,amc FROM category_staged_schemes WHERE category='mid-cap'")}
    paths = [getattr(args, f"batch{i}") for i in range(1, 6) if getattr(args, f"batch{i}") is not None]
    # A supplied-but-missing optional batch is an error, never silently omitted.
    report = from_files(staged, paths, started_at=args.audit_started_at)
    for path in (args.json, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "portfolio_expected_as_of", "current_portfolio_evidence", "current_complete_portfolios",
        "remaining", "inputs_healthy", "input_issues", "production_writes", "public_export_enabled")}, indent=2))


if __name__ == "__main__":
    main()
