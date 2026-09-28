import json
from types import SimpleNamespace

from tracker.release_health import ASSET_REVIEW_THRESHOLD, release_health, summarize_release


def test_summarize_release_counts_assets_and_bytes():
    payload = {
        "tag_name": "tracker-history",
        "assets": [
            {"name": "a.zip", "size": 100},
            {"name": "b.zip", "size": 250},
            {"name": "latest.json", "size": 50},
        ],
    }
    result = summarize_release(payload, threshold=10)
    assert result["status"] == "ok"
    assert result["asset_count"] == 3
    assert result["compressed_bytes"] == 400
    assert result["remaining_to_review_threshold"] == 7
    assert result["review_due"] is False
    assert result["policy"] == "review_only_no_automatic_deletion"


def test_summarize_release_flags_review_threshold_without_deleting():
    payload = {"tag_name": "tracker-history", "assets": [{"size": 1}] * ASSET_REVIEW_THRESHOLD}
    result = summarize_release(payload)
    assert result["asset_count"] == ASSET_REVIEW_THRESHOLD
    assert result["remaining_to_review_threshold"] == 0
    assert result["review_due"] is True
    assert result["policy"] == "review_only_no_automatic_deletion"


def test_release_health_uses_read_only_gh_api_query():
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"tag_name": "tracker-history", "assets": [{"size": 123}]}),
            stderr="",
        )

    result = release_health("Vasuki8/Smallcap-Ledger", threshold=5, runner=runner)
    assert result["asset_count"] == 1
    assert calls == [(
        ["gh", "api", "repos/Vasuki8/Smallcap-Ledger/releases/tags/tracker-history"],
        {"text": True, "capture_output": True, "check": False},
    )]


def test_release_health_degrades_to_unavailable_on_query_failure():
    def runner(args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="temporary API failure")

    result = release_health("Vasuki8/Smallcap-Ledger", runner=runner)
    assert result["status"] == "unavailable"
    assert result["review_due"] is False
    assert "temporary API failure" in result["detail"]


def test_release_health_without_repository_is_nonfatal(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    result = release_health(repository=None)
    assert result["status"] == "unavailable"
    assert result["review_due"] is False
