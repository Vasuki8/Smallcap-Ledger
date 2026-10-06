"""Fail publication when the current collection run is unsafe to publish."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['SMALLCAP_NO_SCHEDULER']='1'

from tracker import db, providers
from tracker.clock import india_today
from tracker.coverage import report as coverage_report

REQUIRED_JOBS=("nav","benchmark","metrics","documents")
HARD_FAILURES={"error","interrupted","running"}


def _age(day,today):
    if not day:return None
    return (today-date.fromisoformat(day)).days


def evaluate(started_at, *, today=None, max_age_days=7):
    if not started_at:
        raise ValueError("Collection start boundary is required")
    today=today or india_today()
    boundary=datetime.fromisoformat(started_at.replace("Z","+00:00"))
    if boundary.tzinfo is None:boundary=boundary.replace(tzinfo=timezone.utc)
    jobs={}
    blockers=[]
    degraded=[]
    for kind in REQUIRED_JOBS:
        row=db.one("""SELECT kind,started_at,finished_at,status,detail
          FROM jobs WHERE kind=? ORDER BY id DESC LIMIT 1""",(kind,))
        if row:
            stamp=datetime.fromisoformat(row["started_at"])
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
            if stamp<boundary:row=None
        jobs[kind]=row
        if not row:
            blockers.append(f"{kind}_job_missing")
            continue
        status=str(row.get("status") or "")
        if status in HARD_FAILURES:
            blockers.append(f"{kind}_job_{status}")
        elif status=="partial":
            # A partial collection may still be safe if the retained current
            # dataset below satisfies its publication invariants.
            degraded.append(f"{kind}_job_partial")
        elif status!="ok":
            blockers.append(f"{kind}_job_unknown_status")

    plans=db.one("SELECT COUNT(*) n FROM schemes")["n"]
    nav_codes=db.one("SELECT COUNT(DISTINCT code) n FROM nav")["n"]
    latest_nav=db.one("SELECT MAX(date) last FROM nav")["last"]
    nav_age=_age(latest_nav,today)
    if plans<=0:blockers.append("scheme_universe_empty")
    if nav_codes!=plans:blockers.append("nav_plan_coverage_incomplete")
    if nav_age is None or nav_age<0 or nav_age>max_age_days:
        blockers.append("latest_nav_stale_or_invalid")

    benchmark=db.one("""SELECT MAX(date) last,COUNT(*) points
      FROM benchmark WHERE name=?""",(providers.BENCHMARK,))
    benchmark_age=_age(benchmark["last"],today) if benchmark else None
    benchmark_fresh=bool(
        benchmark and benchmark["points"]
        and benchmark_age is not None
        and 0<=benchmark_age<=max_age_days
    )
    if not benchmark or not benchmark["points"]:
        blockers.append("primary_benchmark_missing")
    elif not benchmark_fresh:
        blockers.append("primary_benchmark_stale_or_invalid")

    # The benchmark endpoint is a read-only refresh of retained TRI history.
    # A transient transport error must not block an otherwise safe publication
    # when the retained primary benchmark already satisfies the freshness gate.
    # Missing/stale data remains fail-closed.
    if benchmark_fresh and "benchmark_job_error" in blockers:
        blockers.remove("benchmark_job_error")
        degraded.append("benchmark_job_error_using_fresh_retained_data")

    coverage=coverage_report()
    funds=coverage["counts"]["funds"]
    if funds<=0:blockers.append("fund_universe_empty")
    if coverage["counts"]["aum"]!=funds:blockers.append("aum_coverage_incomplete")
    if coverage["counts"]["fee"]!=funds:blockers.append("fee_coverage_incomplete")
    aum_latest=(coverage.get("record_dates",{}).get("aum") or {}).get("latest")
    aum_age=_age(aum_latest,today)
    if aum_age is None or aum_age<0 or aum_age>max_age_days:
        blockers.append("aum_stale_or_invalid")

    status="blocked" if blockers else ("degraded" if degraded else "ok")
    return {
        "status":status,
        "collection_started_at":started_at,
        "checked_for_date":today.isoformat(),
        "max_age_days":max_age_days,
        "jobs":jobs,
        "degraded":degraded,
        "blockers":blockers,
        "data":{
            "plans":plans,
            "nav_codes":nav_codes,
            "latest_nav_date":latest_nav,
            "latest_nav_age_days":nav_age,
            "primary_benchmark":providers.BENCHMARK,
            "primary_benchmark_latest_date":benchmark["last"] if benchmark else None,
            "primary_benchmark_age_days":benchmark_age,
            "funds":funds,
            "aum_funds":coverage["counts"]["aum"],
            "fee_funds":coverage["counts"]["fee"],
            "aum_latest_date":aum_latest,
            "aum_age_days":aum_age,
        },
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--started-at",default=os.environ.get("SMALLCAP_COLLECTION_STARTED_AT",""))
    parser.add_argument("--output",type=Path,default=ROOT/"deployment"/"publication-health.json")
    parser.add_argument("--max-age-days",type=int,default=7)
    args=parser.parse_args(argv)
    report=evaluate(args.started_at,max_age_days=args.max_age_days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if report["degraded"]:
        print("::warning title=Collection degraded::"+", ".join(report["degraded"]))
    if report["blockers"]:
        raise SystemExit("Publication blocked: "+", ".join(report["blockers"]))


if __name__=="__main__":
    main()
