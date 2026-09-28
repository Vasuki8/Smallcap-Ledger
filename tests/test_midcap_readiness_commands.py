"""Integration of file verification, source freshness and the launch policy."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_midcap_launch_readiness import from_files as launch_from_files
from scripts.reconcile_midcap_portfolio_readiness import from_files as portfolios_from_files
from tracker.midcap_launch_readiness import UPSTREAM_FILES
import test_midcap_launch_readiness as launch_fixtures
NOW = launch_fixtures.NOW
from test_midcap_freshness_regressions import FAMILY, AMC, evidence, batch

START = "2026-09-27T12:00:00Z"

class ReadinessCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
    def write(self, name, data):
        path = self.root / name; path.write_text(json.dumps(data), encoding="utf-8"); return path
    def setup_launch(self):
        values = launch_fixtures.MidCapLaunchReadinessTests().fixtures(bench=34, portfolio=34)
        self.paths = {}
        for name,value in zip(("source_audit","ter","benchmark","portfolio","history"),values):
            value.setdefault("built_at", "2026-09-28T11:00:00Z")
            self.paths[name] = self.write(name + ".json",value)
        for filenames in UPSTREAM_FILES.values():
            for name in filenames:
                self.write(name,{"built_at":"2026-09-28T11:00:00Z","results":[]})
    def test_valid_inputs_reach_data_gate_but_never_enable_public_surface(self):
        self.setup_launch()
        result = launch_from_files(self.paths, now=NOW, started_at=START)
        self.assertTrue(result["data_ready"])
        self.assertFalse(result["launch_ready"])
        self.assertFalse(result["public_export_enabled"])
    def test_missing_core_source_produces_blocked_report_instead_of_crashing(self):
        self.setup_launch(); self.paths["source_audit"].unlink()
        result = launch_from_files(self.paths, now=NOW, started_at=START)
        self.assertFalse(result["data_ready"])
        self.assertIn("audit_input_integrity",result["blockers"])
    def test_new_summary_cannot_hide_old_upstream_batch(self):
        self.setup_launch()
        self.write("MIDCAP-BENCHMARK-BATCH1.json",{"built_at":"2026-09-27T11:00:00Z","results":[]})
        result=launch_from_files(self.paths,now=NOW,started_at=START)
        self.assertFalse(result["data_ready"])
        self.assertEqual(next(x for x in result["input_health"] if x["name"]=="MIDCAP-BENCHMARK-BATCH1.json")["error"],"not_generated_this_run")
    def test_supplied_missing_portfolio_batch_is_not_silently_omitted(self):
        path=self.write("batch1.json",batch(evidence()))
        result=portfolios_from_files({FAMILY:AMC},[path,self.root/"missing.json"],now=NOW,started_at=START)
        self.assertFalse(result["inputs_healthy"])
        self.assertEqual(result["current_portfolio_evidence"],1)
        self.assertEqual(result["input_reports"][1]["error"],"missing_file")
    def test_missing_run_boundary_does_not_make_a_green_launch(self):
        self.setup_launch()
        result=launch_from_files(self.paths,now=NOW,started_at=None)
        self.assertFalse(result["data_ready"])
        self.assertTrue(all(not x["ok"] for x in result["input_health"]))

    def test_older_file_has_diagnostics_without_current_coverage(self):
        path=self.write("old.json",batch(evidence()))
        result=portfolios_from_files({FAMILY:AMC},[path],now=NOW,started_at="2026-09-28T00:00:00Z")
        self.assertEqual(result["current_portfolio_evidence"],0)
        self.assertEqual(result["excluded_evidence"][0]["reason"],"not_generated_this_run")

if __name__ == "__main__": unittest.main()
