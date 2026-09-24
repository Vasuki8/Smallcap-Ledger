import json
import unittest
from datetime import date
from unittest.mock import patch

from tracker import amc_expenses


class CanaraExpenseTests(unittest.TestCase):
    def rows(self, day="2026-09-24"):
        return [
            {
                "id": "1",
                "sch_code": "SC",
                "scheme_name": "Canara Robeco Small Cap Fund",
                "date": day,
                "plan_type": "Regular Plan",
                "base_ter": "1.46",
                "additional_expense_6a_b": "0.05",
                "additional_expense_6a_c": "0",
                "gst": "0.33",
                "total_ter": "1.84",
            },
            {
                "id": "2",
                "sch_code": "SC",
                "scheme_name": "Canara Robeco Small Cap Fund",
                "date": day,
                "plan_type": "Direct Plan",
                "base_ter": "0.46",
                "additional_expense_6a_b": "0.05",
                "additional_expense_6a_c": "0",
                "gst": "0.17",
                "total_ter": "0.68",
            },
        ]

    def test_exact_latest_plan_pair_retains_published_ber_and_ter(self):
        records = self.rows("2026-09-23") + self.rows("2026-09-24")
        day, plans = amc_expenses.parse_canara_records(records, date(2026, 9, 24))
        self.assertEqual(day, "2026-09-24")
        self.assertEqual(
            plans,
            {
                "Regular": {"base_expense_ratio": 1.46, "ter": 1.84},
                "Direct": {"base_expense_ratio": 0.46, "ter": 0.68},
            },
        )

    def test_future_rows_are_ignored_and_latest_complete_day_is_used(self):
        records = self.rows("2026-09-23") + self.rows("2026-09-25")
        day, plans = amc_expenses.parse_canara_records(records, date(2026, 9, 24))
        self.assertEqual(day, "2026-09-23")
        self.assertEqual(plans["Direct"]["ter"], 0.68)

    def test_wrong_scheme_or_code_cannot_be_promoted(self):
        rows = self.rows()
        rows[0]["scheme_name"] = "Canara Robeco Mid Cap Fund"
        with self.assertRaisesRegex(ValueError, "no complete dated"):
            amc_expenses.parse_canara_records(rows, date(2026, 9, 24))

        rows = self.rows()
        rows[1]["sch_code"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "no complete dated"):
            amc_expenses.parse_canara_records(rows, date(2026, 9, 24))

    def test_duplicate_plan_or_total_below_ber_is_rejected(self):
        rows = self.rows()
        rows.append(dict(rows[1], id="3"))
        with self.assertRaisesRegex(ValueError, "duplicate plan rows"):
            amc_expenses.parse_canara_records(rows, date(2026, 9, 24))

        rows = self.rows()
        rows[1]["total_ter"] = "0.40"
        with self.assertRaisesRegex(ValueError, "below BER"):
            amc_expenses.parse_canara_records(rows, date(2026, 9, 24))

    @patch("tracker.amc_expenses.db.metric")
    @patch("tracker.amc_expenses.db.one", return_value={"code": "CANARA"})
    @patch("tracker.amc_expenses.fetch")
    def test_live_collector_shape_stores_four_exact_metrics(self, mock_fetch, _mock_one, mock_metric):
        body = json.dumps(self.rows()).encode()
        mock_fetch.return_value = (body, "hash123", "application/json")
        result = amc_expenses.canara(today=date(2026, 9, 24), lookback_days=3)

        self.assertIn("2026-09-24", result)
        url = mock_fetch.call_args.args[0]
        self.assertIn("from_date=2026-09-22", url)
        self.assertIn("to_date=2026-09-24", url)
        self.assertEqual(mock_metric.call_count, 4)

        calls = {
            (call.args[1], call.args[2]): call.args[4]
            for call in mock_metric.call_args_list
        }
        self.assertEqual(calls[("Regular", "base_expense_ratio")], 1.46)
        self.assertEqual(calls[("Regular", "ter")], 1.84)
        self.assertEqual(calls[("Direct", "base_expense_ratio")], 0.46)
        self.assertEqual(calls[("Direct", "ter")], 0.68)
        self.assertTrue(all(call.args[3] == "2026-09-24" for call in mock_metric.call_args_list))
        self.assertTrue(all(call.args[7] == "hash123" for call in mock_metric.call_args_list))


if __name__ == "__main__":
    unittest.main()
