import unittest
from datetime import date
from unittest.mock import patch

from tracker import amc_expenses


class MiraeExpenseTests(unittest.TestCase):
    def metadata(self, *, title="Total Expense Ratio -24 Sep 2026",
                 path="/DailyUploads/TotalExpenseRatio/IN_MF_EXPENSE_RATIO_SEBI_V3_24092026.xls",
                 published="/Date(1790208000000)/"):
        return [{"Title": title, "URL": path, "PublishDate": published}]

    def row(self, day=46289.0, *, scheme="Mirae Asset Small Cap Fund",
            nsdl="MIRA/O/E/SCF/24/10/0075", regular_ter=0.0212, direct_ter=0.0064):
        return [
            nsdl, scheme, day,
            0.0157, 0.0007, 0.0001, 0.0047, regular_ter,
            0.0032, 0.0007, 0.0001, 0.0024, direct_ter,
        ]

    def rows(self, data):
        return [
            list(amc_expenses._MIRAE_HEADER_1),
            list(amc_expenses._MIRAE_HEADER_2),
            *data,
        ]

    def test_mirae_metadata_selects_exact_latest_consistent_workbook(self):
        source, day = amc_expenses._mirae_select_file(
            self.metadata(), date(2026, 9, 25)
        )
        self.assertEqual(day, "2026-09-24")
        self.assertEqual(
            source,
            "https://www.miraeassetmf.co.in/DailyUploads/TotalExpenseRatio/"
            "IN_MF_EXPENSE_RATIO_SEBI_V3_24092026.xls",
        )

    def test_mirae_metadata_rejects_mismatched_or_duplicate_latest_file(self):
        with self.assertRaisesRegex(ValueError, "no dated current workbook"):
            amc_expenses._mirae_select_file(
                self.metadata(title="Total Expense Ratio -23 Sep 2026"),
                date(2026, 9, 25),
            )
        duplicate = self.metadata() + self.metadata()
        with self.assertRaisesRegex(ValueError, "duplicate workbooks"):
            amc_expenses._mirae_select_file(duplicate, date(2026, 9, 25))

    def test_mirae_latest_exact_row_retains_published_ber_and_total_ter(self):
        day, plans = amc_expenses.parse_mirae_rows(
            self.rows([
                self.row(46288.0),
                self.row(46289.0),
            ]),
            datemode=0,
            today=date(2026, 9, 25),
        )
        self.assertEqual(day, "2026-09-24")
        self.assertAlmostEqual(plans["Regular"]["base_expense_ratio"], 1.57)
        self.assertAlmostEqual(plans["Regular"]["ter"], 2.12)
        self.assertAlmostEqual(plans["Direct"]["base_expense_ratio"], 0.32)
        self.assertAlmostEqual(plans["Direct"]["ter"], 0.64)

    def test_mirae_future_wrong_identity_duplicate_and_format_change_rejected(self):
        day, plans = amc_expenses.parse_mirae_rows(
            self.rows([self.row(46289.0), self.row(46290.0)]),
            datemode=0,
            today=date(2026, 9, 24),
        )
        self.assertEqual(day, "2026-09-24")
        self.assertAlmostEqual(plans["Direct"]["ter"], 0.64)

        for kwargs in (
            {"scheme": "Mirae Asset Midcap Fund"},
            {"nsdl": "MIRA/O/E/OTHER"},
        ):
            with self.assertRaisesRegex(ValueError, "no dated Small Cap rows"):
                amc_expenses.parse_mirae_rows(
                    self.rows([self.row(**kwargs)]),
                    datemode=0,
                    today=date(2026, 9, 25),
                )

        row = self.row()
        with self.assertRaisesRegex(ValueError, "duplicate Small Cap rows"):
            amc_expenses.parse_mirae_rows(
                self.rows([row, list(row)]),
                datemode=0,
                today=date(2026, 9, 25),
            )

        changed = self.rows([self.row()])
        changed[1][12] = "Direct Plan - Calculated TER (%)"
        with self.assertRaisesRegex(ValueError, "metric columns changed"):
            amc_expenses.parse_mirae_rows(
                changed, datemode=0, today=date(2026, 9, 25)
            )

    def test_mirae_component_reconciliation_and_fraction_scale_are_strict(self):
        with self.assertRaisesRegex(ValueError, "components do not reconcile"):
            amc_expenses.parse_mirae_rows(
                self.rows([self.row(direct_ter=0.0070)]),
                datemode=0,
                today=date(2026, 9, 25),
            )
        bad = self.row()
        bad[8] = 0.32
        with self.assertRaisesRegex(ValueError, "fraction range"):
            amc_expenses.parse_mirae_rows(
                self.rows([bad]), datemode=0, today=date(2026, 9, 25)
            )

    @patch("tracker.amc_expenses.db.metric")
    @patch("tracker.amc_expenses.db.one", return_value={"code": "MIRAE"})
    @patch("tracker.amc_expenses._mirae_disclosure")
    def test_mirae_collector_stores_exact_source_hash_and_plan_metrics(
        self, mock_disclosure, _mock_one, mock_metric
    ):
        source = (
            "https://www.miraeassetmf.co.in/DailyUploads/TotalExpenseRatio/"
            "IN_MF_EXPENSE_RATIO_SEBI_V3_24092026.xls"
        )
        _, plans = amc_expenses.parse_mirae_rows(
            self.rows([self.row()]), datemode=0, today=date(2026, 9, 25)
        )
        mock_disclosure.return_value = (source, "2026-09-24", plans, "miraehash")
        result = amc_expenses.mirae(today=date(2026, 9, 25))
        self.assertIn("2026-09-24", result)
        self.assertEqual(mock_metric.call_count, 10)
        calls = {
            (call.args[1], call.args[2]): call.args[4]
            for call in mock_metric.call_args_list
        }
        self.assertAlmostEqual(calls[("Regular", "ter")], 2.12)
        self.assertAlmostEqual(calls[("Direct", "ter")], 0.64)
        self.assertAlmostEqual(calls[("Direct", "base_expense_ratio")], 0.32)
        self.assertTrue(all(call.args[3] == "2026-09-24" for call in mock_metric.call_args_list))
        self.assertTrue(all(call.args[6] == source for call in mock_metric.call_args_list))
        self.assertTrue(all(call.args[7] == "miraehash" for call in mock_metric.call_args_list))


if __name__ == "__main__":
    unittest.main()
