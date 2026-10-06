"""Local import UI must surface successful audit-log warnings."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ImportAuditWarningUiTests(unittest.TestCase):
    def test_import_result_includes_backend_warning(self):
        source=(ROOT/"dist"/"app.js").read_text(encoding="utf-8")
        self.assertIn("r.warning?saved+' '+r.warning:saved",source)
        self.assertIn("const saved=r.note||",source)


if __name__=="__main__":
    unittest.main()
