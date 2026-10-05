"""PDF parser resource-limit regressions."""
from pathlib import Path
import unittest

from tracker.pdf_safe import safe_pdf_text

ROOT=Path(__file__).resolve().parents[1]


class FakeContents:
    def __init__(self,data):
        self.data=data
    def get_data(self):
        return self.data


class FakePage:
    def __init__(self,data=b"BT (hello) Tj ET",text="hello"):
        self.contents=FakeContents(data)
        self.text=text
        self.calls=[]
    def get_contents(self):
        return self.contents
    def extract_text(self,**kwargs):
        self.calls.append(kwargs)
        return self.text


class PdfResourceLimitTests(unittest.TestCase):
    def test_small_content_stream_extracts_normally(self):
        page=FakePage()
        self.assertEqual(safe_pdf_text(page),"hello")
        self.assertEqual(page.calls,[{}])

    def test_oversized_content_stream_is_rejected_before_text_extraction(self):
        page=FakePage(data=b"A"*33)
        with self.assertRaisesRegex(ValueError,"exceeds the parser limit"):
            safe_pdf_text(page,max_content_bytes=32)
        self.assertEqual(page.calls,[])

    def test_layout_mode_is_forwarded_after_size_check(self):
        page=FakePage(text="layout")
        self.assertEqual(safe_pdf_text(page,extraction_mode="layout"),"layout")
        self.assertEqual(page.calls,[{"extraction_mode":"layout"}])

    def test_lightweight_parser_fixture_without_get_contents_still_works(self):
        class Fixture:
            def extract_text(self,**kwargs):
                return "fixture"
        self.assertEqual(safe_pdf_text(Fixture()),"fixture")

    def test_all_pdf_text_extraction_entry_points_use_shared_guard(self):
        disclosures=(ROOT/"tracker"/"disclosures.py").read_text(encoding="utf-8")
        expenses=(ROOT/"tracker"/"amc_expenses.py").read_text(encoding="utf-8")
        self.assertNotIn(".extract_text(",disclosures)
        self.assertIn("safe_pdf_text(reader.pages[0])",expenses)
        self.assertIn("len(reader.pages)>400",disclosures)

    def test_locked_pypdf_includes_latest_security_release(self):
        lock=(ROOT/"uv.lock").read_text(encoding="utf-8")
        start=lock.index('name = "pypdf"')
        block=lock[start:start+700]
        self.assertIn('version = "6.19.0"',block)


if __name__=="__main__":
    unittest.main()
