"""Delete only explicitly approved, audited merged-tip branches.

This script is intentionally fail-closed:
- the audit must contain exactly the expected high-confidence candidate count;
- main is never eligible;
- branches with an open PR are skipped;
- branches whose current tip moved away from the audited SHA are skipped;
- only exact current-tip matches are deleted.

Network access is via the GitHub REST API and requires GH_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

CONFIRMATION = "DELETE_AUDITED_MERGED_TIPS_299"


def _next_link(headers):
    raw = headers.get("Link", "")
    for part in raw.split(","):
        bits = [x.strip() for x in part.split(";")]
        if len(bits) >= 2 and bits[1] == 'rel="next"':
            return bits[0].strip("<>")
    return None


def api_json(url, token, method="GET"):
    request = Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "smallcap-ledger-branch-cleanup",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            if not body:
                return None, response.headers
            return json.loads(body), response.headers
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"GitHub API {method} {url} failed: {exc.code} {detail}") from exc


def paged_json(url, token):
    rows = []
    while url:
        payload, headers = api_json(url, token)
        if not isinstance(payload, list):
            raise RuntimeError("Expected paginated GitHub list response")
        rows.extend(payload)
        url = _next_link(headers)
    return rows


def plan_cleanup(audit, current_heads, open_pr_heads, expected_count):
    candidates = audit.get("high_confidence_candidates")
    if not isinstance(candidates, list):
        raise ValueError("Audit does not contain high_confidence_candidates")
    if len(candidates) != expected_count:
        raise ValueError(
            f"Expected {expected_count} audited candidates, found {len(candidates)}"
        )
    seen = set()
    delete = []
    missing = []
    moved = []
    open_pr = []
    for row in candidates:
        branch = str(row.get("branch") or "")
        audited_sha = str(row.get("tip_sha") or "")
        if not branch or not audited_sha:
            raise ValueError("Candidate is missing branch or tip_sha")
        if branch == "main":
            raise ValueError("main can never be a cleanup candidate")
        if branch in seen:
            raise ValueError(f"Duplicate cleanup candidate: {branch}")
        seen.add(branch)
        if branch in open_pr_heads:
            open_pr.append(branch)
            continue
        current_sha = current_heads.get(branch)
        if current_sha is None:
            missing.append(branch)
            continue
        if current_sha != audited_sha:
            moved.append(
                {
                    "branch": branch,
                    "audited_sha": audited_sha,
                    "current_sha": current_sha,
                }
            )
            continue
        delete.append({"branch": branch, "tip_sha": audited_sha})
    return {
        "delete": delete,
        "missing": missing,
        "moved": moved,
        "open_pr": open_pr,
    }


def live_repository_state(repository, token):
    owner = repository.split("/", 1)[0]
    branches = paged_json(
        f"https://api.github.com/repos/{repository}/branches?per_page=100", token
    )
    current_heads = {
        row["name"]: row["commit"]["sha"]
        for row in branches
        if isinstance(row, dict)
        and row.get("name")
        and isinstance(row.get("commit"), dict)
        and row["commit"].get("sha")
    }
    pulls = paged_json(
        f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100", token
    )
    open_pr_heads = {
        row.get("head", {}).get("ref")
        for row in pulls
        if isinstance(row, dict)
        and row.get("head", {}).get("repo", {}).get("owner", {}).get("login") == owner
    }
    open_pr_heads.discard(None)
    return current_heads, open_pr_heads


def delete_branch(repository, branch, token):
    encoded = quote(branch, safe="/")
    api_json(
        f"https://api.github.com/repos/{repository}/git/refs/heads/{encoded}",
        token,
        method="DELETE",
    )


def run(audit_path, repository, token, expected_count, apply=False):
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    if audit.get("destructive_actions_taken"):
        raise RuntimeError("Branch cleanup audit is already marked as executed")
    current_heads, open_pr_heads = live_repository_state(repository, token)
    plan = plan_cleanup(audit, current_heads, open_pr_heads, expected_count)
    result = {
        "repository": repository,
        "audit_main_sha": audit.get("main_sha"),
        "expected_candidates": expected_count,
        "eligible_exact_matches": len(plan["delete"]),
        "skipped_missing": plan["missing"],
        "skipped_moved": plan["moved"],
        "skipped_open_pr": plan["open_pr"],
        "deleted": [],
        "failures": [],
        "applied": bool(apply),
    }
    if not apply:
        return result
    if os.environ.get("CONFIRM_BRANCH_CLEANUP") != CONFIRMATION:
        raise RuntimeError("Explicit branch-cleanup confirmation environment value is missing")
    for row in plan["delete"]:
        try:
            delete_branch(repository, row["branch"], token)
            result["deleted"].append(row)
        except Exception as exc:
            result["failures"].append(
                {"branch": row["branch"], "error": str(exc)[:500]}
            )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=Path("docs/BRANCH-CLEANUP-AUDIT.json"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--expected-count", type=int, default=299)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    if not args.repository:
        raise SystemExit("GITHUB_REPOSITORY/--repository is required")
    if not token:
        raise SystemExit("GH_TOKEN is required")
    result = run(
        args.audit,
        args.repository,
        token,
        expected_count=args.expected_count,
        apply=args.apply,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
