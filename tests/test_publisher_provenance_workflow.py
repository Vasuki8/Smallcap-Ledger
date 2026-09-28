from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"
RECORD_BUILD = ROOT / "scripts" / "record_build.py"


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

    def test_record_build_never_rebases_generated_status_onto_newer_main(self):
        source = RECORD_BUILD.read_text(encoding="utf-8")
        self.assertNotIn("git('pull','--rebase','origin','main')", source)
        self.assertNotIn("git('push','origin','HEAD:main')", source)
        self.assertIn("push_generated_status_commit(ROOT,expected_build_sha)", source)
        self.assertIn("SMALLCAP_BUILD_SHA", source)


if __name__ == "__main__":
    unittest.main()
