from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


class PublisherMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_completed_push_only_recovery_hooks_are_not_in_normal_publisher(self):
        push_only_if_lines = [
            line.strip()
            for line in self.text.splitlines()
            if line.strip().startswith("if: github.event_name == 'push'")
        ]
        self.assertEqual(push_only_if_lines, [])
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

    def test_nightly_collection_and_retained_archive_repair_remain_active(self):
        self.assertIn(
            "if: github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.refresh)",
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
