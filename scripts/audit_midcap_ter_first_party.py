"""Run read-only first-party Mid Cap TER recovery batch."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_ter_first_party import collect


def markdown(result):
    lines=[
        "# Mid Cap first-party TER recovery batch 1","",
        f"Prepared: {result['built_at']}","",
        f"Targets: **{result['targets']}** · recovered: **{result['recovered']}** · failed: **{result['failed']}**.",'',
        "| Family | AMC | Status | As of | Direct TER | Regular TER | Source | Identity |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    by_family={r["family"]:r for r in result["results"]}
    errors={r["family"]:r for r in result["errors"]}
    for family in sorted(set(by_family)|set(errors)):
        if family in by_family:
            row=by_family[family]
            identity=", ".join(f"{k}={v}" for k,v in row.get("identity",{}).items())
            lines.append("| "+" | ".join([
                family,row["amc"],"recovered",row["as_of"],
                f"{row['direct_ter']:.4f}%",f"{row['regular_ter']:.4f}%",
                row["source"],identity,
            ])+" |")
        else:
            row=errors[family]
            lines.append("| "+" | ".join([
                family,row.get("amc",""),"failed","","","","",row["error"],
            ])+" |")
    lines.extend(["","## Notes",""])
    lines.extend("- "+x for x in result.get("notes",[]))
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    args=p.parse_args(argv)
    db.init()
    result=collect()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "targets":result["targets"],"recovered":result["recovered"],"failed":result["failed"],
        "production_writes":result["production_writes"],
        "public_export_enabled":result["public_export_enabled"],
        "errors":result["errors"],
    },indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
