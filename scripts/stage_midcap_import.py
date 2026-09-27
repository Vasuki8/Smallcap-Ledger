"""Import an audited category proposal into isolated staging tables only."""
from __future__ import annotations

import argparse
from decimal import Decimal,InvalidOperation
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db


def stage(audit,preview):
    if not audit.get("mid_cap_import_ready"):
        raise ValueError("Mid Cap identity audit is not import-ready")
    if audit.get("production_writes")!=0:
        raise ValueError("Identity audit must be read-only")
    source_hash=str(preview.get("source_sha256") or "")
    if not source_hash or audit.get("source_preview_sha256")!=source_hash:
        raise ValueError("Audit/preview source hash mismatch")
    proposals=list(audit.get("proposals") or [])
    preview_rows={int(r["code"]):r for r in preview.get("rows",[]) if r.get("category")=="mid-cap"}
    if len(proposals)!=len(preview_rows):
        raise ValueError("Audit proposal count does not match Mid Cap preview")

    live_codes={int(r["code"]) for r in db.rows("SELECT code FROM schemes")}
    candidate_codes={int(p["code"]) for p in proposals}
    overlap=sorted(live_codes&candidate_codes)
    if overlap:
        raise ValueError(f"Staged scheme codes collide with live schemes: {overlap[:10]}")

    observed=db.now()
    with db.connect() as conn:
        for proposal in proposals:
            code=int(proposal["code"]);row=preview_rows.get(code)
            if not row:
                raise ValueError(f"Missing preview evidence for staged code {code}")
            if proposal.get("category")!="mid-cap":
                raise ValueError(f"Unexpected staged category for code {code}")
            try:
                nav=Decimal(str(row.get("nav_raw") or "").replace(",",""))
            except (InvalidOperation,ValueError) as exc:
                raise ValueError(f"Invalid staged NAV for code {code}") from exc
            if not nav.is_finite() or nav<=0:
                raise ValueError(f"Invalid staged NAV for code {code}")
            metadata={
                "source_label":proposal.get("source_label"),
                "source_line":proposal.get("source_line"),
                "preview_prepared_at":preview.get("prepared_at"),
                "audit_method":"reviewed_identity_gate",
            }
            conn.execute("""INSERT INTO category_staged_schemes(
                code,category,name,family,amc,plan,option,isin,reinvestment_isin,
                source_sha256,source_line,first_seen,last_seen,metadata_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET
                  category=excluded.category,name=excluded.name,family=excluded.family,
                  amc=excluded.amc,plan=excluded.plan,option=excluded.option,
                  isin=excluded.isin,reinvestment_isin=excluded.reinvestment_isin,
                  source_sha256=excluded.source_sha256,source_line=excluded.source_line,
                  last_seen=excluded.last_seen,metadata_json=excluded.metadata_json""",
                (code,"mid-cap",row["name"],proposal["family"],proposal["amc"],
                 proposal["plan"],proposal["option"],proposal.get("isin"),
                 proposal.get("reinvestment_isin"),source_hash,proposal.get("source_line"),
                 observed,observed,json.dumps(metadata,separators=(",",":"))))
            conn.execute("""INSERT INTO category_staged_nav(code,date,value,source_sha256,observed_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(code,date) DO UPDATE SET
                  value=excluded.value,source_sha256=excluded.source_sha256,
                  observed_at=excluded.observed_at""",
                (code,row["date"],float(nav),source_hash,observed))

    staged=db.one("""SELECT COUNT(*) schemes,COUNT(DISTINCT family) families,
        COUNT(DISTINCT amc) amcs FROM category_staged_schemes WHERE category='mid-cap'""")
    nav=db.one("""SELECT COUNT(*) observations,MIN(date) first_date,MAX(date) last_date
        FROM category_staged_nav n JOIN category_staged_schemes s ON s.code=n.code
        WHERE s.category='mid-cap'""")
    live=db.one("SELECT COUNT(*) schemes FROM schemes")
    return {
        "staged_category":"mid-cap",
        "source_sha256":source_hash,
        "staged_schemes":staged["schemes"],
        "staged_families":staged["families"],
        "staged_amcs":staged["amcs"],
        "staged_nav_observations":nav["observations"],
        "staged_nav_first_date":nav["first_date"],
        "staged_nav_last_date":nav["last_date"],
        "live_scheme_rows":live["schemes"],
        "public_category_stage":"staged",
        "public_export_enabled":False,
        "observed_at":observed,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit",type=Path,required=True)
    parser.add_argument("--preview",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args(argv)
    db.init()
    result=stage(
        json.loads(args.audit.read_text(encoding="utf-8")),
        json.loads(args.preview.read_text(encoding="utf-8")),
    )
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
