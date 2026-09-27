"""Generate the staged Mid Cap source-coverage audit artifact."""
from __future__ import annotations

import argparse
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
    args=parser.parse_args(argv)
    db.init()
    result=collect()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "counts":result["counts"],
        "source_errors":result["source_errors"],
        "remaining_gates":result["remaining_gates"],
        "production_writes":result["production_writes"],
        "public_export_enabled":result["public_export_enabled"],
        "mid_cap_launch_ready":result["mid_cap_launch_ready"],
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
