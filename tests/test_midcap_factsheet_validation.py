"""Offline regression coverage for factsheet issuer/sector separation."""
from html import escape
import unittest

from bs4 import BeautifulSoup
from tracker.midcap_factsheet_validation import mahindra_positions


def table(rows, header=("Company / Issuer", "% of Net Assets")):
    head = "<tr>" + "".join(f"<th>{escape(value)}</th>" for value in header) + "</tr>"
    body = "".join("<tr><td></td>" + "".join(f"<td>{escape(value)}</td>" for value in row)
                   + "</tr>" for row in rows)
    return f"<table>{head}{body}</table>"


def parse(html):
    return mahindra_positions(BeautifulSoup(html, "html.parser"))


class MahindraIssuerRowsTests(unittest.TestCase):
    def test_all_four_previously_misclassified_sectors_are_excluded(self):
        rows = [("Consumer Services", "0.85%"), ("Alpha Hotels Limited", "0.85%"),
                ("Healthcare", "9.70%"), ("Beta Healthcare Limited", "9.70%"),
                ("Power", "1.90%"), ("Gamma Energy Ltd.", "1.90%"),
                ("Services", "2.67%"), ("Delta Services Ltd", "2.67%")]
        result = parse(table(rows))
        self.assertEqual([x["name"] for x in result],
                         ["Alpha Hotels Limited", "Beta Healthcare Limited",
                          "Gamma Energy Ltd.", "Delta Services Ltd"])
        self.assertAlmostEqual(sum(x["weight"] for x in result), 15.12)

    def test_real_company_with_sector_word_is_retained(self):
        rows = [("Financial Services", "4.0%"), ("Alpha Financial Services Limited", "2%"),
                ("Beta Power Ltd.", "2%"), ("Bank of Maharashtra", "1%")]
        self.assertEqual(len(parse(table(rows))), 3)

    def test_other_sector_and_total_rows_are_not_holdings(self):
        rows = [("Capital Goods", "2%"), ("Alpha Industries Limited", "2%"),
                ("Equity and Equity Related Total", "2%"),
                ("Cash & Other Receivables", "98%"), ("Grand Total", "100%")]
        self.assertEqual(parse(table(rows)), [{"name": "Alpha Industries Limited", "weight": 2.0}])

    def test_sector_only_table_cannot_prove_named_holdings(self):
        self.assertEqual(parse(table([("Healthcare", "100%")])), [])

    def test_exact_header_is_required(self):
        self.assertEqual(parse(table([("Alpha Limited", "1%")], ("Sector", "Weight"))), [])

    def test_missing_name_or_weight_columns_fail_closed(self):
        for row in [("Alpha Limited",), ("Alpha Limited", "1%", "unexpected")]:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "columns"):
                parse(table([row]))

    def test_missing_or_nonfinite_weights_are_not_zero(self):
        for value in ["", "-", "NA", "NaN", "Infinity", "1 to 2", "1%%", "-1%"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse(table([("Alpha Limited", value)]))

    def test_out_of_range_weight_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            parse(table([("Alpha Limited", "100.1%")]))

    def test_explicit_zero_and_decimal_weight_are_retained(self):
        self.assertEqual([x["weight"] for x in parse(table(
            [("Alpha Limited", "0%"), ("Beta Ltd", "1.2345")]))], [0.0, 1.2345])

    def test_unknown_sector_label_is_not_silently_misclassified(self):
        with self.assertRaisesRegex(ValueError, "Unclassified"):
            parse(table([("New Industry Group", "4%")]))

    def test_duplicates_within_one_table_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse(table([("Alpha Limited", "1%"), ("ALPHA LIMITED", "1%")]))

    def test_identical_responsive_tables_are_counted_once(self):
        html = table([("Alpha Limited", "1%"), ("Beta Ltd", "2%")])
        self.assertEqual(len(parse(html + html)), 2)

    def test_conflicting_responsive_tables_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            parse(table([("Alpha Limited", "1%")]) + table([("Alpha Limited", "2%")]))

    def test_nested_layout_table_is_not_counted_twice(self):
        html = "<table><tr><td>" + table([("Alpha Limited", "1%")]) + "</td></tr></table>"
        self.assertEqual(len(parse(html)), 1)

    def test_whitespace_and_marker_column_are_normalized(self):
        result = parse(table([("Alpha\u00a0 Limited", "1.25 %")]))
        self.assertEqual(result[0], {"name": "Alpha Limited", "weight": 1.25})

    def test_impossible_named_weight_total_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceed"):
            parse(table([("Alpha Limited", "60%"), ("Beta Limited", "60%")]))


if __name__ == "__main__":
    unittest.main()
