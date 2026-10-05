from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"
RECORD_BUILD = ROOT / "scripts" / "record_build.py"
RECORD_DEPLOYMENT = ROOT / "scripts" / "record_deployment.py"


class PublisherProvenanceWorkflowTests(unittest.TestCase):
    def test_push_builds_checkout_the_triggering_sha(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "ref: ${{ github.event_name == 'push' && github.sha || 'main' }}",
            text,
        )
        self.assertIn(
            'echo "SMALLCAP_BUILD_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"',
            text,
        )

    def test_publication_is_rechecked_before_archive_and_status_publish(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Verify publication base is still current", text)
        self.assertIn('if [ "$CURRENT_MAIN" != "$SMALLCAP_BUILD_SHA" ]; then', text)
        verify = text.index("Verify publication base is still current")
        archive = text.index("Save cumulative historical archive")
        record = text.index("Record collection status")
        self.assertLess(verify, archive)
        self.assertLess(archive, record)

    def test_pages_live_marker_is_recorded_only_after_deploy_succeeds(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        publish = text.index("Publish website")
        marker = text.index("Record successful Pages deployment")
        self.assertLess(publish, marker)
        self.assertIn("build_sha: ${{ steps.revision.outputs.sha }}", text)
        self.assertIn("SMALLCAP_BUILD_SHA: ${{ needs.build.outputs.build_sha }}", text)
        self.assertIn("ref: main", text)

        build_source = RECORD_BUILD.read_text(encoding="utf-8")
        deploy_source = RECORD_DEPLOYMENT.read_text(encoding="utf-8")
        self.assertIn("'publication_state':'built_pending_pages_deploy'", build_source)
        self.assertIn('"publication_state":"deployed"', deploy_source)
        self.assertIn('deployment/pages-live.json', deploy_source)

    def test_deployment_marker_is_fail_closed_on_status_commit_parent(self):
        source = RECORD_DEPLOYMENT.read_text(encoding="utf-8")
        self.assertIn("assert_deployment_base", source)
        self.assertIn("status_parent!=expected", source)
        self.assertIn("remote!=status_commit", source)
        self.assertIn("push_generated_status_commit(ROOT,status_commit)", source)

    def test_record_build_never_rebases_generated_status_onto_newer_main(self):
        source = RECORD_BUILD.read_text(encoding="utf-8")
        self.assertNotIn("git('pull','--rebase','origin','main')", source)
        self.assertNotIn("git('push','origin','HEAD:main')", source)
        self.assertIn("push_generated_status_commit(ROOT,expected_build_sha)", source)
        self.assertIn("SMALLCAP_BUILD_SHA", source)


if __name__ == "__main__":
    unittest.main()
