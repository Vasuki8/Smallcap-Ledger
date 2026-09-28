"""Generate the explicit staged Mid Cap launch-readiness gate."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.midcap_launch_readiness import evaluate,markdown


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-audit",type=Path,required=True)
    p.add_argument("--ter",type=Path,required=True)
    p.add_argument("--benchmark",type=Path,required=True)
    p.add_argument("--portfolio",type=Path,required=True)
    p.add_argument("--history",type=Path,required=True)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    args=p.parse_args(argv)
    result=evaluate(
        load(args.source_audit),load(args.ter),load(args.benchmark),
        load(args.portfolio),load(args.history),
        public_surface_ready=False,
    )
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print(json.dumps({
        "actual":result["actual"],"required":result["required"],
        "remaining_to_data_gate":result["remaining_to_data_gate"],
        "data_ready":result["data_ready"],"launch_ready":result["launch_ready"],
        "blockers":result["blockers"],"recommended_action":result["recommended_action"],
    },indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
