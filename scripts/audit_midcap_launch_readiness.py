"""Generate a blocked-or-ready launch report from this run's verified inputs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker.midcap_audit_inputs import clock, load_audit
from tracker.midcap_launch_readiness import UPSTREAM_FILES, evaluate, markdown


def from_files(paths, *, now=None, started_at=None):
    now = clock(now)
    reports, checks = {}, []
    for name in ("source_audit", "ter", "benchmark", "portfolio", "history"):
        report, check = load_audit(paths[name], now=now, started_at=started_at)
        reports[name] = report
        checks.append(dict(check, name=name))
    # Check producing batches too: a summary can be new even when its inputs are old.
    for parent, filenames in UPSTREAM_FILES.items():
        for filename in filenames:
            _, check = load_audit(Path(paths[parent]).parent / filename, now=now, started_at=started_at)
            checks.append(dict(check, name=filename))
    return evaluate(*(reports[name] for name in ("source_audit", "ter", "benchmark", "portfolio", "history")),
                    public_surface_ready=False, now=now, input_health=checks)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-audit", "ter", "benchmark", "portfolio", "history"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--audit-started-at", default=os.environ.get("MIDCAP_AUDIT_STARTED_AT"))
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = from_files({name:getattr(args,name) for name in ("source_audit", "ter", "benchmark", "portfolio", "history")},
                        started_at=args.audit_started_at)
    for path in (args.json, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    # Even missing or malformed inputs produce a fresh, explicitly blocked report.
    args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({key:report[key] for key in ("actual", "required", "remaining_to_data_gate",
        "data_ready", "launch_ready", "blockers", "input_issues", "recommended_action")}, indent=2))


if __name__ == "__main__":
    main()
