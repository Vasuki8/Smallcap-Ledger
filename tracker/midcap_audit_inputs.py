"""Read-only audit input validation: file generation is not source freshness."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def timestamp(value):
    """Require a timezone-bearing ISO timestamp; never assume a missing zone."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing_timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("naive_timestamp")
    return result.astimezone(timezone.utc)


def clock(now=None):
    result = now or datetime.now(timezone.utc)
    if not isinstance(result, datetime) or result.tzinfo is None:
        raise ValueError("evaluation clock must be timezone-aware")
    return result.astimezone(timezone.utc)


def _reject_constant(value):
    raise ValueError("nonfinite_json: " + value)


def load_audit(path, *, now=None, started_at=None):
    """Return the original report and a separate integrity record, including failures.

    A successful old file remains available for diagnosis but cannot satisfy a
    current-run check. The GitHub workflow supplies the boundary before audits.
    This function never writes, retimestamps or modifies the source file.
    """
    now = clock(now)
    path = Path(path)
    check = {"path": str(path), "sha256": None, "built_at": None,
             "ok": False, "error": None}
    data = {}
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        check["error"] = "missing_file"
        return data, check
    except OSError:
        check["error"] = "unreadable_file"
        return data, check
    check["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError):
        check["error"] = "invalid_json"
        return {}, check
    if not isinstance(data, dict):
        check["error"] = "invalid_shape"
        return {}, check
    check["built_at"] = data.get("built_at", data.get("observed_at"))
    try:
        built = timestamp(check["built_at"])
        if built > now:
            raise ValueError("future_timestamp")
        if started_at is None:
            raise ValueError("missing_run_boundary")
        start = timestamp(started_at)
        if start > now:
            raise ValueError("future_run_boundary")
        if built < start:
            raise ValueError("not_generated_this_run")
        if data.get("status") in ("failed", "error", "cancelled", "interrupted"):
            raise ValueError("failed_report")
    except ValueError as exc:
        check["error"] = str(exc)
        return data, check
    check["ok"] = True
    return data, check
