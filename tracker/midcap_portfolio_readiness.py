"""Combine staged portfolios by reporting freshness without discarding evidence."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import re
from urllib.parse import urlsplit

from .coverage import expected_portfolio_as_of
from .midcap_audit_inputs import clock, timestamp

SCHEMA_VERSION = 2


def _report_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid_reporting_date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid_reporting_date") from exc


def _validate_row(row, staged, now, built):
    if not isinstance(row, dict):
        raise ValueError("invalid_row_shape")
    family = row.get("family")
    if not isinstance(family, str) or family not in staged:
        raise ValueError("unknown_family")
    if row.get("amc") != staged[family]:
        raise ValueError("amc_mismatch")
    if row.get("status") != "recovered":
        raise ValueError("unsuccessful_evidence")
    count = row.get("positions_observed")
    if type(count) is not int or count < 5:
        raise ValueError("invalid_position_count")
    if type(row.get("complete")) is not bool:
        raise ValueError("invalid_completeness")
    day = _report_day(row.get("as_of"))
    if day > now.date():
        raise ValueError("future_reporting_date")
    if (day + timedelta(days=1)).day != 1 or day >= now.date().replace(day=1):
        raise ValueError("not_closed_month_end")
    source = row.get("source")
    try:
        parsed = urlsplit(source) if isinstance(source, str) else None
        if not parsed or parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError("invalid_source")
    except ValueError as exc:
        raise ValueError("invalid_source") from exc
    if not isinstance(row.get("source_sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", row["source_sha256"]):
        raise ValueError("missing_source_hash")
    observed = timestamp(row.get("observed_at"))
    if observed > now or observed > built or observed.date() < day:
        raise ValueError("invalid_observation_time")
    return day


def reconcile(staged_families, *batches, now=None, input_reports=None):
    """Count only valid current-month evidence; preserve stale/alternate records.

    A current-reporting-month partial supersedes an older complete portfolio.
    Completeness/position count break ties only for the SAME reporting date.
    New summary timestamps never replace source observation timestamps.
    """
    now = clock(now)
    expected = expected_portfolio_as_of(now.date())
    if not isinstance(staged_families, dict) or not staged_families or any(
        not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
        for k, v in staged_families.items()
    ):
        raise ValueError("invalid staged family universe")
    if input_reports is not None and (
        not isinstance(input_reports, list) or len(input_reports) != len(batches)
        or any(not isinstance(report, dict) for report in input_reports)
    ):
        raise ValueError("input reports must match batches")
    merged, errors, issues, excluded = {}, [], [], []
    for index, batch in enumerate(batches):
        reason = None
        built = None
        if not isinstance(batch, dict) or not isinstance(batch.get("results"), list):
            reason = "invalid_batch_shape"
        elif batch.get("staged_category") != "mid-cap":
            reason = "wrong_batch_category"
        elif batch.get("status") in ("failed", "error", "cancelled", "interrupted"):
            reason = "failed_batch"
        else:
            try:
                built = timestamp(batch.get("built_at"))
                if built > now:
                    raise ValueError("future_batch_timestamp")
            except ValueError as exc:
                reason = str(exc)
        if input_reports is not None and input_reports[index].get("ok") is not True:
            reason = input_reports[index].get("error") or "unverified_artifact"
        if reason:
            issues.append({"batch": index, "reason": reason})
            excluded.append({"batch": index, "reason": reason, "evidence": deepcopy(batch)})
            continue
        batch_errors = batch.get("errors", [])
        if not isinstance(batch_errors, list):
            issues.append({"batch": index, "reason": "invalid_error_list"})
        else:
            errors.extend(deepcopy(batch_errors))
        for row in batch["results"]:
            try:
                _validate_row(row, staged_families, now, built)
            except ValueError as exc:
                excluded.append({"batch": index, "reason": str(exc), "evidence": deepcopy(row)})
                issues.append({"batch": index, "reason": str(exc)})
                continue
            family = row["family"]
            current = merged.get(family)
            rank = lambda item: (item["as_of"], item["complete"], item["positions_observed"])
            if current is None or rank(row) > rank(current):
                if current is not None:
                    excluded.append({"reason": "superseded_snapshot", "evidence": deepcopy(current)})
                merged[family] = deepcopy(row)
            else:
                excluded.append({"batch": index, "reason": "alternate_snapshot", "evidence": deepcopy(row)})
    rows = []
    for family, amc in sorted(staged_families.items()):
        evidence = merged.get(family)
        row = deepcopy(evidence) if evidence else {
            "family": family, "amc": amc, "status": "unavailable", "as_of": None,
            "positions_observed": 0, "scope": None, "complete": False, "source": None,
        }
        row["current"] = bool(evidence and evidence["as_of"] >= expected)
        row["freshness_status"] = "current" if row["current"] else "stale" if evidence else "unavailable"
        rows.append(row)
    current = sum(row["current"] for row in rows)
    return {
        "schema_version": SCHEMA_VERSION, "staged_category": "mid-cap",
        "built_at": now.isoformat(), "evaluated_at": now.isoformat(),
        "portfolio_expected_as_of": expected, "families": len(rows),
        "current_portfolio_evidence": current,
        "current_complete_portfolios": sum(row["current"] and row["complete"] for row in rows),
        "remaining": len(rows) - current, "families_detail": rows,
        "remaining_families": [row["family"] for row in rows if not row["current"]],
        "batch_errors": errors, "input_issues": issues, "excluded_evidence": excluded,
        "input_reports": deepcopy(input_reports or []),
        "inputs_healthy": bool(batches) and not issues,
        "production_writes": 0, "public_export_enabled": False,
        "notes": [
            "Reporting date precedes completeness and position count; ties retain all alternate evidence.",
            "The existing 10-day grace policy is unchanged. Stale rows remain visible but do not count as current.",
            "Source hashes, source identity, observation times and partial flags are retained without retimestamping.",
            "Malformed/failed/retained inputs remain diagnostic evidence and cannot make the launch gate green.",
        ],
    }
