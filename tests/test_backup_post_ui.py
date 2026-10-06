"""Local backup UI must stream through a protected native POST."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class BackupPostUiTests(unittest.TestCase):
    def test_backup_uses_native_post_without_buffering_whole_zip_in_javascript(self):
        source=(ROOT/"dist"/"app.js").read_text(encoding="utf-8")
        self.assertNotIn('href="/api/export/backup"',source)
        self.assertNotIn("fetch('/api/export/backup'",source)
        self.assertNotIn(".blob()",source)
        self.assertNotIn("URL.createObjectURL",source)
        self.assertGreaterEqual(
            source.count('method="post" action="/api/export/backup"'),2)
        self.assertIn('id="backup-download"',source)
        self.assertIn('id="settings-backup-download"',source)


if __name__=="__main__":
    unittest.main()
