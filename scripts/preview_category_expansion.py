"""Preview Small Cap + Mid Cap from one AMFI snapshot without production writes."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.categories import registry_payload
from tracker.category_catalogue import AMFI_NAV_URL,parse_catalogue


def build_preview(content,*,family_name,plan_type,option_type,legacy_parse_amfi,
                  coverage=None,today=None):
    catalogue=parse_catalogue(content,today=today)
    old={row["code"]:(row["date"],Decimal(str(row["nav"])))
         for row in legacy_parse_amfi(content.decode("utf-8-sig",errors="replace"))}
    new={row["code"]:(row["date"],Decimal(row["nav_raw"].replace(",","")))
         for row in catalogue["rows"] if row["category"]=="small-cap"}
    if old!=new:
        changed=sorted(code for code in old.keys()&new.keys() if old[code]!=new[code])
        raise ValueError("Small Cap parser parity failed: "+json.dumps({
            "legacy_only":sorted(old.keys()-new.keys()),
            "preview_only":sorted(new.keys()-old.keys()),
            "changed_values":changed,
        }))

    known_amcs={str(row.get("amc") or "").strip().casefold()
                for row in (coverage or {}).get("funds",[])}
    summaries={}
    for category in catalogue["category_ids"]:
        rows=[row for row in catalogue["rows"] if row["category"]==category]
        groups={(row["amc"],family_name(row["name"])) for row in rows}
        amcs=sorted({row["amc"] for row in rows})
        summaries[category]={
            "scheme_codes":len(rows),
            "candidate_fund_groups":len(groups),
            "amcs":len(amcs),
            "oldest_nav_date":min((r["date"] for r in rows),default=None),
            "latest_nav_date":max((r["date"] for r in rows),default=None),
            "plan_counts":dict(sorted(Counter(plan_type(r["plan_raw"],r["name"]) for r in rows).items())),
            "option_counts":dict(sorted(Counter(option_type(r["option_raw"],r["name"]) for r in rows).items())),
            "amcs_already_in_smallcap_coverage":[amc for amc in amcs if amc.casefold() in known_amcs],
            "candidate_families":[{"amc":amc,"family":family} for amc,family in sorted(groups)],
        }
    return {
        **catalogue,
        "prepared_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry":registry_payload(),
        "summary":summaries,
        "smallcap_parser_parity":True,
        "mid_cap_launch_ready":False,
        "existing_database_identity_check":"not_performed_in_feed_only_preview",
        "notes":[
            "This is an onboarding inventory, not a published second category.",
            "Candidate family groups use the existing normalizer; identities must be reconciled before import.",
            "All eligible plan/option codes are retained in the preview, including IDCW variants.",
            "Shared AMC counts identify possible collector reuse, not proven runtime/storage savings.",
            "No database, daily schedule, benchmark identity or public fund URL is changed.",
        ],
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--amfi-file",type=Path)
    source.add_argument("--fetch-amfi",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--coverage",type=Path,default=ROOT/"COVERAGE-AS-OF.json")
    args=parser.parse_args(argv)

    from tracker import providers
    if args.fetch_amfi:
        content,_,_=providers.fetch(AMFI_NAV_URL,archive=False,max_bytes=12*1024*1024)
    else:
        content=args.amfi_file.read_bytes()
    if not content:
        raise ValueError("AMFI snapshot is empty")
    coverage=json.loads(args.coverage.read_text(encoding="utf-8")) if args.coverage.exists() else None
    result=build_preview(
        content,family_name=providers.family_name,plan_type=providers.plan_type,
        option_type=providers.option_type,legacy_parse_amfi=providers.parse_amfi,
        coverage=coverage,
    )
    output=args.output.resolve()
    if output==providers.db.DATA or output.is_relative_to(providers.db.DATA):
        raise ValueError("Preview output must be outside the tracker data directory")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "prepared_at":result["prepared_at"],
        "source_sha256":result["source_sha256"],
        "source_bytes":result["source_bytes"],
        "smallcap_parser_parity":result["smallcap_parser_parity"],
        "mid_cap_launch_ready":result["mid_cap_launch_ready"],
        "production_writes":result["production_writes"],
        "summary":result["summary"],
        "rejected_rows":len(result["rejected_rows"]),
    },indent=2,ensure_ascii=False))
    return 0 if (
        not result["rejected_rows"]
        and result["summary"]["small-cap"]["scheme_codes"]
        and result["summary"]["mid-cap"]["scheme_codes"]
    ) else 1


if __name__=="__main__":
    raise SystemExit(main())
