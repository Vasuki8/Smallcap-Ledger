"""Record a successful GitHub Pages deployment against the exact tested build."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.publication_provenance import PublicationBaseMoved, git_text, normalize_sha, push_generated_status_commit


def assert_deployment_base(expected_build_sha,status_commit_sha,status_parent_sha,remote_main_sha):
    expected=normalize_sha(expected_build_sha)
    status_commit=normalize_sha(status_commit_sha)
    status_parent=normalize_sha(status_parent_sha)
    remote=normalize_sha(remote_main_sha)
    if status_parent!=expected:
        raise PublicationBaseMoved(
            f"Pre-deploy status commit parent {status_parent} does not match tested revision {expected}"
        )
    if remote!=status_commit:
        raise PublicationBaseMoved(
            f"main moved from pre-deploy status commit {status_commit} to {remote}; refusing deployment marker"
        )
    return status_commit


def marker(expected_build_sha,status_commit_sha,page_url,run_id,*,now=None):
    expected=normalize_sha(expected_build_sha)
    status_commit=normalize_sha(status_commit_sha)
    stamp=(now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return {
        "publication_state":"deployed",
        "deployed_at":stamp,
        "source_build_sha":expected,
        "status_commit_sha":status_commit,
        "page_url":str(page_url or ""),
        "workflow_run_id":str(run_id or ""),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-url",required=True)
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args(argv)
    expected=os.environ.get("SMALLCAP_BUILD_SHA","").strip()
    if not expected:
        raise RuntimeError("SMALLCAP_BUILD_SHA is required for deployment provenance")

    status_commit=git_text(ROOT,"rev-parse","HEAD")
    status_parent=git_text(ROOT,"rev-parse","HEAD^")
    subprocess.run(["git","fetch","--no-tags","origin","main"],cwd=ROOT,check=True)
    remote_main=git_text(ROOT,"rev-parse","FETCH_HEAD")
    assert_deployment_base(expected,status_commit,status_parent,remote_main)

    target=ROOT/"deployment"/"pages-live.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(marker(expected,status_commit,args.page_url,args.run_id),indent=2)+"\n",encoding="utf-8")

    subprocess.run(["git","config","user.name","github-actions[bot]"],cwd=ROOT,check=True)
    subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],cwd=ROOT,check=True)
    subprocess.run(["git","add","deployment/pages-live.json"],cwd=ROOT,check=True)
    subprocess.run(["git","commit","-m","Record successful Pages deployment [skip ci]"],cwd=ROOT,check=True)
    push_generated_status_commit(ROOT,status_commit)


if __name__=="__main__":
    main()
