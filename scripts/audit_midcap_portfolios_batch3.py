"""Generate staged Mid Cap structured current portfolio audit batch 3."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_portfolio_batch3 import collect


def markdown(result):
    lines=[
        "# Mid Cap structured current portfolio evidence — batch 3","",
        f"Prepared: {result['built_at']}","",
        f"Expected month-end: **{result['portfolio_expected_as_of']}** · targets: **{result['targets']}** · recovered: **{result['recovered']}** · failed: **{result['failed']}**.",'',
        "| Family | AMC | As of | Positions | Complete? | Source |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in result["results"]:
        lines.append("| "+" | ".join([
            row["family"],row["amc"],row["as_of"],str(row["positions_observed"]),
            str(row["complete"]).lower(),row["source"],
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
        "portfolio_expected_as_of":result["portfolio_expected_as_of"],
        "targets":result["targets"],"recovered":result["recovered"],"failed":result["failed"],
        "errors":result["errors"],"production_writes":0,"public_export_enabled":False,
    },indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
