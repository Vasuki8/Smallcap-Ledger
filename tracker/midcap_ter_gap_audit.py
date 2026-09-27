"""Classify staged Mid Cap TER gaps from retained source-coverage evidence."""
from __future__ import annotations

from collections import defaultdict


def classify(source_audit):
    families={row["family"]:row for row in source_audit.get("families",[])}
    checks=[row for row in source_audit.get("source_checks",[])
            if row.get("kind")=="ter_mid_cap_by_amc"]
    by_amc=defaultdict(list)
    for row in checks:
        by_amc[row.get("amc")].append(row)
    errors=list(source_audit.get("source_errors") or [])
    error_text="\n".join(str(x) for x in errors)

    rows=[]
    for family,row in sorted(families.items()):
        if row.get("direct_ter_available"):
            continue
        amc=row.get("amc")
        evidence=sorted(by_amc.get(amc,[]),key=lambda x:x.get("month") or "",reverse=True)
        months=[x.get("month") for x in evidence if x.get("month")]
        total_rows=sum(sum(int(p.get("rows") or 0) for p in x.get("pages_checked",[])) for x in evidence)
        mid_rows=sum(sum(int(p.get("mid_cap_rows") or 0) for p in x.get("pages_checked",[])) for x in evidence)
        exact_matches=sum(len(x.get("matched_families") or []) for x in evidence)
        has_error=amc and amc in error_text

        if has_error:
            classification="amfi_source_error"
            next_action="retry_official_amfi_before_fallback"
        elif evidence and total_rows==0 and mid_rows==0 and exact_matches==0:
            classification="amfi_exact_amc_category_no_rows"
            next_action="seek_exact_first_party_amc_ter"
        elif evidence and mid_rows>0 and exact_matches==0:
            classification="amfi_midcap_rows_identity_unmatched"
            next_action="review_amfi_scheme_name_identity"
        elif evidence:
            classification="amfi_unresolved"
            next_action="review_amfi_evidence"
        else:
            classification="no_amfi_evidence"
            next_action="rerun_source_audit"

        rows.append({
            "family":family,
            "amc":amc,
            "classification":classification,
            "next_action":next_action,
            "months_checked":months,
            "amfi_rows":total_rows,
            "amfi_mid_cap_rows":mid_rows,
            "exact_family_matches":exact_matches,
            "source_checks":evidence,
        })

    counts={}
    for row in rows:
        counts[row["classification"]]=counts.get(row["classification"],0)+1
    return {
        "built_at":source_audit.get("built_at"),
        "staged_category":"mid-cap",
        "official_ter_category_selector":next((
            {
                "category_id":x.get("category_id"),
                "category_label":x.get("category_label"),
            }
            for x in source_audit.get("source_checks",[])
            if x.get("kind")=="ter_mid_cap_contract_summary"
        ),None),
        "gap_families":len(rows),
        "classification_counts":counts,
        "families":rows,
        "production_writes":0,
        "public_export_enabled":False,
        "notes":[
            "This classifier consumes retained audit evidence only and performs no network fetches or financial-data writes.",
            "amfi_exact_amc_category_no_rows means the exact AMFI AMC selector and verified Mid Cap category were queried but returned zero TER rows for the checked months.",
            "A zero-row AMFI result is not converted into a TER value and does not justify reusing another scheme's expense ratio.",
        ],
    }


def markdown(result):
    lines=[
        "# Mid Cap TER gap classification","",
        f"Prepared: {result.get('built_at') or 'unknown'}","",
        f"Unresolved Direct TER families: **{result['gap_families']}**.",'',
        "| Family | AMC | Classification | Months checked | AMFI rows | Mid Cap rows | Next action |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in result["families"]:
        lines.append("| "+" | ".join([
            str(row["family"]).replace("|","\\|"),
            str(row["amc"]).replace("|","\\|"),
            row["classification"],
            ", ".join(row["months_checked"]) or "None",
            str(row["amfi_rows"]),
            str(row["amfi_mid_cap_rows"]),
            row["next_action"],
        ])+" |")
    lines.extend(["","## Classification counts",""])
    for key,value in sorted(result["classification_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["","## Notes",""])
    for note in result["notes"]:
        lines.append("- "+note)
    return "\n".join(lines)+"\n"
