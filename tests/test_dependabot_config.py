from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "dependabot.yml"


class DependabotConfigTests(unittest.TestCase):
    def test_actions_and_uv_are_monitored_weekly(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("version: 2\n"))
        self.assertIn('package-ecosystem: "github-actions"', text)
        self.assertIn('package-ecosystem: "uv"', text)
        self.assertEqual(text.count('interval: "weekly"'), 2)
        self.assertEqual(text.count('day: "monday"'), 2)
        self.assertEqual(text.count('timezone: "Asia/Kolkata"'), 2)

    def test_dependabot_pr_volume_is_bounded(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertEqual(text.count("open-pull-requests-limit: 5"), 2)


if __name__ == "__main__":
    unittest.main()
