"""Read-only Mid Cap identity audit before any staged import."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers
from tracker.categories import identity_issues

MFAPI=providers.MFAPI


def resolve_metadata(row,fetch_fn=providers.fetch):
    code=int(row["code"])
    url=f"{MFAPI}/{code}"
    body,_,typ=fetch_fn(url,archive=False,max_bytes=3*1024*1024)
    payload=json.loads(body.decode("utf-8","replace"))
    meta=payload.get("meta") or {}
    if int(meta.get("scheme_code") or 0)!=code:
        raise ValueError(f"MFAPI returned a different scheme code for {code}")
    scheme_name=str(meta.get("scheme_name") or "").strip()
    plan=providers.plan_type("",scheme_name)
    option=providers.option_type("",scheme_name)
    return {
        "code":code,
        "url":url,
        "scheme_name":scheme_name,
        "scheme_category":meta.get("scheme_category"),
        "scheme_type":meta.get("scheme_type"),
        "plan":plan,
        "option":option,
        "resolved":plan!="Unspecified" and option!="Other",
    }


def audit(preview,retained_rows,fetch_fn=providers.fetch):
    rows=[dict(r) for r in preview.get("rows",[]) if r.get("category")=="mid-cap"]
    retained=[dict(r) for r in retained_rows]
    retained_by_code={int(r["code"]):r for r in retained}
    retained_family={(str(r.get("family") or "").strip(),str(r.get("amc") or "").strip(),str(r.get("category") or "").strip())
                     for r in retained}

    code_collisions=[]
    family_collisions=[]
    proposals=[]
    unresolved=[]
    metadata_resolutions=[]

    for row in rows:
        official_family=" ".join(str(row.get("name") or "").split())
        plan=providers.plan_type(row.get("plan_raw"),official_family)
        option=providers.option_type(row.get("option_raw"),official_family)
        code=int(row["code"])
        existing=retained_by_code.get(code)
        if existing:
            code_collisions.append({
                "code":code,"candidate_category":"mid-cap",
                "retained_category":existing.get("category"),
                "retained_family":existing.get("family"),
                "candidate_family":official_family,
            })
        cross=[{"family":f,"amc":a,"category":cat} for f,a,cat in retained_family
               if f==official_family and (a!=row["amc"] or cat!="mid-cap")]
        if cross:
            family_collisions.append({
                "code":code,"candidate_family":official_family,
                "candidate_amc":row["amc"],"retained":cross,
            })

        resolution=None
        if plan=="Unspecified" or option=="Other":
            try:
                resolution=resolve_metadata(row,fetch_fn=fetch_fn)
                metadata_resolutions.append(resolution)
                if resolution["resolved"]:
                    plan=resolution["plan"];option=resolution["option"]
            except Exception as exc:
                resolution={"code":code,"resolved":False,"error":(str(exc) or type(exc).__name__)[:300]}
                metadata_resolutions.append(resolution)
        proposal={
            "code":code,"category":"mid-cap","family":official_family,"amc":row["amc"],
            "plan":plan,"option":option,"isin":row.get("isin"),
            "reinvestment_isin":row.get("reinvestment_isin"),
            "nav_date":row.get("date"),"nav_raw":row.get("nav_raw"),
            "source_label":row.get("source_label"),"source_line":row.get("source_line"),
        }
        proposals.append(proposal)
        if plan=="Unspecified" or option=="Other":
            unresolved.append({
                "code":code,"family":official_family,"amc":row["amc"],
                "plan":plan,"option":option,"resolution":resolution,
            })

    proposed_identity_issues=identity_issues([
        {"code":p["code"],"family":p["family"],"amc":p["amc"],"category":"mid-cap"}
        for p in proposals
    ])
    shared_amcs=sorted({p["amc"] for p in proposals}&{str(r.get("amc") or "") for r in retained})
    new_amcs=sorted({p["amc"] for p in proposals}-{str(r.get("amc") or "") for r in retained})
    ready=not(code_collisions or family_collisions or unresolved or proposed_identity_issues)
    return {
        "source_preview_sha256":preview.get("source_sha256"),
        "mid_cap_scheme_codes":len(proposals),
        "mid_cap_families":len({(p["amc"],p["family"]) for p in proposals}),
        "mid_cap_amcs":len({p["amc"] for p in proposals}),
        "shared_amcs":shared_amcs,
        "new_amcs":new_amcs,
        "code_collisions":code_collisions,
        "family_collisions":family_collisions,
        "identity_issues":proposed_identity_issues,
        "metadata_resolutions":metadata_resolutions,
        "unresolved_plan_option":unresolved,
        "proposals":proposals,
        "production_writes":0,
        "mid_cap_import_ready":ready,
        "notes":[
            "This audit is read-only and does not insert schemes or NAVs.",
            "Family identity preserves the official AMFI Scheme Name.",
            "Missing Plan/Option fields are resolved only from exact scheme-code metadata.",
            "A staged Mid Cap import remains blocked unless all collisions and unresolved identities are empty.",
        ],
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    preview=json.loads(args.preview.read_text(encoding="utf-8"))
    retained=db.rows("SELECT code,family,amc,category FROM schemes ORDER BY code")
    result=audit(preview,retained)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        key:result[key] for key in (
            "mid_cap_scheme_codes","mid_cap_families","mid_cap_amcs","new_amcs",
            "code_collisions","family_collisions","identity_issues",
            "unresolved_plan_option","production_writes","mid_cap_import_ready"
        )
    },indent=2,ensure_ascii=False))
    return 0 if result["mid_cap_import_ready"] else 1


if __name__=="__main__":
    raise SystemExit(main())
