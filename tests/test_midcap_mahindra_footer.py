"""The factsheet footer starts after its validated total, not amid holdings."""
import unittest
from bs4 import BeautifulSoup
from tracker.midcap_factsheet_validation import mahindra_positions
from tracker.midcap_factsheet_equities import equity_positions


HEADER = '<table><tr><th></th><th>Company / Issuer</th><th>% of Net Assets</th></tr>'
ROWS = ('<tr style="font-weight:bold"><td></td><td>Healthcare</td><td>5.00%</td></tr>'
        '<tr style="f ont-weight:bold"><td></td><td>Alpha Limited</td><td>2.00%</td></tr>'
        '<tr><td></td><td>Beta Limited</td><td>3.00%</td></tr>'
        '<tr><td></td><td>Equity and Equity Related Total</td><td>5.00%</td></tr>'
        '<tr><td></td><td>Cash &amp; Other Receivables</td><td>95.00%</td></tr>')
TOTAL = '<tr><td></td><td>Grand Total</td><td>100.00%</td></tr>'
FOOTER = '<tr><td colspan="3">(Top Ten Holdings - Issuer wise) as on August 31, 2026</td></tr>'


class MahindraFooterTests(unittest.TestCase):
    def parse(self, html):
        return mahindra_positions(BeautifulSoup(html, 'html.parser'))

    def test_colspan_footer_after_total_does_not_become_a_holding(self):
        soup = BeautifulSoup(HEADER + ROWS + TOTAL + FOOTER + '</table>', 'html.parser')
        classified = mahindra_positions(soup)
        structural = equity_positions(soup)
        self.assertEqual(len(classified), 2)
        self.assertEqual([(x['name'], x['weight']) for x in classified],
                         [(x['name'], x['weight']) for x in structural])

    def test_footer_shape_inside_portfolio_still_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'name and weight columns'):
            self.parse(HEADER + ROWS + FOOTER + TOTAL + '</table>')

    def test_wrong_grand_total_does_not_terminate_validation(self):
        with self.assertRaisesRegex(ValueError, 'grand total is not 100'):
            self.parse(HEADER + ROWS + TOTAL.replace('100.00', '99.00') + FOOTER + '</table>')

    def test_blank_grand_total_does_not_terminate_validation(self):
        with self.assertRaises(ValueError):
            self.parse(HEADER + ROWS + TOTAL.replace('100.00%', '') + FOOTER + '</table>')

    def test_later_table_content_does_not_leak_into_issuer_rows(self):
        extra = '<tr><td></td><td>Unrelated Limited</td><td>8.00%</td></tr>'
        rows = self.parse(HEADER + ROWS + TOTAL + FOOTER + extra + '</table>')
        self.assertNotIn('Unrelated Limited', {x['name'] for x in rows})


if __name__ == '__main__':
    unittest.main()
