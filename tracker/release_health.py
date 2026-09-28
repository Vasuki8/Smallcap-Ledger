"""Operational health for the durable GitHub release archive.

This module is read-only. It never deletes, uploads, repacks, or changes retained
evidence. The review threshold is an internal maintenance trigger, not a
retention rule.
"""
from __future__ import annotations

import json
import os
import subprocess

RELEASE_TAG = "tracker-history"
ASSET_REVIEW_THRESHOLD = 750


def summarize_release(payload, threshold=ASSET_REVIEW_THRESHOLD):
    assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(assets, list):
        raise ValueError("Release payload does not contain an asset list")
    sizes = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        try:
            size = int(asset.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        sizes.append(max(0, size))
    count = len(assets)
    threshold = int(threshold)
    if threshold <= 0:
        raise ValueError("Review threshold must be positive")
    return {
        "status": "ok",
        "tag": str(payload.get("tag_name") or RELEASE_TAG),
        "asset_count": count,
        "compressed_bytes": sum(sizes),
        "review_threshold_assets": threshold,
        "remaining_to_review_threshold": max(0, threshold - count),
        "review_due": count >= threshold,
        "policy": "review_only_no_automatic_deletion",
    }


def release_health(repository=None, threshold=ASSET_REVIEW_THRESHOLD, runner=None):
    repository = repository or os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        return {
            "status": "unavailable",
            "tag": RELEASE_TAG,
            "review_threshold_assets": int(threshold),
            "review_due": False,
            "policy": "review_only_no_automatic_deletion",
            "detail": "GITHUB_REPOSITORY is not set",
        }
    runner = runner or subprocess.run
    result = runner(
        ["gh", "api", f"repos/{repository}/releases/tags/{RELEASE_TAG}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "GitHub release query failed").strip()
        return {
            "status": "unavailable",
            "tag": RELEASE_TAG,
            "review_threshold_assets": int(threshold),
            "review_due": False,
            "policy": "review_only_no_automatic_deletion",
            "detail": detail[:300],
        }
    try:
        payload = json.loads(result.stdout)
        return summarize_release(payload, threshold=threshold)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "unavailable",
            "tag": RELEASE_TAG,
            "review_threshold_assets": int(threshold),
            "review_due": False,
            "policy": "review_only_no_automatic_deletion",
            "detail": str(exc)[:300],
        }
