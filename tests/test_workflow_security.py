from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


class WorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.header, cls.jobs = cls.text.split("\njobs:\n", 1)
        cls.build, cls.deploy = cls.jobs.split("\n  deploy:\n", 1)

    def test_workflow_default_permissions_are_read_only(self):
        self.assertIn("permissions:\n  contents: read\n", self.header)
        self.assertNotIn("pages: write", self.header)
        self.assertNotIn("id-token: write", self.header)

    def test_build_does_not_receive_pages_or_oidc_permissions(self):
        self.assertIn("  build:\n    permissions:\n      contents: write\n", "\njobs:\n" + self.jobs)
        self.assertNotIn("pages: write", self.build)
        self.assertNotIn("id-token: write", self.build)

    def test_deploy_is_the_only_pages_oidc_writer(self):
        self.assertIn("    permissions:\n      pages: write\n      id-token: write\n", "\n  deploy:\n" + self.deploy)

    def test_checkout_token_is_not_persisted(self):
        self.assertIn(
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6",
            self.build,
        )
        self.assertIn("persist-credentials: false", self.build)
        self.assertNotIn("actions/checkout@v6", self.text)

    def test_github_token_is_step_scoped(self):
        pre_steps = self.build.split("\n    steps:\n", 1)[0]
        self.assertNotIn("GH_TOKEN:", pre_steps)
        self.assertEqual(self.text.count("GH_TOKEN: ${{ github.token }}"), 5)
        for step in (
            "Restore cumulative history",
            "Import owner-supplied additions",
            "Generate GitHub Pages site",
            "Save cumulative historical archive",
            "Record collection status",
        ):
            block = self.text.split(f"- name: {step}", 1)[1].split("\n      - name:", 1)[0]
            self.assertIn("GH_TOKEN: ${{ github.token }}", block)

    def test_pages_actions_are_immutable_and_configure_step_removed(self):
        self.assertNotIn("actions/configure-pages@", self.text)
        self.assertIn(
            "actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b # v4",
            self.build,
        )
        self.assertIn(
            "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4",
            self.deploy,
        )


if __name__ == "__main__":
    unittest.main()
