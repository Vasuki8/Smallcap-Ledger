"""Generate the staged Mid Cap source-coverage audit artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_source_coverage import collect


def markdown(result):
    c=result["counts"]
    lines=[
        "# Mid Cap source coverage audit","",
        f"Prepared: {result['built_at']}","",
        "**Read-only staged-category audit. No Mid Cap metric, portfolio, document, scheme, NAV, API or public-page writes are performed.**","",
        f"Families: **{c['families']}** · scheme codes: **{c['scheme_codes']}** · AUM: **{c['aum']}** · Direct TER: **{c['direct_ter']}** · reported benchmark identity: **{c['benchmark_identity']}** · current portfolio: **{c['portfolio_current']}** · all required evidence: **{c['all_required_source_evidence']}**.","",
        f"AUM evidence mode: **{result.get('aum_evidence',{}).get('mode','unknown')}**. A retained last-verified AUM set preserves original reporting dates and never clears a live source-fetch error.","",
        f"Mid Cap registry stage: **{result['stage']}** · public export enabled: **{str(result['public_export_enabled']).lower()}** · launch ready: **{str(result['mid_cap_launch_ready']).lower()}**.","",
        "| Family | AMC | AUM | Direct TER | Benchmark identity | Current portfolio | AMC source candidates | Gaps |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in result["families"]:
        aum=row.get("aum")
        ter=row.get("ter") or {}
        direct=ter.get("direct")
        benchmark=row.get("benchmark_identity")
        portfolio=row.get("portfolio")
        lines.append("| "+" | ".join([
            str(row["family"]).replace("|","\\|"),
            str(row["amc"]).replace("|","\\|"),
            (f"₹ {aum['value']:.2f} Cr · {aum['as_of']}" if aum else "Gap"),
            (f"{direct['value']:.4f}% · {ter['as_of']}" if direct else "Gap"),
            (f"{benchmark['value']} · {benchmark['as_of']}" if benchmark else "Gap"),
            (f"{portfolio['as_of']} · {portfolio['positions']} positions · {'complete' if portfolio['complete'] else 'partial'}"
             if row.get("portfolio_current") and portfolio else "Gap"),
            str(len(row.get("amc_source_candidates") or [])),
            ", ".join(row.get("coverage_gaps") or []) or "None",
        ])+" |")
    lines.extend(["","## Remaining gates",""])
    for gate in result.get("remaining_gates") or []:
        lines.append("- "+gate)
    if result.get("source_errors"):
        lines.extend(["","## Source fetch errors",""])
        for error in result["source_errors"]:
            lines.append(f"- {error['source']}: {error['error']}")
    lines.extend(["","## Notes",""])
    for note in result.get("notes") or []:
        lines.append("- "+note)
    return "\n".join(lines)+"\n"


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json",type=Path,required=True)
    parser.add_argument("--markdown",type=Path,required=True)
    parser.add_argument("--aum-last-verified",type=Path,default=ROOT/"docs"/"MIDCAP-AUM-LAST-VERIFIED.json")
    args=parser.parse_args(argv)
    db.init()
    retained=None
    retained_sha256=None
    if args.aum_last_verified.exists():
        raw=args.aum_last_verified.read_bytes()
        retained_sha256=hashlib.sha256(raw).hexdigest()
        retained=json.loads(raw)
    result=collect(retained_aum=retained)
    result["aum_evidence"]["retained_artifact_path"]=str(args.aum_last_verified.relative_to(ROOT) if args.aum_last_verified.is_relative_to(ROOT) else args.aum_last_verified)
    result["aum_evidence"]["retained_artifact_sha256"]=retained_sha256
    if (result["aum_evidence"]["mode"]=="current_fetch"
            and result["counts"]["aum"]==result["counts"]["families"]):
        rows=[]
        for row in result["families"]:
            evidence=row.get("aum")
            if not evidence:
                continue
            rows.append({
                "schemeName":evidence["scheme_name"],
                "dailyAUM":evidence["value"],
                "navDate":evidence["as_of"],
                "unit":evidence["unit"],
                "source":evidence["source"],
            })
        payload={
            "schema_version":1,
            "retained_from_audit_built_at":result["built_at"],
            "source":"https://www.amfiindia.com/otherdata/fund-performance",
            "evidence_kind":"last_verified_mid_cap_aum",
            "rows":rows,
            "notes":[
                "This file preserves the last fully verified staged Mid Cap AUM set when the live AMFI AUM fetch is temporarily unavailable.",
                "Its original reporting dates and values must not be retimestamped.",
                "Using this retained evidence never clears source fetch errors or source_fetch_health.",
            ],
        }
        args.aum_last_verified.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        result["aum_evidence"]["retained_artifact_sha256"]=hashlib.sha256(args.aum_last_verified.read_bytes()).hexdigest()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "counts":result["counts"],
        "aum_evidence":result["aum_evidence"],
        "source_errors":result["source_errors"],
        "remaining_gates":result["remaining_gates"],
        "production_writes":result["production_writes"],
        "public_export_enabled":result["public_export_enabled"],
        "mid_cap_launch_ready":result["mid_cap_launch_ready"],
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
