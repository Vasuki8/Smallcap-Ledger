import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tracker.release_health import ASSET_REVIEW_THRESHOLD, release_health, summarize_release


class ReleaseHealthTests(unittest.TestCase):
    def test_summarize_release_counts_assets_and_bytes(self):
        payload = {
            "tag_name": "tracker-history",
            "assets": [
                {"name": "a.zip", "size": 100},
                {"name": "b.zip", "size": 250},
                {"name": "latest.json", "size": 50},
            ],
        }
        result = summarize_release(payload, threshold=10)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["asset_count"], 3)
        self.assertEqual(result["compressed_bytes"], 400)
        self.assertEqual(result["remaining_to_review_threshold"], 7)
        self.assertFalse(result["review_due"])
        self.assertEqual(result["policy"], "review_only_no_automatic_deletion")

    def test_summarize_release_flags_review_threshold_without_deleting(self):
        payload = {
            "tag_name": "tracker-history",
            "assets": [{"size": 1}] * ASSET_REVIEW_THRESHOLD,
        }
        result = summarize_release(payload)
        self.assertEqual(result["asset_count"], ASSET_REVIEW_THRESHOLD)
        self.assertEqual(result["remaining_to_review_threshold"], 0)
        self.assertTrue(result["review_due"])
        self.assertEqual(result["policy"], "review_only_no_automatic_deletion")

    def test_release_health_uses_read_only_gh_api_query(self):
        calls = []

        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"tag_name": "tracker-history", "assets": [{"size": 123}]}),
                stderr="",
            )

        result = release_health("Vasuki8/Smallcap-Ledger", threshold=5, runner=runner)
        self.assertEqual(result["asset_count"], 1)
        self.assertEqual(calls, [(
            ["gh", "api", "repos/Vasuki8/Smallcap-Ledger/releases/tags/tracker-history"],
            {"text": True, "capture_output": True, "check": False},
        )])

    def test_release_health_degrades_to_unavailable_on_query_failure(self):
        def runner(args, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="temporary API failure")

        result = release_health("Vasuki8/Smallcap-Ledger", runner=runner)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["review_due"])
        self.assertIn("temporary API failure", result["detail"])

    def test_release_health_without_repository_is_nonfatal(self):
        with patch.dict(os.environ, {}, clear=True):
            result = release_health(repository=None)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["review_due"])


if __name__ == "__main__":
    unittest.main()
