"""Generate staged Mid Cap first-party benchmark audit batch 2."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_benchmark_batch2 import collect


def markdown(result):
    lines=[
        "# Mid Cap benchmark identity audit — batch 2","",
        f"Prepared: {result['built_at']}","",
        f"Targets: **{result['targets']}** · recovered: **{result['recovered']}** · failed: **{result['failed']}**.",'',
        "| Family | AMC | Primary benchmark | Source |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["results"]:
        lines.append(f"| {row['family']} | {row['amc']} | {row['primary_benchmark']} | {row['source']} |")
    if result["errors"]:
        lines+=["","## Errors",""]+[f"- {x['family']}: {x['error']}" for x in result["errors"]]
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv);db.init();r=collect()
    a.json.parent.mkdir(parents=True,exist_ok=True);a.markdown.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    a.markdown.write_text(markdown(r),encoding="utf-8")
    print(json.dumps({"targets":r["targets"],"recovered":r["recovered"],"failed":r["failed"],"errors":r["errors"],"production_writes":0,"public_export_enabled":False},indent=2))

if __name__=="__main__":main()
