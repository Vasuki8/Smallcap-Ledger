"""Combine staged Mid Cap benchmark evidence across read-only batches."""
from __future__ import annotations

from copy import deepcopy


def reconcile(staged_families,*batches):
    merged={}
    errors=[]
    for batch in batches:
        for row in batch.get("results",[]) or []:
            family=row.get("family")
            if family and family not in merged:
                merged[family]=row
        errors.extend(batch.get("errors",[]) or [])
    rows=[]
    for family,amc in sorted(staged_families.items()):
        evidence=merged.get(family)
        rows.append({
            "family":family,"amc":amc,
            "benchmark_identity":evidence.get("primary_benchmark") if evidence else None,
            "reported_benchmarks":evidence.get("reported_benchmarks") if evidence else [],
            "source":evidence.get("source") if evidence else None,
            "source_sha256":evidence.get("source_sha256") if evidence else None,
            "source_evidence":deepcopy(evidence) if evidence else None,
            "source_data_as_of":evidence.get("source_data_as_of") if evidence else None,
            "observed_at":evidence.get("observed_at") if evidence else None,
        })
    covered=sum(bool(x["benchmark_identity"]) for x in rows)
    return {
        "families":len(rows),"benchmark_identity":covered,
        "remaining":len(rows)-covered,
        "families_detail":rows,
        "remaining_families":[x["family"] for x in rows if not x["benchmark_identity"]],
        "batch_errors":errors,
        "production_writes":0,"public_export_enabled":False,
        "notes":[
            "This combines read-only evidence only; no Mid Cap benchmark metric is inserted into the live metrics table.",
            "A family is covered only when an exact first-party page explicitly reports its benchmark.",
        ],
    }
