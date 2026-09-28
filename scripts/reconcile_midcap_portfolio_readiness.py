"""Generate combined staged Mid Cap current portfolio readiness."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db
from tracker.midcap_portfolio_readiness import reconcile


def markdown(r):
    lines=[
        "# Mid Cap current portfolio readiness","",
        f"Current evidence: **{r['current_portfolio_evidence']} / {r['families']}** · complete current portfolios: **{r['current_complete_portfolios']}** · remaining: **{r['remaining']}**.",'',
        "| Family | AMC | As of | Positions | Scope | Complete? | Source |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in r["families_detail"]:
        lines.append("| "+" | ".join([
            row["family"],row["amc"],row["as_of"] or "Gap",
            str(row["positions_observed"]),row["scope"] or "Gap",
            str(row["complete"]).lower(),row["source"] or "Gap",
        ])+" |")
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--batch1",type=Path,required=True)
    p.add_argument("--batch2",type=Path,required=True)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv);db.init()
    staged={x["family"]:x["amc"] for x in db.rows(
        "SELECT DISTINCT family,amc FROM category_staged_schemes WHERE category='mid-cap'"
    )}
    r=reconcile(staged,
        json.loads(a.batch1.read_text(encoding="utf-8")),
        json.loads(a.batch2.read_text(encoding="utf-8")))
    r["built_at"]=db.now()
    a.json.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    a.markdown.write_text(markdown(r),encoding="utf-8")
    print(json.dumps({
        "families":r["families"],
        "current_portfolio_evidence":r["current_portfolio_evidence"],
        "current_complete_portfolios":r["current_complete_portfolios"],
        "remaining":r["remaining"],
        "production_writes":0,"public_export_enabled":False,
    },indent=2))

if __name__=="__main__":main()
