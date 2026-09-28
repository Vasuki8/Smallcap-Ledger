"""Fail-closed provenance checks for automated status commits.

The publisher may create a generated status commit only when the remote main
branch still points to the exact revision that the workflow tested. This avoids
rebasing generated evidence onto newer code that was not part of the run.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class PublicationBaseMoved(RuntimeError):
    """Raised when main moved after the workflow started."""


def normalize_sha(value: str) -> str:
    value = str(value or "").strip()
    if len(value) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(f"Invalid commit SHA: {value!r}")
    return value.lower()


def assert_publication_base(expected_sha: str, local_parent_sha: str, remote_main_sha: str) -> None:
    expected = normalize_sha(expected_sha)
    local_parent = normalize_sha(local_parent_sha)
    remote_main = normalize_sha(remote_main_sha)
    if local_parent != expected:
        raise PublicationBaseMoved(
            f"Generated status commit parent {local_parent} does not match tested revision {expected}"
        )
    if remote_main != expected:
        raise PublicationBaseMoved(
            f"main moved from tested revision {expected} to {remote_main}; refusing stale status push"
        )


def git_text(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def push_generated_status_commit(root: Path, expected_sha: str) -> None:
    """Push HEAD to main only if main still equals the tested revision."""
    expected = normalize_sha(expected_sha)
    local_parent = git_text(root, "rev-parse", "HEAD^")
    subprocess.run(
        ["git", "fetch", "--no-tags", "origin", "main"],
        cwd=root,
        check=True,
    )
    remote_main = git_text(root, "rev-parse", "FETCH_HEAD")
    assert_publication_base(expected, local_parent, remote_main)
    subprocess.run(
        ["git", "push", "origin", "HEAD:main"],
        cwd=root,
        check=True,
    )
