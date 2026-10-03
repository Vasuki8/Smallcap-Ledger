"""Rejected Kotak responses remain failed, with replayable bounded evidence."""
import base64
from datetime import date, datetime
import hashlib
import json
import unittest
from unittest.mock import patch

from tracker import db
from tracker import midcap_portfolio_batch5 as batch5
from tracker import midcap_portfolio_first_party as batch1


FAMILY = batch5.KOTAK_FAMILY
URL = batch5.KOTAK_URL
LIMIT = 64 * 1024
TODAY = date(2026, 9, 27)


def factsheet():
    # The observed three-column issuer/sector layout, with synthetic weights.
    return b'''<h1>KOTAK MID CAP FUND (ERSTWHILE KNOWN AS KOTAK MIDCAP FUND)</h1>
    <p>Data as on 31st August 2026 unless otherwise specified.</p>
    <p>Folio Count data as on 31st July 2026.</p>
    <table><tr><th>Issuer/Instrument</th><th></th><th>% to Net Assets</th></tr>
    <tr><td>Equity &amp; Equity related</td><td></td><td></td></tr>
    <tr style="font-weight:bold"><td>Finance</td><td></td><td>5.00</td></tr>
    <tr style="fo nt-weight:bold"><td>A Finance Ltd</td><td></td><td>1.00</td></tr>
    <tr><td>B Bank Ltd</td><td></td><td>1.00</td></tr>
    <tr><td>C Industries Ltd</td><td></td><td>1.00</td></tr>
    <tr><td>D Services Ltd</td><td></td><td>1.00</td></tr>
    <tr><td>E Technologies Ltd</td><td></td><td>1.00</td></tr>
    <tr><td>Equity &amp; Equity related - Total</td><td></td><td>5.00</td></tr>
    <tr><td>Triparty Repo</td><td></td><td>95.00</td></tr>
    <tr><td>Grand Total</td><td></td><td>100.00</td></tr></table>'''


class KotakFailureEvidenceTests(unittest.TestCase):
    def collect(self, module, body=None, transport_error=None):
        calls = []

        def fetch(url, **kwargs):
            calls.append(url)
            self.assertEqual(url, URL)
            self.assertIs(kwargs['archive'], False)
            if transport_error:
                raise transport_error
            return body, None, 'text/html; charset=utf-8'

        def forbidden(*args, **kwargs):
            raise AssertionError('Source diagnostics must not archive or write the database')

        with patch.object(db, 'rows', return_value=[{
            'family': FAMILY, 'amc': 'Kotak Mahindra Mutual Fund',
        }]), patch.object(db, 'archive', forbidden), patch.object(db, 'connect', forbidden):
            report = module.collect(fetch_fn=fetch, today=TODAY)
        self.assertEqual(calls, [URL])
        self.assertEqual(report['production_writes'], 0)
        self.assertIs(report['public_export_enabled'], False)
        return report

    def rejected(self, module, body, message):
        report = self.collect(module, body)
        self.assertEqual(report['recovered'] if module is batch5 else len(report['results']), 0)
        row = next(row for row in report['errors'] if row['family'] == FAMILY)
        self.assertIn(message, row['error'])
        self.assertIn('source_sha256', row)
        self.assertEqual(row['source'], URL)
        self.assertEqual(row['source_sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(row['source_bytes'], len(body))
        self.assertEqual(row['source_content_type'], 'text/html; charset=utf-8')
        clock = datetime.fromisoformat(row['source_observed_at'])
        self.assertIsNotNone(clock.tzinfo)
        self.assertLessEqual(clock, datetime.fromisoformat(report['built_at']))
        return json.loads(json.dumps(row))

    def test_both_identity_rejections_retain_exact_non_utf8_bytes(self):
        body = b'<html><title>Unavailable</title>\xff\x00</html>'
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                row = self.rejected(module, body, 'exact staged')
                self.assertTrue(row['source_body_retained'])
                self.assertEqual(row['source_body_encoding'], 'base64')
                self.assertEqual(base64.b64decode(row['source_body_base64'], validate=True), body)
                self.assertEqual(row['source_validation_stage'],
                                 'family_identity' if module is batch1 else 'factsheet_context')

    def test_both_stale_factsheet_rejections_retain_the_rejected_source(self):
        body = factsheet().replace(b'31st August 2026', b'31st July 2026')
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                row = self.rejected(module, body, 'current portfolio date')
                self.assertEqual(base64.b64decode(row['source_body_base64']), body)
                self.assertEqual(row['source_validation_stage'],
                                 'reporting_date' if module is batch1 else 'factsheet_context')

    def test_sector_reconciliation_failure_stays_rejected(self):
        body = factsheet().replace(b'<td>Finance</td><td></td><td>5.00',
                                   b'<td>Finance</td><td></td><td>6.00')
        row = self.rejected(batch5, body, 'Finance weights do not reconcile')
        self.assertEqual(row['source_validation_stage'], 'equity_positions')
        self.assertEqual(base64.b64decode(row['source_body_base64']), body)

    def test_equity_reconciliation_failure_stays_rejected(self):
        body = factsheet().replace(b'- Total</td><td></td><td>5.00',
                                   b'- Total</td><td></td><td>6.00')
        row = self.rejected(batch5, body, 'Equity weights do not reconcile')
        self.assertEqual(row['source_validation_stage'], 'equity_positions')

    def test_conflicting_responsive_tables_stay_rejected(self):
        body = factsheet() + factsheet().replace(b'A Finance Ltd', b'Other Finance Ltd')
        self.rejected(batch5, body, 'Responsive portfolio tables disagree')

    def test_missing_portfolio_table_stays_rejected(self):
        body = factsheet().split(b'<table>')[0]
        row = self.rejected(batch5, body, 'No supported issuer/weight portfolio table')
        self.assertEqual(row['source_validation_stage'], 'equity_positions')

    def test_fewer_than_five_positions_stays_rejected_in_both_batches(self):
        body = factsheet().replace(
            b'<tr><td>E Technologies Ltd</td><td></td><td>1.00</td></tr>', b'')
        body = body.replace(b'5.00', b'4.00')
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                row = self.rejected(module, body, 'need at least 5')
                self.assertEqual(row['source_validation_stage'], 'minimum_positions')

    def test_exact_retention_limit_is_replayable_in_both_batches(self):
        body = b'X' * LIMIT
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                row = self.rejected(module, body, 'exact staged')
                self.assertTrue(row['source_body_retained'])
                self.assertEqual(base64.b64decode(row['source_body_base64']), body)

    def test_larger_body_keeps_full_hash_and_size_without_partial_body(self):
        body = b'X' * (LIMIT + 1)
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                row = self.rejected(module, body, 'exact staged')
                self.assertFalse(row['source_body_retained'])
                self.assertEqual(row['source_body_omitted_reason'], 'exceeds_64_kib_limit')
                self.assertNotIn('source_body_base64', row)
                self.assertNotIn('source_body_encoding', row)

    def test_empty_response_is_retained_as_empty_not_invented_transport_evidence(self):
        for module in (batch1, batch5):
            # BeautifulSoup warns when detecting the encoding of empty bytes.
            # Retention must still distinguish an acquired empty body from none.
            with self.subTest(batch=module.__name__), self.assertLogs('bs4.dammit', level='WARNING'):
                row = self.rejected(module, b'', 'exact staged')
                self.assertTrue(row['source_body_retained'])
                self.assertEqual(row['source_body_base64'], '')

    def test_transport_failure_does_not_invent_acquired_bytes(self):
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                report = self.collect(module, transport_error=TimeoutError('read timed out'))
                row = next(row for row in report['errors'] if row['family'] == FAMILY)
                self.assertEqual(row['error'], 'read timed out')
                self.assertNotIn('source_sha256', row)
                self.assertNotIn('source_bytes', row)
                self.assertNotIn('source_body_base64', row)

    def test_successful_portfolios_keep_existing_partial_scope_and_dates(self):
        for module in (batch1, batch5):
            with self.subTest(batch=module.__name__):
                report = self.collect(module, factsheet())
                row = next(row for row in report['results'] if row['family'] == FAMILY)
                self.assertEqual(row['as_of'], '2026-08-31')
                self.assertEqual(row['positions_observed'], 5)
                self.assertFalse(row['complete'])
                self.assertNotIn('source_body_base64', row)
                if module is batch5:
                    self.assertEqual(row['scope'], 'factsheet_equity_only')
                    self.assertEqual(row['equity_weight_sum'], 5.0)
                    self.assertEqual(row['sectors_checked'], 1)

    def test_other_issuer_rejections_do_not_get_kotak_body_diagnostics(self):
        fetch = lambda *args, **kwargs: (b'<html>Unavailable</html>', None, 'text/html')
        for inspect in (
            lambda: batch5._mahindra_result(fetch, '2026-08-31'),
            lambda: batch1.inspect_family('Canara Robeco Mid Cap Fund', {
                'url': 'https://digitalassets.canararobeco.com/test.html',
                'parser': 'canara', 'scope': 'full_page_portfolio',
            }, fetch_fn=fetch, today=TODAY),
        ):
            with self.assertRaises(ValueError) as error:
                inspect()
            self.assertFalse(hasattr(error.exception, 'source_evidence'))


if __name__ == '__main__':
    unittest.main()
