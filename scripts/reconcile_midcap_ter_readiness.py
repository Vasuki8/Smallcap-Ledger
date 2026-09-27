"""Generate reconciled staged Mid Cap TER readiness."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.midcap_ter_readiness import reconcile,markdown

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-audit",type=Path,required=True)
    p.add_argument("--first-party",type=Path,required=True)
    p.add_argument("--first-party-extra",type=Path)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    args=p.parse_args(argv)
    first=json.loads(args.first_party.read_text(encoding="utf-8"))
    if args.first_party_extra and args.first_party_extra.exists():
        extra=json.loads(args.first_party_extra.read_text(encoding="utf-8"))
        first={**first,"results":[*(first.get("results") or []),*(extra.get("results") or [])]}
    result=reconcile(
        json.loads(args.source_audit.read_text(encoding="utf-8")),
        first,
    )
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({"counts":result["counts"],"remaining_families":result["remaining_families"],
                      "production_writes":0,"public_export_enabled":False},indent=2))

if __name__=="__main__":
    main()
