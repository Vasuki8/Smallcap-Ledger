"""Generate staged Mid Cap TER gap classification from retained audit evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.midcap_ter_gap_audit import classify,markdown


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit",type=Path,required=True)
    parser.add_argument("--json",type=Path,required=True)
    parser.add_argument("--markdown",type=Path,required=True)
    args=parser.parse_args(argv)
    source=json.loads(args.source_audit.read_text(encoding="utf-8"))
    result=classify(source)
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "gap_families":result["gap_families"],
        "classification_counts":result["classification_counts"],
        "production_writes":result["production_writes"],
        "public_export_enabled":result["public_export_enabled"],
    },indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
