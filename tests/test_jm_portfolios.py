import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import jm_portfolios
from tracker.portfolio_parser import parse_sheet


class JmPortfolioTests(unittest.TestCase):
    def test_closed_months_roll_year_boundary(self):
        self.assertEqual(
            list(jm_portfolios.closed_months(date(2027, 2, 5))),
            [date(2027, 1, 31), date(2026, 12, 31)])

    def test_monthly_subcategory_requires_exact_public_category(self):
        rows = [
            {'DownloadCategoryID': 2, 'DownloadSubCategoryID': 3,
             'SubCategoryName': 'Fortnightly Portfolio of Schemes'},
            {'DownloadCategoryID': 2, 'DownloadSubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes'},
            {'DownloadCategoryID': 3, 'DownloadSubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes'},
        ]
        with patch('tracker.jm_portfolios._decrypt', return_value=rows):
            self.assertEqual(jm_portfolios._monthly_subcategory(b'cipher'), 4)

    def test_listing_accepts_only_exact_smallcap_closed_months(self):
        rows = [
            {'CategoryID': 2, 'SubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes',
             'Title': 'Monthly Portfolio - JM Small Cap Fund - Aug 31, 2026',
             'FileName': 'CMS/downloads/Portfolio Disclosure/Monthly Portfolio of Schemes/Monthly Portfolio - JM Small Cap Fund - Aug 31, 2026.xlsx',
             'FileEXT': '.xlsx'},
            {'CategoryID': 2, 'SubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes',
             'Title': 'Monthly Portfolio - JM Small Cap Fund - July 31, 2026',
             'FileName': 'CMS/downloads/Portfolio Disclosure/Monthly Portfolio of Schemes/Monthly Portfolio - JM Small Cap Fund - July 31, 2026.xlsx',
             'FileEXT': '.xlsx'},
            {'CategoryID': 2, 'SubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes',
             'Title': 'Monthly Portfolio - JM Small Cap Fund - Sep 30, 2026',
             'FileName': 'CMS/downloads/Portfolio Disclosure/Monthly Portfolio of Schemes/future.xlsx',
             'FileEXT': '.xlsx'},
            {'CategoryID': 2, 'SubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes',
             'Title': 'Monthly Portfolio - JM Mid cap Fund - Aug 31, 2026',
             'FileName': 'CMS/downloads/Portfolio Disclosure/Monthly Portfolio of Schemes/midcap.xlsx',
             'FileEXT': '.xlsx'},
            {'CategoryID': 2, 'SubCategoryID': 4,
             'SubCategoryName': 'Monthly Portfolio of Schemes',
             'Title': 'Monthly Portfolio - JM Small Cap Fund - Aug 31, 2026',
             'FileName': 'https://example.com/not-jm.xlsx',
             'FileEXT': '.xlsx'},
        ]
        with patch('tracker.jm_portfolios._decrypt', return_value=rows):
            found = jm_portfolios.listing_candidates(
                b'cipher', 4, today=date(2026, 9, 24))
        self.assertEqual([x[2] for x in found], [
            'Monthly Portfolio - JM Small Cap Fund - Aug 31, 2026',
            'Monthly Portfolio - JM Small Cap Fund - July 31, 2026'])
        self.assertTrue(found[0][1].startswith('https://www.jmfinancialmf.com/CMS/'))
        self.assertNotIn('example.com', ''.join(x[1] for x in found))

    def test_discover_requires_both_closed_months(self):
        drops = [{'DownloadCategoryID': 2, 'DownloadSubCategoryID': 4,
                  'SubCategoryName': 'Monthly Portfolio of Schemes'}]
        listing = [{
            'CategoryID': 2, 'SubCategoryID': 4,
            'SubCategoryName': 'Monthly Portfolio of Schemes',
            'Title': 'Monthly Portfolio - JM Small Cap Fund - Aug 31, 2026',
            'FileName': 'CMS/downloads/Portfolio Disclosure/Monthly Portfolio of Schemes/Aug.xlsx',
            'FileEXT': '.xlsx'}]
        calls = []
        def fake_read(url, body=None):
            calls.append((url, body))
            return (b'drop' if 'Drop' in url else b'listing', 'h', 'application/json')
        with patch('tracker.jm_portfolios._decrypt', side_effect=[drops, listing]):
            with self.assertRaisesRegex(ValueError, 'both closed-month'):
                list(jm_portfolios.discover(fake_read, today=date(2026, 9, 24)))
        self.assertEqual(calls[0][1], {'IICategoryID': '2'})
        self.assertEqual(calls[1][1]['IISubCategoryID'], '4')

    def test_decrypt_rejects_invalid_public_api_envelope(self):
        with self.assertRaisesRegex(ValueError, 'invalid encrypted response'):
            jm_portfolios._decrypt(json.dumps({'statusCode': -1, 'data': ''}).encode())

    def test_jm_ccil_repo_reconciles_without_relaxing_other_unknown_rows(self):
        rows = [
            ['JM Financial Mutual Fund','','','','','',''],
            ['','JM Small Cap Fund (An open ended equity scheme predominantly investing in small cap stocks.)','','','','',''],
            ['','Monthly Portfolio Statement for the period ended 31.08.2026','','','','',''],
            ['ISIN','Name of Instrument','Rating/Industry','Quantity','Market Value (In Rs. lakh)','% To Net Assets','Maturity Date'],
            ['', 'EQUITY & EQUITY RELATED','','','','',''],
            ['INE123456789','Alpha Industries Limited','Industrial Products',100,98500,98.5,''],
            ['', 'TREPS / Reverse Repo Investments / Corporate Debt Repo','','','','',''],
            ['', 'CCIL','',1000,1500,1.5,'01-SEP-2026'],
            ['', 'Grand Total','','',100000,100,''],
        ]
        formats = [['General'] * 7 for _ in rows]
        parsed = parse_sheet(rows, formats, 'Jm Small Cap Fund')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'], '2026-08-31')
        self.assertTrue(parsed['complete'])
        self.assertEqual(len(parsed['positions']), 2)
        self.assertEqual(parsed['positions'][1]['name'], 'CCIL')
        self.assertEqual(parsed['positions'][1]['asset_type'], 'Money market')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']), 100.0)
        self.assertAlmostEqual(parsed['aum'], 1000.0)

        bad = [row[:] for row in rows]
        bad[7][1] = 'Unknown Repo Counterparty'
        rejected = parse_sheet(bad, formats, 'Jm Small Cap Fund')
        self.assertFalse(rejected['complete'])
        self.assertIn('Unknown Repo Counterparty', rejected['unknown_rows'])

    def test_v128_scope_and_nightly_wiring(self):
        from tracker import amc_reports
        with patch.object(amc_reports, 'PARSER_VERSION', 'amc-reports-2026-09-v128'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Jm Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Invesco India Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Jm Small Cap Fund',
                'https://www.jmfinancialmf.com/CMS/portfolio.xlsx', 'hash'))
        root = Path(__file__).resolve().parents[1]
        refresh = (root / 'scripts' / 'refresh_amc_reports.py').read_text()
        discovery = (root / 'tracker' / 'amc_discovery.py').read_text()
        self.assertIn("'amc-reports-2026-09-v128'", refresh)
        self.assertIn("amc_discovery.discover('JM Financial')", refresh)
        self.assertIn("latest['positions']>=85", refresh)
        self.assertIn("prior['positions']>=83", refresh)
        self.assertIn("'JM Financial'", discovery.split('ThreadPoolExecutor', 1)[-1])


if __name__ == '__main__':
    unittest.main()
