"""Queued push publishers should skip expensive work once superseded."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github"/"workflows"/"daily.yml"


class SupersededPublisherWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_push_preflight_compares_event_sha_to_current_main(self):
        self.assertIn("Skip superseded push",self.text)
        self.assertIn('if [ "$GITHUB_EVENT_NAME" != "push" ]; then',self.text)
        self.assertIn('CURRENT_MAIN="$(gh api "repos/$GITHUB_REPOSITORY/branches/main" --jq '.commit.sha')"',self.text)
        self.assertIn('if [ "$CURRENT_MAIN" = "$GITHUB_SHA" ]; then',self.text)
        self.assertIn('echo "proceed=false" >> "$GITHUB_OUTPUT"',self.text)

    def test_expensive_build_requires_preflight_permission(self):
        self.assertIn("  build:\n    needs: supersession\n    if: needs.supersession.outputs.proceed == 'true'\n",self.text)

    def test_existing_late_stale_main_guard_remains(self):
        self.assertIn("Verify publication base is still current",self.text)
        self.assertIn('if [ "$CURRENT_MAIN" != "$SMALLCAP_BUILD_SHA" ]; then',self.text)

    def test_preflight_does_not_enable_mid_run_cancellation(self):
        self.assertIn("cancel-in-progress: false",self.text)


if __name__=="__main__":
    unittest.main()
