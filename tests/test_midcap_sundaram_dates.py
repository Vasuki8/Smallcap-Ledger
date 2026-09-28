"""AUM, NAV and portfolio reporting dates must remain independent."""
import json
import unittest
from unittest.mock import patch

from tracker.midcap_portfolio_batch5 import SUNDARAM_CARD, SUNDARAM_FAMILY, _sundaram_result


class SundaramPortfolioDateTests(unittest.TestCase):
    def card(self):
        return {'GROUP_NAME': SUNDARAM_FAMILY, 'FUNDGROUP_ID': 'MC', 'FUND_CATEGORY': 'Mid Cap',
                'AUMASONDATE': '31-Jul-2026', 'REG_NAV_DT': '25-Sep-2026',
                'PORTFOLIO_PATH': '/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx'}

    def reader(self, cards, content=b'PKfixture'):
        calls = []
        def fetch(url, **kwargs):
            self.assertIs(kwargs.get('archive'), False)
            calls.append(url)
            if url == SUNDARAM_CARD:
                return json.dumps(cards).encode(), None, 'application/json'
            return content, None, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return fetch, calls

    def snapshot(self):
        return {'as_of': '2026-08-31', 'positions_observed': 6, 'complete': False,
                'sheet': 'MIDCAP', 'unknown_rows': ['Publisher censored a holding'], 'aum': 123.0}

    def test_current_workbook_is_accepted_even_when_card_aum_is_older(self):
        fetch, calls = self.reader([self.card()])
        with patch('tracker.midcap_portfolio_batch5._parse_workbook', return_value=self.snapshot()) as parse:
            row = _sundaram_result(fetch, '2026-08-31')
        parse.assert_called_once_with(b'PKfixture', SUNDARAM_FAMILY, '2026-08-31')
        self.assertEqual(len(calls), 2)
        self.assertEqual(row['as_of'], '2026-08-31')
        self.assertEqual(row['card_aum_as_of_raw'], '31-Jul-2026')
        self.assertEqual(row['publisher_scheme_code'], 'MC')
        self.assertEqual(len(row['discovery_source_sha256']), 64)
        self.assertFalse(row['complete'])
        self.assertEqual(row['unknown_rows'], self.snapshot()['unknown_rows'])

    def test_current_card_aum_never_overrides_stale_workbook(self):
        card = self.card(); card['AUMASONDATE'] = '31-Aug-2026'
        fetch, _ = self.reader([card])
        with patch('tracker.midcap_portfolio_batch5._parse_workbook', side_effect=ValueError('No exact current snapshot')):
            with self.assertRaisesRegex(ValueError, 'No exact current'):
                _sundaram_result(fetch, '2026-08-31')

    def test_returned_workbook_date_is_checked_again(self):
        fetch, _ = self.reader([self.card()])
        snapshot = {**self.snapshot(), 'as_of': '2026-07-31'}
        with patch('tracker.midcap_portfolio_batch5._parse_workbook', return_value=snapshot):
            with self.assertRaisesRegex(ValueError, 'current portfolio date'):
                _sundaram_result(fetch, '2026-08-31')

    def test_wrong_scheme_code_or_category_fails_before_download(self):
        for key, value in [('FUNDGROUP_ID', 'SC'), ('FUND_CATEGORY', 'Large & Mid Cap')]:
            card = self.card(); card[key] = value
            fetch, calls = self.reader([card])
            with self.assertRaisesRegex(ValueError, 'scheme code/category'):
                _sundaram_result(fetch, '2026-08-31')
            self.assertEqual(calls, [SUNDARAM_CARD])

    def test_missing_external_and_non_workbook_paths_are_rejected(self):
        for path in ['', 'https://example.com/MIDCAP.xlsx', '/login.html']:
            card = self.card(); card['PORTFOLIO_PATH'] = path
            fetch, calls = self.reader([card])
            with self.assertRaisesRegex(ValueError, 'approved first-party workbook'):
                _sundaram_result(fetch, '2026-08-31')
            self.assertEqual(calls, [SUNDARAM_CARD])

    def test_duplicate_or_wrong_family_is_not_coverage(self):
        wrong = self.card(); wrong['GROUP_NAME'] = 'Sundaram Small Cap Fund'
        for cards in [[self.card(), self.card()], [wrong]]:
            fetch, calls = self.reader(cards)
            with self.assertRaisesRegex(ValueError, 'exact Mid Cap rows'):
                _sundaram_result(fetch, '2026-08-31')
            self.assertEqual(calls, [SUNDARAM_CARD])

    def test_html_error_response_is_not_parsed_as_portfolio(self):
        fetch, _ = self.reader([self.card()], b'<html>not a workbook</html>')
        with patch('tracker.midcap_portfolio_batch5._parse_workbook') as parse:
            with self.assertRaisesRegex(ValueError, 'supported workbook'):
                _sundaram_result(fetch, '2026-08-31')
        parse.assert_not_called()


if __name__ == '__main__':
    unittest.main()
