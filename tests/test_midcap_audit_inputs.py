"""File provenance must distinguish this run from checked-in last-good reports."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tracker.midcap_audit_inputs import load_audit

NOW = datetime(2026, 9, 28, 4, 30, tzinfo=timezone.utc)
START = "2026-09-28T04:00:00+00:00"

class AuditInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "audit.json"
    def load(self, payload=None, start=START):
        if payload is not None:
            self.path.write_text(json.dumps(payload), encoding="utf-8")
        return load_audit(self.path, now=NOW, started_at=start)
    def test_current_file_keeps_hash_and_publisher_timestamp(self):
        report, check = self.load({"built_at":"2026-09-28T04:01:00+00:00", "results":[]})
        self.assertTrue(check["ok"])
        self.assertEqual(check["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(check["built_at"], report["built_at"])
    def test_missing_report_is_a_named_error_not_an_empty_success(self):
        report, check = self.load()
        self.assertEqual(report, {})
        self.assertFalse(check["ok"])
        self.assertEqual(check["error"], "missing_file")
    def test_malformed_report_is_not_accepted(self):
        self.path.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.load()[1]["error"], "invalid_json")
    def test_wrong_shape_is_not_accepted(self):
        self.assertEqual(self.load([])[1]["error"], "invalid_shape")
    def test_same_day_retained_file_is_not_generated_this_run(self):
        report, check = self.load({"built_at":"2026-09-28T03:59:59+00:00", "results":[1]})
        self.assertEqual(check["error"], "not_generated_this_run")
        self.assertEqual(report["results"], [1])  # Evidence is preserved, not erased.
    def test_missing_run_boundary_fails_closed(self):
        self.assertEqual(self.load({"built_at": START}, start=None)[1]["error"], "missing_run_boundary")
    def test_history_uses_observed_at_without_inventing_a_build_time(self):
        report, check = self.load({"observed_at":START})
        self.assertTrue(check["ok"])
        self.assertNotIn("built_at", report)
    def test_invalid_future_naive_and_missing_times_fail_closed(self):
        for stamp in (None, "bad", "2026-09-28T04:05:00", "2026-09-29T00:00:00+00:00"):
            with self.subTest(stamp=stamp):
                self.assertFalse(self.load({"built_at":stamp})[1]["ok"])
    def test_explicit_failed_status_is_not_success(self):
        self.assertEqual(self.load({"built_at":START, "status":"failed"})[1]["error"], "failed_report")
    def test_nonfinite_json_is_rejected(self):
        self.path.write_text('{"built_at":"'+START+'","value":NaN}', encoding="utf-8")
        self.assertEqual(self.load()[1]["error"], "invalid_json")

if __name__ == "__main__": unittest.main()
