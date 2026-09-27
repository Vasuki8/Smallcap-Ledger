"""Reconcile staged Mid Cap TER readiness across AMFI and verified first-party evidence."""
from __future__ import annotations


def reconcile(source_audit, first_party):
    families={row["family"]:dict(row) for row in source_audit.get("families",[])}
    fp={row["family"]:row for row in first_party.get("results",[]) if row.get("status")=="recovered"}
    rows=[]
    for family,row in sorted(families.items()):
        evidence="amfi" if row.get("direct_ter_available") else None
        direct=None
        regular=None
        as_of=None
        source=None
        identity=None
        if row.get("ter"):
            direct=(row["ter"].get("direct") or {}).get("value")
            regular=(row["ter"].get("regular") or {}).get("value")
            as_of=row["ter"].get("as_of")
            source=row["ter"].get("source")
        if not evidence and family in fp:
            item=fp[family]
            evidence="first_party_amc"
            direct=item.get("direct_ter")
            regular=item.get("regular_ter")
            as_of=item.get("as_of")
            source=item.get("source")
            identity=item.get("identity")
        rows.append({
            "family":family,
            "amc":row.get("amc"),
            "direct_ter_available":evidence is not None and direct is not None,
            "direct_ter":direct,
            "regular_ter":regular,
            "as_of":as_of,
            "source":source,
            "evidence_channel":evidence,
            "identity":identity,
        })
    counts={
        "families":len(rows),
        "direct_ter":sum(bool(r["direct_ter_available"]) for r in rows),
        "amfi":sum(r["evidence_channel"]=="amfi" for r in rows),
        "first_party_amc":sum(r["evidence_channel"]=="first_party_amc" for r in rows),
        "remaining":sum(not r["direct_ter_available"] for r in rows),
    }
    return {
        "built_at":source_audit.get("built_at"),
        "staged_category":"mid-cap",
        "counts":counts,
        "families":rows,
        "remaining_families":[r["family"] for r in rows if not r["direct_ter_available"]],
        "production_writes":0,
        "public_export_enabled":False,
        "notes":[
            "This reconciles read-only evidence only; no Mid Cap TER is inserted into the live metrics table.",
            "AMFI evidence is preferred when available; exact first-party AMC evidence fills only families missing from the AMFI feed.",
            "First-party evidence is accepted only from the dedicated audit that required exact staged family identity and a complete Regular/Direct pair.",
        ],
    }


def markdown(result):
    c=result["counts"]
    lines=[
        "# Mid Cap TER readiness reconciliation","",
        f"Prepared: {result.get('built_at') or 'unknown'}","",
        f"Direct TER evidence: **{c['direct_ter']} / {c['families']}** · AMFI: **{c['amfi']}** · first-party AMC: **{c['first_party_amc']}** · remaining: **{c['remaining']}**.",'',
        "| Family | AMC | Direct TER | Regular TER | As of | Evidence | Source |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in result["families"]:
        lines.append("| "+" | ".join([
            row["family"],row["amc"] or "",
            f"{row['direct_ter']:.4f}%" if row["direct_ter"] is not None else "Gap",
            f"{row['regular_ter']:.4f}%" if row["regular_ter"] is not None else "Gap",
            row["as_of"] or "Gap",
            row["evidence_channel"] or "Gap",
            row["source"] or "Gap",
        ])+" |")
    lines.extend(["","## Remaining families",""])
    for family in result["remaining_families"]:
        lines.append("- "+family)
    lines.extend(["","## Notes",""])
    for note in result["notes"]:
        lines.append("- "+note)
    return "\n".join(lines)+"\n"
