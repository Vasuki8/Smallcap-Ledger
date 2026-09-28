"""Regress the observed Mahindra colspan legend after the portfolio total.

Contract observed in read-only source probe 36377130226; HTML response SHA-256:
53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640.
The sample issuers below are synthetic; only the layout/legend is reproduced.
"""
import unittest

from bs4 import BeautifulSoup
from tracker.midcap_factsheet_validation import mahindra_positions

HEADER = '<tr><th>Company / Issuer</th><th>% of Net Assets</th></tr>'
ISSUER = '<tr><td></td><td>Example Industries Limited</td><td>2.03%</td></tr>'
TOTAL = '<tr><td></td><td>Grand Total</td><td>100.00%</td></tr>'
FOOTER = ('<tr><td colspan="3"><div align="left">('
          '<img src="../Charts/Circle.svg"/> Top Ten Holdings - Issuer wise) '
          'as on August 31, 2026</div></td></tr>')


def parse(rows):
    return mahindra_positions(BeautifulSoup('<table>' + HEADER + rows + '</table>', 'html.parser'))


class MahindraPostTotalFooterTests(unittest.TestCase):
    def test_exact_observed_colspan_footer_is_not_a_financial_row(self):
        self.assertEqual(parse(ISSUER + TOTAL + FOOTER),
                         [{'name': 'Example Industries Limited', 'weight': 2.03}])

    def test_top_ten_marker_legend_does_not_truncate_the_full_issuer_table(self):
        rows = ''.join(f'<tr><td>Issuer {i} Limited</td><td>1%</td></tr>' for i in range(12))
        self.assertEqual(len(parse(rows + TOTAL + FOOTER)), 12)

    def test_same_footer_before_total_does_not_hide_a_malformed_row(self):
        with self.assertRaisesRegex(ValueError, 'name and weight columns'):
            parse(ISSUER + FOOTER + TOTAL)

    def test_unknown_footer_after_total_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'after Grand Total'):
            parse(ISSUER + TOTAL + '<tr><td colspan="3">Unreviewed extra content</td></tr>')

    def test_total_must_be_explicitly_one_hundred_percent(self):
        with self.assertRaisesRegex(ValueError, 'not 100%'):
            parse(ISSUER + TOTAL.replace('100.00%', '99.00%') + FOOTER)

    def test_financial_rows_after_total_are_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, 'after Grand Total'):
            parse(ISSUER + TOTAL + '<tr><td>Another Limited</td><td>1%</td></tr>')


if __name__ == '__main__':
    unittest.main()
