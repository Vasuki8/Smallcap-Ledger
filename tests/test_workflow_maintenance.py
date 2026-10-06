from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


class PublisherMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_completed_push_only_recovery_hooks_are_not_in_normal_publisher(self):
        retired = (
            "scripts/diagnose_bajaj_media.py",
            "scripts/diagnose_wealth_uti_transport.py",
            "scripts/refresh_sbi_sundaram_communications.py",
            "scripts/refresh_tata_wealth_communications.py",
            "scripts/refresh_union_communications.py",
            "scripts/refresh_uti_communications.py",
            "scripts/refresh_amc_reports.py",
            "scripts/refresh_icici_portfolios.py",
            "scripts/refresh_sbi_portfolios.py",
            "scripts/refresh_bandhan_portfolios.py",
            "scripts/refresh_axis_portfolios.py",
            "scripts/refresh_axis_expenses.py",
            "scripts/refresh_uti_expenses.py",
            "scripts/repair_samco_communication_classification.py",
        )
        for script in retired:
            with self.subTest(script=script):
                self.assertNotIn(script, self.text)

    def test_superseded_publishers_cancel_instead_of_consuming_collection_slot(self):
        self.assertIn("group: smallcap-daily-and-deploy", self.text)
        self.assertIn("cancel-in-progress: true", self.text)

    def test_staged_midcap_audits_do_not_delay_ordinary_code_pushes(self):
        midcap_steps = (
            "Establish staged audit generation boundary",
            "Preview staged Mid Cap universe",
            "Audit staged Mid Cap identities",
            "Store audited Mid Cap staging data",
            "Backfill staged Mid Cap NAV history",
            "Audit staged Mid Cap source coverage",
            "Classify staged Mid Cap TER gaps",
            "Audit staged Mid Cap first-party TER batch",
            "Audit staged Mid Cap first-party TER batch 2",
            "Reconcile staged Mid Cap TER readiness",
            "Audit staged Mid Cap benchmark identities",
            "Audit staged Mid Cap benchmark identities batch 2",
            "Reconcile staged Mid Cap benchmark readiness",
            "Audit staged Mid Cap current portfolio evidence",
            "Audit staged Mid Cap structured portfolio evidence batch 2",
            "Audit staged Mid Cap structured portfolio evidence batch 3",
            "Audit staged Mid Cap structured portfolio evidence batch 4",
            "Audit staged Mid Cap current portfolio evidence batch 5",
            "Reconcile staged Mid Cap portfolio readiness",
            "Audit staged Mid Cap launch readiness",
        )
        for name in midcap_steps:
            marker = f"- name: {name}\n        if: github.event_name != 'push'"
            with self.subTest(name=name):
                self.assertIn(marker, self.text)
        self.assertEqual(self.text.count("if: github.event_name != 'push'"), len(midcap_steps))

    def test_daily_collection_runs_for_push_schedule_and_manual_refresh(self):
        self.assertIn(
            "if: github.event_name == 'push' || github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.refresh)",
            self.text,
        )
        self.assertIn("uv run --frozen python scripts/daily_update.py", self.text)
        self.assertIn("uv run --frozen python scripts/repair_unarchived_communications.py", self.text)

    def test_publication_safety_pipeline_is_unchanged(self):
        for command in (
            "scripts/prepare_retention_metadata.py --apply",
            "scripts/compact_database.py --apply",
            "python -m unittest discover -s tests -v",
            "scripts/export_site.py",
            "scripts/validate_site.py site",
            "scripts/github_state.py publish",
            "scripts/record_build.py",
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.text)


if __name__ == "__main__":
    unittest.main()
