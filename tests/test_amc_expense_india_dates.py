"""AMC expense collectors default to the Asia/Kolkata reporting calendar."""
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from tracker import amc_expenses


class AmcExpenseIndiaDateTests(unittest.TestCase):
    def canara_rows(self, day):
        return [
            {
                "id":"1","sch_code":"SC","scheme_name":"Canara Robeco Small Cap Fund",
                "date":day,"plan_type":"Regular Plan","base_ter":"1.46","total_ter":"1.84",
            },
            {
                "id":"2","sch_code":"SC","scheme_name":"Canara Robeco Small Cap Fund",
                "date":day,"plan_type":"Direct Plan","base_ter":"0.46","total_ter":"0.68",
            },
        ]

    def test_default_parser_date_uses_india_today(self):
        rows=self.canara_rows("2026-09-24")+self.canara_rows("2026-09-25")
        with patch("tracker.amc_expenses.india_today",return_value=date(2026,9,24)):
            day,plans=amc_expenses.parse_canara_records(rows)
        self.assertEqual(day,"2026-09-24")
        self.assertEqual(plans["Direct"]["ter"],0.68)

    def test_explicit_today_still_overrides_default_clock(self):
        rows=self.canara_rows("2026-09-24")+self.canara_rows("2026-09-25")
        with patch("tracker.amc_expenses.india_today",return_value=date(2026,9,24)):
            day,_=amc_expenses.parse_canara_records(rows,today=date(2026,9,25))
        self.assertEqual(day,"2026-09-25")

    def test_expense_module_has_no_process_local_date_today_defaults(self):
        source=(Path(__file__).resolve().parents[1]/"tracker"/"amc_expenses.py").read_text(encoding="utf-8")
        self.assertNotIn("date.today()",source)
        self.assertEqual(source.count("today = today or india_today()"),37)


if __name__=="__main__":
    unittest.main()
