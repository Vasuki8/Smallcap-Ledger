"""Current fee selection must prioritize reporting date before metric type."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.app import funds, fund
from tracker.coverage import report
from tracker.fees import select_fee

FAMILY="Fee Selection Small Cap Fund"


class FeeSelectionTests(unittest.TestCase):
    def test_newer_ber_beats_older_ter(self):
        selected=select_fee([
            {"metric":"ter","as_of":"2026-04-30","value":"1.12"},
            {"metric":"base_expense_ratio","as_of":"2026-09-23","value":"0.42"},
        ])
        self.assertEqual(selected["metric"],"base_expense_ratio")
        self.assertEqual(selected["as_of"],"2026-09-23")

    def test_ter_wins_same_date_tie(self):
        selected=select_fee([
            {"metric":"base_expense_ratio","as_of":"2026-09-23","value":"0.42"},
            {"metric":"ter","as_of":"2026-09-23","value":"0.72"},
        ])
        self.assertEqual(selected["metric"],"ter")
        self.assertEqual(selected["value"],"0.72")

    def test_api_and_coverage_share_newest_dated_fee(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            with db.connect() as conn:
                conn.execute(
                    """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                       VALUES(?,?,?,?,?,?,?)""",
                    (8811,FAMILY+" Direct Growth",FAMILY,"Fee AMC","Direct","Growth","test"),
                )
            db.metric(
                FAMILY,"Direct","ter","2026-04-30",1.12,"% p.a.",
                "https://example.com/april-ter",
            )
            db.metric(
                FAMILY,"Direct","base_expense_ratio","2026-09-23",0.42,"% p.a.",
                "https://example.com/september-ber",
            )
            api_row=next(x for x in funds()["funds"] if x["family"]==FAMILY)
            detail=fund(8811)
            coverage=next(x for x in report()["funds"] if x["family"]==FAMILY)

            for selected in (api_row["selected_fee"],detail["selected_fee"],coverage["fee"]):
                self.assertEqual(selected["metric"],"base_expense_ratio")
                self.assertEqual(selected["as_of"],"2026-09-23")
                self.assertEqual(str(selected["value"]),"0.42")

    def test_frontend_and_static_export_use_selected_fee(self):
        root=Path(__file__).resolve().parents[1]
        app=(root/"dist"/"app.js").read_text(encoding="utf-8")
        research=(root/"dist"/"research.js").read_text(encoding="utf-8")
        export=(root/"scripts"/"export_site.py").read_text(encoding="utf-8")
        self.assertIn("if(s.selected_fee)return s.selected_fee",app)
        self.assertIn("function currentFee(f)",research)
        self.assertIn("key === 'ter' ? currentFee(f)?.value",research)
        self.assertIn("fee=row.get('selected_fee')",export)


if __name__=="__main__":
    unittest.main()
