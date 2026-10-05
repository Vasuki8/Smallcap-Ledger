"""Local backup UI must use the protected POST boundary."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class BackupPostUiTests(unittest.TestCase):
    def test_backup_is_not_exposed_as_passive_get_link(self):
        source=(ROOT/"dist"/"app.js").read_text(encoding="utf-8")
        self.assertNotIn('href="/api/export/backup"',source)
        self.assertIn("fetch('/api/export/backup',{method:'POST'",source)
        self.assertIn("'X-Smallcap-Client':'local'",source)
        self.assertIn('id="backup-download"',source)
        self.assertIn('id="settings-backup-download"',source)


if __name__=="__main__":
    unittest.main()
