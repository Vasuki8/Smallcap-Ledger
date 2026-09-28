"""Generate staged Mid Cap current portfolio audit batch 5."""
from __future__ import annotations

import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_portfolio_batch5 import collect


def markdown(result):
    lines=[
        "# Mid Cap current portfolio evidence — batch 5","",
        f"Prepared: {result['built_at']}","",
        f"Expected month-end: **{result['portfolio_expected_as_of']}** · targets: **{result['targets']}** · recovered: **{result['recovered']}** · failed: **{result['failed']}**.",'',
        "| Family | AMC | As of | Positions | Scope | Complete? | Source |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in result["results"]:
        lines.append("| "+" | ".join([
            row["family"],row["amc"],row["as_of"],str(row["positions_observed"]),
            row["scope"],str(row["complete"]).lower(),row["source"],
        ])+" |")
    if result["errors"]:
        lines+=["","## Errors",""]+[f"- {x['family']}: {x['error']}" for x in result["errors"]]
    lines+=["","## Notes",""]+["- "+x for x in result["notes"]]
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv);db.init();r=collect()
    a.json.parent.mkdir(parents=True,exist_ok=True);a.markdown.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    a.markdown.write_text(markdown(r),encoding="utf-8")
    print(json.dumps({
        "targets":r["targets"],"recovered":r["recovered"],"failed":r["failed"],
        "errors":r["errors"],"production_writes":0,"public_export_enabled":False
    },indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
