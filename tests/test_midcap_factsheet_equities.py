"""Regression fixtures for actual sector/holding HTML structure, not live values."""
import unittest
from bs4 import BeautifulSoup
from tracker.midcap_factsheet_equities import equity_positions, is_bold, validate_factsheet_context


def fixture():
    return '''<h1>Mahindra Manulife Mid Cap Fund</h1><p>Data as on 31st August 2026</p>
    <table><tr><th></th><th>Company / Issuer</th><th>% of Net Assets</th></tr>
    <tr style="font-weight:bold"><td></td><td>Healthcare</td><td>3.00%</td></tr>
    <tr style="f ont-weight:bold"><td></td><td>Aster DM Quality Care Limited</td><td>1.00%</td></tr>
    <tr><td></td><td>Biocon Limited</td><td>2.00%</td></tr>
    <tr style="font-weight:bold"><td></td><td>Information Technology</td><td>1.50%</td></tr>
    <tr style="fo nt-weight:bold"><td></td><td>Coforge Limited</td><td>1.50%</td></tr>
    <tr style="font-weight:700"><td></td><td>Power</td><td>2.00%</td></tr>
    <tr><td></td><td>JSW Energy Limited</td><td>2.00%</td></tr>
    <tr style="font-weight:bold"><td></td><td>Realty</td><td>1.00%</td></tr>
    <tr><td></td><td>Godrej Properties Limited</td><td>1.00%</td></tr>
    <tr style="font-weight:bold"><td></td><td>Financial Services</td><td>2.50%</td></tr>
    <tr><td></td><td>Bank of Maharashtra</td><td>2.50%</td></tr>
    <tr style="font-weight:bold"><td></td><td>Equity and Equity Related Total</td><td>10.00%</td></tr>
    <tr><td></td><td>Cash &amp; Other Receivables</td><td>90.00%</td></tr>
    <tr><td></td><td>Grand Total</td><td>100.00%</td></tr></table>'''


def parse(html):
    return equity_positions(BeautifulSoup(html, 'html.parser'))


class FactsheetEquityEvidenceTests(unittest.TestCase):
    def test_sector_names_are_not_holdings_and_suffix_is_not_required(self):
        rows = parse(fixture())
        self.assertEqual(len(rows), 6)
        names = {r['name'] for r in rows}
        self.assertFalse(names & {'Healthcare', 'Information Technology', 'Power', 'Realty', 'Financial Services'})
        self.assertIn('Bank of Maharashtra', names)
        self.assertAlmostEqual(sum(r['weight'] for r in rows), 10)
        self.assertTrue(all(r['asset_type'] == 'Equity' for r in rows))

    def test_css_does_not_repair_invalid_publisher_property_names(self):
        for style, expected in [('font-weight:bold', True), ('font-weight:700 !important', True),
                                ('f ont-weight:bold', False), ('fo nt-weight:bold', False)]:
            node = BeautifulSoup(f'<tr style="{style}"></tr>', 'html.parser').tr
            self.assertEqual(is_bold(node), expected)

    def test_kotak_column_layout_and_non_equity_exclusion(self):
        html = '''<table><tr><th>Issuer/Instrument</th><th></th><th>% to Net Assets</th></tr>
        <tr style="font-weight:bold"><td>Equity &amp; Equity related</td><td></td><td></td></tr>
        <tr style="font-weight:bold"><td>Finance</td><td></td><td>25.00</td></tr>
        <tr style="fo nt-weight:bold"><td>HOME FIRST FINANCE CO INDIA</td><td></td><td>25.00</td></tr>
        <tr><td>Equity &amp; Equity related - Total</td><td></td><td>25.00</td></tr>
        <tr><td>Mutual Fund Units</td><td></td><td></td></tr>
        <tr><td>Kotak Liquid Direct Growth</td><td></td><td>0.16</td></tr>
        <tr><td>Futures</td><td></td><td></td></tr>
        <tr><td>Company-SEP2026</td><td></td><td>0.49</td></tr></table>'''
        rows = parse(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['weight'], 25)

    def test_sector_subtotal_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Healthcare weights do not reconcile'):
            parse(fixture().replace('3.00%', '4.00%'))

    def test_equity_subtotal_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Equity weights do not reconcile'):
            parse(fixture().replace('10.00%', '11.00%'))

    def test_unknown_censored_and_nonfinite_weights_are_not_zero(self):
        for bad in ('-', '', '$', 'NaN', 'Infinity', '-1.00', '101.00'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse(fixture().replace('1.50%', bad))

    def test_duplicate_holding_is_not_silently_deduplicated(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate or ambiguous holding'):
            parse(fixture().replace('Biocon Limited', 'Aster DM Quality Care Limited'))

    def test_layout_drift_cannot_turn_sector_into_security(self):
        with self.assertRaises(ValueError):
            parse(fixture().replace('font-weight:bold', 'not-a-style:bold', 1))

    def test_identical_responsive_tables_are_not_double_counted(self):
        self.assertEqual(len(parse(fixture() + fixture())), 6)

    def test_conflicting_responsive_tables_are_rejected(self):
        other = fixture().replace('Aster DM Quality Care Limited', 'Different Issuer Limited')
        with self.assertRaisesRegex(ValueError, 'tables disagree'):
            parse(fixture() + other)

    def test_missing_equity_subtotal_is_not_current_evidence(self):
        with self.assertRaises(ValueError):
            parse(fixture().replace('Equity and Equity Related Total', 'Unknown aggregate'))

    def test_exact_scheme_and_current_data_date(self):
        soup = BeautifulSoup(fixture(), 'html.parser')
        validate_factsheet_context(soup, 'Mahindra Manulife Mid Cap Fund', '2026-08-31')
        with self.assertRaisesRegex(ValueError, 'exact staged scheme'):
            validate_factsheet_context(soup, 'Mahindra Manulife Small Cap Fund', '2026-08-31')

    def test_current_nav_does_not_refresh_old_factsheet(self):
        html = fixture().replace('Data as on 31st August 2026', 'Data as on 31st July 2026')
        html += '<p>NAV as on August 31, 2026</p>'
        with self.assertRaisesRegex(ValueError, 'current portfolio date'):
            validate_factsheet_context(BeautifulSoup(html, 'html.parser'), 'Mahindra Manulife Mid Cap Fund', '2026-08-31')

    def test_conflicting_data_dates_and_future_date_fail_closed(self):
        for text, expected in [(fixture() + '<p>Data as on 31 July 2026</p>', '2026-08-31'),
                               (fixture().replace('2026', '2099'), '2099-08-31')]:
            with self.assertRaisesRegex(ValueError, 'current portfolio date'):
                validate_factsheet_context(BeautifulSoup(text, 'html.parser'), 'Mahindra Manulife Mid Cap Fund', expected)


if __name__ == '__main__':
    unittest.main()
