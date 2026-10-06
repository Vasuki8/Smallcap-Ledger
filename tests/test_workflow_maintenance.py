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

    def test_staged_midcap_audits_run_only_for_schedule_or_manual_refresh(self):
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
        condition = "github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.refresh)"
        for name in midcap_steps:
            marker = f"- name: {name}\n        if: {condition}"
            with self.subTest(name=name):
                self.assertIn(marker, self.text)
        self.assertEqual(self.text.count(f"if: {condition}"), len(midcap_steps))

    def test_manual_diagnostics_require_refresh_opt_in(self):
        diagnostics = (
            "Diagnose final six Mid Cap TER sources",
            "Inspect four concrete Mid Cap TER files",
            "Diagnose final three Mid Cap TER sources precisely",
            "Diagnose staged Mid Cap portfolio batch 1",
            "Diagnose staged Mid Cap portfolio batch 3 contracts",
        )
        for name in diagnostics:
            with self.subTest(name=name):
                self.assertIn(
                    f"- name: {name}\n        if: github.event_name == 'workflow_dispatch' && inputs.refresh",
                    self.text,
                )

    def test_manual_no_refresh_skips_source_repair_and_uses_retained_health_gate(self):
        repair = (
            "- name: Repair retained unarchived AMC communications\n"
            "        if: github.event_name == 'push' || github.event_name == 'schedule' || "
            "(github.event_name == 'workflow_dispatch' && inputs.refresh)"
        )
        self.assertIn(repair,self.text)
        self.assertIn("Gate retained publication on data health",self.text)
        self.assertIn("github.event_name == 'workflow_dispatch' && !inputs.refresh",self.text)
        self.assertIn("--retained-only",self.text)

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
