"""Current fee selection shared by API and coverage reporting."""
from __future__ import annotations

FEE_METRICS=("ter","ter_observed","base_expense_ratio","expense_ratio")
FEE_PRIORITY={name:i for i,name in enumerate(FEE_METRICS)}


def select_fee(records):
    """Choose the newest dated fee; metric type only breaks same-date ties."""
    candidates=[]
    if isinstance(records,dict):
        candidates=list(records.values())
    else:
        candidates=list(records or [])
    candidates=[
        r for r in candidates
        if r and r.get("metric") in FEE_PRIORITY and r.get("as_of")
    ]
    if not candidates:return None
    return max(
        candidates,
        key=lambda r:(
            str(r.get("as_of") or ""),
            -FEE_PRIORITY[r["metric"]],
            str(r.get("observed_at") or ""),
            int(r.get("id") or 0),
        ),
    )
