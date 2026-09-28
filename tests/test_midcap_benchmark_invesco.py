"""Synthetic fixtures for the reviewed Invesco scheme-detail PDF contract."""
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import importlib
import unittest

FAMILY = 'Invesco India Mid Cap Fund'
NOW = datetime(2026, 9, 28, 15, 0, tzinfo=timezone.utc)
COVER = 'Fact Sheet - August 2026\nScheme Name Page No.\nInvesco India Mid Cap Fund 11'
DESCRIPTION = '(An open ended equity scheme predominantly investing in mid cap stocks)'


def detail(primary='BSE 150 Midcap TRI', facts=None):
    return '\n'.join([
        FAMILY, DESCRIPTION, 'This product is suitable for investors who are seeking* :',
        '*Investors should consult their financial advisers.',
        'SCHEME RISKOMETER SCHEME BENCHMARK BENCHMARK RISKOMETER',
        'As per AMFI Tier I', 'Benchmark i.e.', primary,
        'Investment Objective', 'To generate capital appreciation.',
        'Key Facts', 'NAV As on 31st August, 2026', 'Base Expense Ratio',
        'Benchmark Index', facts if facts is not None else primary,
        'AAuM for the month of', 'August, 2026', 'Fund Manager & Experience',
        'Asset Allocation', 'Equity Holding',
        'Lumpsum Performance', 'Additional Benchmark Nifty 50 TRI',
        'SIP Performance', 'BSE Midcap 150 TRI', '11 of 70',
    ])


def pdf_bytes(pages):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=600, height=900)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): font})})
        lines = [x.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                 for x in text.splitlines()]
        stream = DecodedStreamObject()
        stream.set_data(('BT /F1 9 Tf 12 TL 20 850 Td ' +
                         ' T* '.join(f'({x}) Tj' for x in lines) + ' ET').encode())
        page[NameObject('/Contents')] = stream
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class InvescoBenchmarkTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('tracker.midcap_benchmark_invesco'),
                             'Invesco benchmark source is not implemented')
        return importlib.import_module('tracker.midcap_benchmark_invesco')

    def parse(self, page=None, cover=COVER, pages=None):
        return self.module().parse_pages(pages or [cover, page or detail()], '2026-08')

    def test_recovers_publisher_wording_from_both_primary_roles(self):
        row = self.parse()
        self.assertEqual(row['primary_benchmark'], 'BSE 150 Midcap TRI')
        self.assertEqual(row['reported_benchmarks'], ['BSE 150 Midcap TRI'])
        self.assertEqual(row['benchmark_role'], 'primary')
        self.assertEqual(row['return_variant'], 'total_return')
        self.assertFalse(row['benchmark_series_verified'])

    def test_detail_page_is_located_not_hardcoded(self):
        row = self.parse(pages=[COVER, 'Other page', detail()])
        self.assertEqual(row['source_page'], 3)

    def test_other_fund_and_toc_cannot_supply_identity(self):
        with self.assertRaises(ValueError):
            self.parse(page=detail().replace(FAMILY, 'Invesco India Small Cap Fund'))
        with self.assertRaises(ValueError):
            self.parse(pages=[COVER, 'Benchmark Index\nBSE 150 Midcap TRI'])

    def test_scheme_descriptor_is_required(self):
        with self.assertRaises(ValueError):
            self.parse(page=detail().replace(DESCRIPTION, '(An open ended large & midcap scheme)'))

    def test_duplicate_scheme_detail_pages_are_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(pages=[COVER, detail(), detail()])

    def test_mixed_scheme_heading_is_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(page=detail() + '\nInvesco India Small Cap Fund')

    def test_both_primary_fields_must_agree(self):
        with self.assertRaises(ValueError):
            self.parse(page=detail(facts='Nifty Midcap 150 TRI'))

    def test_whole_values_are_validated_without_truncation(self):
        for bad in ('BSE 150 Midcap TRI Enhanced', 'BSE 150 Midcap TRI + Nifty 50 TRI',
                    'NA', '', 'Awaiting update'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.parse(page=detail(primary=bad))

    def test_additional_or_previous_labels_cannot_supply_primary(self):
        for label in ('Additional Benchmark Index', 'Previous Benchmark Index'):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.parse(page=detail().replace('Benchmark Index', label))
        with self.assertRaises(ValueError):
            self.parse(page=detail().replace('As per AMFI Tier I', 'As per AMFI Tier II'))

    def test_unknown_duplicate_primary_value_cannot_disappear(self):
        with self.assertRaises(ValueError):
            self.parse(page=detail().replace('AAuM for the month of',
                       'Benchmark Index\nUnknown\nAAuM for the month of'))
        with self.assertRaises(ValueError):
            self.parse(page=detail().replace('Investment Objective',
                       'As per AMFI Tier I\nBenchmark i.e.\nUnknown\nInvestment Objective'))

    def test_explicit_role_block_boundaries_are_required(self):
        for boundary in ('SCHEME RISKOMETER SCHEME BENCHMARK BENCHMARK RISKOMETER',
                         'Investment Objective', 'Key Facts', 'AAuM for the month of',
                         'Asset Allocation'):
            with self.subTest(boundary=boundary), self.assertRaises(ValueError):
                self.parse(page=detail().replace(boundary, 'Changed structure'))

    def test_performance_comparators_are_not_promoted(self):
        row = self.parse(page=detail() + '\nNifty 50 TRI\nBenchmark Nifty Midcap 150 TRI')
        self.assertEqual(row['reported_benchmarks'], ['BSE 150 Midcap TRI'])
        self.assertEqual(row['additional_benchmarks'], [])

    def test_unspecified_and_price_variant_are_not_inferred_to_tri(self):
        for value, variant in (('BSE 150 Midcap', 'unspecified'), ('BSE 150 Midcap PRI', 'price_return')):
            with self.subTest(value=value):
                row = self.parse(page=detail(primary=value))
                self.assertEqual(row['primary_benchmark'], value)
                self.assertEqual(row['return_variant'], variant)

    def test_document_period_is_not_effective_or_financial_reporting_date(self):
        row = self.parse()
        self.assertEqual(row['source_document_period'], '2026-08')
        self.assertIsNone(row['source_data_as_of'])
        self.assertIsNone(row['benchmark_effective_as_of'])

    def test_missing_stale_or_conflicting_cover_period_fails(self):
        for cover in ('Invesco Fact Sheet', COVER.replace('August', 'July'),
                      COVER.replace('2026', '2027'), COVER+'\nFact Sheet - July 2026'):
            with self.subTest(cover=cover), self.assertRaises(ValueError):
                self.parse(cover=cover)

    def test_current_url_is_resolved_at_call_time_across_year_boundary(self):
        m = self.module()
        self.assertTrue(m.sources(NOW)[FAMILY].endswith('august-2026.pdf'))
        self.assertTrue(m.sources(datetime(2027, 1, 1, tzinfo=timezone.utc))[FAMILY].endswith('december-2026.pdf'))
        self.assertTrue(m.sources(datetime(2026, 10, 1, tzinfo=timezone.utc))[FAMILY].endswith('september-2026.pdf'))

    def test_unknown_family_or_url_is_rejected_before_fetch(self):
        m = self.module()
        def forbidden(*args, **kwargs): self.fail('Invalid source must not be fetched')
        url = m.sources(NOW)[FAMILY]
        for family, bad in ((FAMILY, url+'?x=1'), (FAMILY, url.replace('august', 'july')),
                            ('Other Fund', url), (FAMILY, url.replace('https:', 'http:'))):
            with self.subTest(family=family, bad=bad), self.assertRaises(ValueError):
                m.inspect_family(family, bad, fetch_fn=forbidden, now=NOW)

    def test_read_only_fetch_keeps_exact_provenance_with_real_pdf_extraction(self):
        m = self.module(); body = pdf_bytes([COVER, 'Other page', detail()]); calls=[]
        def fetch(url, **kw):
            calls.append((url,kw)); return body,None,'application/pdf'
        row = m.inspect_family(FAMILY, m.sources(NOW)[FAMILY], fetch_fn=fetch, now=NOW)
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][1]['archive'])
        self.assertEqual(row['source_sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(row['observed_at'], NOW.isoformat())
        self.assertEqual(row['source_page'], 3)
        self.assertEqual(row['amc'], 'Invesco Mutual Fund')
        self.assertIn('Benchmark Index', row['evidence_excerpt'])

    def test_bad_media_bytes_and_oversize_are_rejected(self):
        m = self.module(); url=m.sources(NOW)[FAMILY]
        for body, typ in ((b'<html>not pdf</html>', 'application/pdf'),
                          (pdf_bytes([COVER,detail()]), 'text/html'),
                          (b'%PDF'+b'x'*(m.MAX_BYTES+1), 'application/pdf'),
                          (b'%PDF not parseable', 'application/pdf')):
            with self.subTest(typ=typ), self.assertRaises(ValueError):
                m.inspect_family(FAMILY,url,fetch_fn=lambda *a,**kw:(body,None,typ),now=NOW)

    def test_no_stale_fallback_when_current_source_fails(self):
        m=self.module(); calls=[]
        def fetch(url,**kw): calls.append(url); raise OSError('source unavailable')
        with self.assertRaises(OSError):
            m.inspect_family(FAMILY,m.sources(NOW)[FAMILY],fetch_fn=fetch,now=NOW)
        self.assertEqual(calls,[m.sources(NOW)[FAMILY]])

    def test_aware_clock_required(self):
        m=self.module()
        for now in (datetime(2026,9,28), '2026-09-28'):
            with self.subTest(now=now), self.assertRaises(ValueError): m.sources(now)

    def test_bounded_nonempty_pdf_page_input(self):
        m=self.module()
        for pages in ([], [''], [COVER,None], [COVER]+['x']*(m.MAX_PAGES+1)):
            with self.subTest(pages=len(pages)), self.assertRaises(ValueError):
                m.parse_pages(pages,'2026-08')

if __name__ == '__main__': unittest.main()
