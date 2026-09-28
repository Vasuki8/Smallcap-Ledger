"""Qualified metric dates cannot replace a factsheet's own data date."""
import unittest
from bs4 import BeautifulSoup
from tracker.midcap_factsheet_equities import validate_factsheet_context


class FactsheetDateScopeTests(unittest.TestCase):
    def test_kotak_older_folio_count_date_does_not_override_report_date(self):
        html = ('<h1>Kotak Mid Cap Fund</h1><p>Data as on 31st August, 2026 unless otherwise specified.</p>'
                '<p>Folio Count data as on 31st July 2026.</p>')
        validate_factsheet_context(BeautifulSoup(html, 'html.parser'), 'Kotak Mid Cap Fund', '2026-08-31')

    def test_qualified_metric_date_cannot_establish_a_factsheet_date(self):
        html = '<h1>Kotak Mid Cap Fund</h1><p>Folio Count data as on 31st August 2026.</p>'
        with self.assertRaisesRegex(ValueError, 'current portfolio date'):
            validate_factsheet_context(BeautifulSoup(html, 'html.parser'), 'Kotak Mid Cap Fund', '2026-08-31')


if __name__ == '__main__':
    unittest.main()
