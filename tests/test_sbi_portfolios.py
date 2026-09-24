"""SBI public listing, exact ownership and explicit-margin reconciliation."""
import copy
import io
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import openpyxl
from tracker import amc_discovery, amc_reports, db, disclosures, sbi_portfolios as sbi
from tracker.portfolio_parser import parse_sheet
from scripts import refresh_sbi_portfolios as upgrade


def link(title='SBI SMALL CAP FUND MONTHLY PORTFOLIO - AUGUST 2026',
         url='https://www.sbimf.com/docs/default-source/scheme-portfolios/small-cap-august.xlsx?sfvrsn=version_2'):
    return f'<tr><td><a href="{url}">{title}</a></td><td><a href="{url}">Download</a></td></tr>'


def workbook_rows():
    # Synthetic values, preserving the real SBI workbook's column geometry.
    rows = [
        [None, None, 'SBI Mutual Fund', '346'],
        [None, None, 'SCHEME NAME :', 'SBI Smallcap Fund'],
        [None, None, 'PORTFOLIO STATEMENT AS ON :', datetime(2026, 8, 31)],
        [None, None, 'Name of the Instrument / Issuer', 'ISIN', 'Rating / Industry^',
         'Quantity', 'Market value\n(Rs. in Lakhs)', '% to AUM'],
        [None, None, 'EQUITY & EQUITY RELATED'],
        [None, '100001', 'Example Industries Ltd.', 'INE000A01011', 'Industrials', 20, 8800, 88],
        [None, None, 'Total', None, None, None, 8800, 88],
        [None, None, 'TREPS / Reverse Repo Investments'],
        [None, '109260100', 'TREPS', None, None, None, 1100, 11],
        [None, None, 'Total', None, None, None, 1100, 11],
        [None, None, 'Margin amount for Derivative positions', None, None, None, 200, 2],
        [None, None, 'Net Receivables / Payables', None, None, None, -100, -1],
        [None, None, 'Total', None, None, None, 100, 1],
        [None, None, 'GRAND TOTAL (AUM)', None, None, None, 10000, 100],
        [None, None, 'Gross Notional Value of contracts where futures were bought', None, None, 900000],
    ]
    rows = [r + [None] * (8 - len(r)) for r in rows]
    return rows, [['General'] * 8 for _ in rows]


class SbiPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(db, 'DATA', Path(self.tmp.name))
        self.patch.start()
        db.init()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_listing_requires_exact_scheme_period_and_registered_workbook(self):
        good = link()
        html = good + good + link('SBI NIFTY Smallcap 250 Index Fund MONTHLY PORTFOLIO - AUGUST 2026')
        html += link('SBI Nifty Small Cap 250 ETF MONTHLY PORTFOLIO - AUGUST 2026')
        html += link('SBI SMALL CAP FUND MONTHLY PORTFOLIO - SEPTEMBER 2026')
        html += link(url='https://example.org/sbi.xlsx')
        html += link(url='https://www.sbimf.com/portfolio.pdf')
        html += link('SBI SMALL CAP FUND MONTHLY PORTFOLIO - Nonesuch 2026')
        rows = sbi.listing_candidates(html, 2026, 8)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], sbi.FAMILY)
        self.assertTrue(rows[0][1].endswith('?sfvrsn=version_2'))

    def test_discovery_queries_only_two_closed_months_and_keeps_empty_latest(self):
        requests = []
        def read(url, body):
            requests.append((url, body))
            text = '' if body['PSMonth'] == 'August' else link(
                'SBI SMALL CAP FUND MONTHLY PORTFOLIO - JULY 2026')
            return text.encode(), 'hash', 'text/html'
        self.assertEqual(len(list(sbi.discover(read, date(2026, 9, 24)))), 1)
        self.assertEqual([r[1]['PSMonth'] for r in requests], ['August', 'July'])
        self.assertTrue(all(r[0] == sbi.ENDPOINT and r[1]['FundId'] == 0
                            and r[1]['PSFrequency'] == 'Monthly' for r in requests))
        self.assertEqual(list(sbi.closed_months(date(2026, 1, 1))), [(2025, 12), (2025, 11)])
        with self.assertRaises(ValueError):
            list(sbi.discover(lambda *a, **k: (b'', 'h', ''), date(2026, 9, 24)))

    def test_sbi_is_wired_into_nightly_discovery(self):
        with patch('tracker.sbi_portfolios.discover', return_value=iter([('family', 'url', 'title')])) as mock:
            self.assertEqual(list(amc_discovery.discover('SBI')), [('family', 'url', 'title')])
            mock.assert_called_once_with(amc_discovery.read)
        seen = []
        with patch.object(amc_discovery, 'discover', side_effect=lambda amc: seen.append(amc) or []):
            amc_discovery.update()
        self.assertIn('SBI', seen)

    def test_explicit_margin_and_negative_receivables_reconcile_without_notional(self):
        rows, formats = workbook_rows()
        parsed = parse_sheet(rows, formats, sbi.FAMILY)
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['day'], '2026-08-31')
        self.assertEqual(parsed['aum'], 100)
        self.assertEqual(len(parsed['positions']), 4)
        self.assertEqual(sum(p['weight'] for p in parsed['positions']), 100)
        margin = next(p for p in parsed['positions'] if p['name'].startswith('Margin'))
        self.assertEqual(margin['asset_type'], 'Cash and net current assets')
        self.assertEqual(parsed['positions'][0]['quantity'], 20)
        self.assertFalse(any('Notional' in p['name'] for p in parsed['positions']))

    def test_margin_rule_stays_narrow_and_incomplete_sources_stay_partial(self):
        rows, formats = workbook_rows()
        for change in ('unknown', 'missing', 'value', 'weight', 'duplicate'):
            changed = copy.deepcopy(rows)
            if change == 'unknown': changed[10][2] = 'Unreviewed margin exposure'
            if change == 'missing': changed[10] = [None] * 8
            if change == 'value': changed[10][6] = 500
            if change == 'weight': changed[10][7] = 9
            if change == 'duplicate': changed.insert(6, changed[5][:])
            with self.subTest(change=change):
                self.assertFalse(parse_sheet(changed, [['General'] * 8 for _ in changed], sbi.FAMILY)['complete'])
        wrong = copy.deepcopy(rows); wrong[1][3] = 'SBI Nifty Smallcap 250 Index Fund'
        self.assertIsNone(parse_sheet(wrong, formats, sbi.FAMILY))
        other = copy.deepcopy(rows); other[1][3] = 'Other Small Cap Fund'
        self.assertFalse(parse_sheet(other, formats, 'Other Small Cap Fund')['complete'])

    def test_scoped_replay_preserves_old_extraction_and_is_idempotent(self):
        rows, _ = workbook_rows()
        book = openpyxl.Workbook(); sheet = book.active
        for row in rows: sheet.append(row)
        output = io.BytesIO(); book.save(output); body = output.getvalue()
        digest = db.archive(body); url = sbi.listing_candidates(link(), 2026, 8)[0][1]
        amc_reports.init()
        with db.connect() as c:
            c.execute('INSERT INTO document_extractions VALUES(?,?,?,?,?,?,?,?)',
                      (sbi.FAMILY, digest, amc_reports.PARSER_VERSION, url, 'unrecognized', 0, 'old parser', db.now()))
        with patch.object(amc_discovery, 'read', return_value=(body, digest, 'spreadsheet')):
            self.assertEqual(amc_discovery.store_report('SBI', sbi.FAMILY, url), 5)
            self.assertEqual(amc_discovery.store_report('SBI', sbi.FAMILY, url), 5)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM portfolios')['n'], 1)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_extractions')['n'], 2)
        self.assertEqual(db.one('SELECT complete FROM portfolios')['complete'], 1)
        with patch.object(amc_discovery, 'read', return_value=(b'<html>Unavailable</html>', 'bad', 'text/html')):
            with self.assertRaises(ValueError):
                amc_discovery.store_report('SBI', sbi.FAMILY, url)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions')['n'], 1)

    def test_upgrade_failure_does_not_mark_success_or_remove_existing_snapshot(self):
        disclosures.portfolio(sbi.FAMILY, '2026-07-31',
            [{'name': 'retained', 'weight': 10, 'asset_type': 'Equity'}], False, 'old-source', 'old-hash')
        with patch.object(amc_discovery, 'discover', side_effect=ValueError('source unavailable')):
            self.assertFalse(upgrade.run())
        self.assertFalse(db.setting(upgrade.UPGRADE_KEY, False))
        self.assertEqual(db.one('SELECT as_of FROM portfolios')['as_of'], '2026-07-31')
        self.assertEqual(db.one('SELECT status FROM jobs ORDER BY id DESC')['status'], 'partial')

    def test_upgrade_requires_current_complete_and_stops_after_success(self):
        url = sbi.listing_candidates(link(), 2026, 8)[0][1]
        def store(*args):
            disclosures.portfolio(sbi.FAMILY, '2026-08-31',
                [{'name': 'test', 'weight': 100, 'asset_type': 'Equity'}], True, url, 'hash')
            return 1
        with patch.object(amc_discovery, 'discover', return_value=[(sbi.FAMILY, url, 'monthly')]), \
             patch.object(amc_discovery, 'store_report', side_effect=store) as save, \
             patch.object(upgrade, 'expected_portfolio_as_of', return_value='2026-08-31'):
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(save.call_count, 1)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY))
