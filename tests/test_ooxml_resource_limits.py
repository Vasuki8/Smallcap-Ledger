"""OOXML archive resource-limit regressions."""
import io
from pathlib import Path
import unittest
import zipfile

from tracker.archive_limits import validate_ooxml_package

ROOT=Path(__file__).resolve().parents[1]


def package(entries):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in entries:
            z.writestr(name,data)
    return out.getvalue()


class OoxmlResourceLimitTests(unittest.TestCase):
    def test_small_valid_package_passes(self):
        result=validate_ooxml_package(package([
            ("[Content_Types].xml",b"<Types/>"),
            ("xl/workbook.xml",b"<workbook/>"),
        ]))
        self.assertEqual(result["members"],2)
        self.assertGreater(result["uncompressed_bytes"],0)

    def test_total_expansion_limit_is_enforced(self):
        body=package([("xl/worksheets/sheet1.xml",b"A"*4096)])
        with self.assertRaisesRegex(ValueError,"expands beyond"):
            validate_ooxml_package(body,max_total_bytes=1024,max_member_bytes=8192)

    def test_member_count_limit_is_enforced(self):
        body=package([(f"xl/x{i}.xml",b"x") for i in range(3)])
        with self.assertRaisesRegex(ValueError,"too many ZIP members"):
            validate_ooxml_package(body,max_members=2)

    def test_unsafe_member_path_is_rejected(self):
        body=package([("../outside.xml",b"x")])
        with self.assertRaisesRegex(ValueError,"unsafe ZIP path"):
            validate_ooxml_package(body)

    def test_all_current_xlsx_parser_entry_points_are_preflighted(self):
        disclosures=(ROOT/"tracker"/"disclosures.py").read_text(encoding="utf-8")
        expenses=(ROOT/"tracker"/"amc_expenses.py").read_text(encoding="utf-8")
        self.assertIn("validate_ooxml_package(content)",disclosures)
        self.assertEqual(expenses.count("validate_ooxml_package(content)"),5)


if __name__=="__main__":
    unittest.main()
