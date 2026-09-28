"""Generate staged Mid Cap first-party benchmark audit batch 1."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_benchmark_first_party import collect


def markdown(result):
    lines=[
        "# Mid Cap benchmark identity audit — batch 1","",
        f"Prepared: {result['built_at']}","",
        f"Targets: **{result['targets']}** · recovered: **{result['recovered']}** · failed: **{result['failed']}** · staged families: **{result['families']}**.",'',
        "| Family | AMC | Primary benchmark | Source data as of | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in result["results"]:
        lines.append("| "+" | ".join([
            row["family"],row["amc"],row["primary_benchmark"],
            row.get("source_data_as_of") or "Observed current page",
            row["source"],
        ])+" |")
    if result["errors"]:
        lines.extend(["","## Errors",""])
        lines.extend(f"- {x['family']}: {x['error']}" for x in result["errors"])
    lines.extend(["","## Notes",""])
    lines.extend("- "+x for x in result["notes"])
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    args=p.parse_args(argv)
    db.init();result=collect()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "targets":result["targets"],"recovered":result["recovered"],"failed":result["failed"],
        "production_writes":0,"public_export_enabled":False,"errors":result["errors"],
    },indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
