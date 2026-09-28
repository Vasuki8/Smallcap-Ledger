"""Combine staged Mid Cap current portfolio evidence across read-only batches."""
from __future__ import annotations


def reconcile(staged_families,*batches):
    merged={}
    errors=[]
    for batch in batches:
        for row in batch.get("results",[]) or []:
            family=row.get("family")
            if not family:continue
            current=merged.get(family)
            if current is None or (
                bool(row.get("complete")),int(row.get("positions_observed") or 0)
            )>(
                bool(current.get("complete")),int(current.get("positions_observed") or 0)
            ):
                merged[family]=row
        errors.extend(batch.get("errors",[]) or [])
    rows=[]
    for family,amc in sorted(staged_families.items()):
        evidence=merged.get(family)
        rows.append({
            "family":family,"amc":amc,
            "as_of":evidence.get("as_of") if evidence else None,
            "positions_observed":int(evidence.get("positions_observed") or 0) if evidence else 0,
            "scope":evidence.get("scope") if evidence else None,
            "complete":bool(evidence.get("complete")) if evidence else False,
            "source":evidence.get("source") if evidence else None,
        })
    current=sum(bool(x["as_of"]) for x in rows)
    complete=sum(bool(x["as_of"] and x["complete"]) for x in rows)
    return {
        "families":len(rows),
        "current_portfolio_evidence":current,
        "current_complete_portfolios":complete,
        "remaining":len(rows)-current,
        "families_detail":rows,
        "remaining_families":[x["family"] for x in rows if not x["as_of"]],
        "batch_errors":errors,
        "production_writes":0,
        "public_export_enabled":False,
        "notes":[
            "This combines read-only evidence only; no Mid Cap portfolio or holding is inserted into the live database.",
            "When batches overlap, a complete snapshot is preferred; otherwise the larger exact named-position set is retained.",
            "Current evidence and complete portfolio coverage are reported separately.",
        ],
    }
