"""Workflow ordering regressions for the collection publication gate."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github"/"workflows"/"daily.yml"


class PublicationGateWorkflowTests(unittest.TestCase):
    def test_gate_runs_after_collection_recovery_and_before_publication(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        boundary=text.index("Establish collection health boundary")
        collect=text.index("Collect daily data")
        recover=text.index("Recover any interrupted collection status")
        gate=text.index("Gate publication on collection health")
        tests=text.index("Check archive and financial calculations")
        export=text.index("Generate GitHub Pages site")
        archive=text.index("Save cumulative historical archive")
        upload=text.index("Upload website")
        self.assertLess(boundary,collect)
        self.assertLess(collect,recover)
        self.assertLess(recover,gate)
        self.assertLess(gate,tests)
        self.assertLess(gate,export)
        self.assertLess(gate,archive)
        self.assertLess(gate,upload)

    def test_gate_uses_current_run_boundary_and_persists_report(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("SMALLCAP_COLLECTION_STARTED_AT",text)
        self.assertIn("scripts/check_publication_health.py",text)
        self.assertIn("--output deployment/publication-health.json",text)


if __name__=="__main__":
    unittest.main()
