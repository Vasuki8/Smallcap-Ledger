"""Spreadsheet formula-injection regressions for exported CSV files."""
from pathlib import Path
import csv
import io
import unittest

from tracker.csv_safe import safe_cell, safe_record
from tracker.app import csv_response

ROOT=Path(__file__).resolve().parents[1]


class CsvFormulaSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralized_but_numbers_are_unchanged(self):
        for value in ("=1+1","+SUM(A1:A2)","-2+3","@cmd","   =HYPERLINK(\"x\")","\t=1","\r=1","\n=1"):
            with self.subTest(value=value):
                escaped=safe_cell(value)
                self.assertTrue(escaped.startswith("'"))
                self.assertTrue(escaped.endswith(value))
        self.assertEqual(safe_cell("Alpha Limited"),"Alpha Limited")
        self.assertEqual(safe_cell("https://example.com/source"),"https://example.com/source")
        self.assertEqual(safe_cell(123.45),123.45)

    def test_api_csv_response_uses_safe_cells(self):
        response=csv_response([
            {"name":"=2+2","weight":1.25,"source":"https://example.com"},
            {"name":"Normal","weight":2.5,"source":"+danger"},
        ],"test.csv")
        rows=list(csv.DictReader(io.StringIO(response.body.decode())))
        self.assertEqual(rows[0]["name"],"'=2+2")
        self.assertEqual(rows[0]["weight"],"1.25")
        self.assertEqual(rows[1]["source"],"'+danger")

    def test_both_csv_writers_use_the_shared_sanitizer(self):
        app=(ROOT/"tracker"/"app.py").read_text(encoding="utf-8")
        export=(ROOT/"scripts"/"export_site.py").read_text(encoding="utf-8")
        self.assertIn("w.writerows(safe_record(r) for r in records)",app)
        self.assertIn("w.writerows(safe_record(r) for r in rows)",export)


if __name__=="__main__":
    unittest.main()
