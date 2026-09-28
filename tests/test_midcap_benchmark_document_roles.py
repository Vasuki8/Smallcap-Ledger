"""Adversarial primary-role tests; synthetic disclosures, not financial records."""
import unittest
from tracker import midcap_benchmark_documents as docs

ABSL = 'Aditya Birla Sun Life Midcap Fund'
SBI = 'SBI MIDCAP FUND'


def absl(*rows):
    return ('<h1>Aditya Birla Sun Life Midcap Fund</h1>'
            '<table><tr><td><strong>Fund Snapshot</strong></td></tr>'
            + ''.join(f'<tr><td>{row}</td></tr>' for row in rows) + '</table>').encode()


def sbi(*rows):
    return ('KIM – SBI Midcap Fund\nAsset Management Company: SBI Funds Management Ltd.\n'
            'KEY INFORMATION MEMORANDUM\nBenchmark Riskometer\n'
            + '\n'.join(rows) + '\n*Investors should consult their financial advisers.')


class BenchmarkDocumentRoleTests(unittest.TestCase):
    def test_absl_only_additional_label_cannot_be_primary(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Additional Benchmark: Nifty Midcap 150 TRI'))

    def test_absl_historical_label_cannot_be_primary(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Previous Benchmark: Nifty Midcap 150 TRI'))

    def test_absl_conflicting_primary_disclosures_fail_closed(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI',
                                         'Benchmark: Nifty Midcap 100 TRI'))

    def test_absl_unknown_duplicate_primary_does_not_disappear(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI',
                                         'Benchmark: Awaiting update'))

    def test_absl_compound_value_cannot_be_truncated(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI + Nifty 50 TRI'))

    def test_absl_expected_name_prefix_cannot_be_truncated(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI Enhanced'))

    def test_sbi_conflicting_tier_i_disclosures_fail_closed(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI',
                'Tier I Benchmark i.e. Nifty Midcap 100 Index TRI'))

    def test_sbi_unknown_duplicate_tier_i_does_not_disappear(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI',
                'Tier I Benchmark i.e. Awaiting update'))

    def test_valid_absl_primary_still_works(self):
        self.assertEqual(docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI'))[
            'primary_benchmark'], 'Nifty Midcap 150 TRI')

    def test_valid_sbi_primary_still_works(self):
        row = docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
            'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI'))
        self.assertEqual(row['primary_benchmark'], 'Nifty Midcap 150 Index TRI')
        self.assertFalse(row['benchmark_series_verified'])

    def test_absl_snapshot_table_is_required(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI').replace(
                b'Fund Snapshot', b'Past Performance'))

    def test_absl_primary_cannot_come_from_an_unrelated_table(self):
        body = absl('Additional Benchmark: Nifty Midcap 150 TRI')
        body += b'<table><tr><td>Benchmark: Nifty Midcap 150 TRI</td></tr></table>'
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, body)

    def test_absl_wrapped_additional_role_cannot_be_promoted(self):
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl('Additional <strong>Benchmark:</strong>Nifty Midcap 150 TRI'))

    def test_absl_duplicate_snapshot_tables_are_ambiguous(self):
        body = absl('Benchmark: Nifty Midcap 150 TRI')
        table = body[body.index(b'<table>'):]
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, body + table)

    def test_absl_identical_primary_rows_do_not_create_conflict(self):
        row = docs.parse_source(ABSL, absl('Benchmark: Nifty Midcap 150 TRI',
                                          'Benchmark: Nifty Midcap 150 TRI'))
        self.assertEqual(row['primary_benchmark'], 'Nifty Midcap 150 TRI')

    def test_absl_additional_and_primary_in_separate_cells_keep_roles(self):
        row = docs.parse_source(ABSL, absl('Additional Benchmark: Nifty 50 TRI',
                                          '<strong>Benchmark:</strong>Nifty Midcap 150 TRI'))
        self.assertEqual(row['reported_benchmarks'], ['Nifty Midcap 150 TRI'])

    def test_absl_mixed_scheme_headings_are_rejected(self):
        body = absl('Benchmark: Nifty Midcap 150 TRI')
        body += b'<h2>Aditya Birla Sun Life Small Cap Fund</h2>'
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, body)

    def test_absl_exact_heading_period_is_preserved_without_borrowing_nav_date(self):
        body = absl('Benchmark: Nifty Midcap 150 TRI').replace(
            b'<h1>Aditya Birla Sun Life Midcap Fund</h1>',
            b'<div><h2>Aditya Birla Sun Life Midcap Fund</h2><p><strong>July 2026</strong></p></div>')
        body += b'<p>NAV as on September 25, 2026</p>'
        row = docs.parse_source(ABSL, body)
        self.assertEqual(row.get('source_document_period'), '2026-07')
        self.assertIsNone(row['benchmark_effective_as_of'])
        self.assertIsNone(row['source_data_as_of'])

    def test_sbi_primary_compound_value_is_not_truncated(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI + Nifty 50 TRI'))

    def test_sbi_benchmark_name_suffix_is_not_truncated(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI Enhanced'))

    def test_sbi_historical_tier_i_label_is_not_primary(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Previous Tier I Benchmark i.e. Nifty Midcap 150 Index TRI'))

    def test_sbi_duplicate_identical_tier_i_blocks_are_ambiguous(self):
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: sbi(
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI',
                'Tier I Benchmark i.e. Nifty Midcap 150 Index TRI'))

    def test_sbi_riskometer_scope_is_required(self):
        text = sbi('Tier I Benchmark i.e. Nifty Midcap 150 Index TRI').replace(
            'Benchmark Riskometer', 'Historical Comparison')
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: text)

    def test_sbi_explicit_block_end_is_required(self):
        text = sbi('Tier I Benchmark i.e. Nifty Midcap 150 Index TRI').split('*Investors')[0]
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: text)

    def test_sbi_line_wrapping_is_accepted(self):
        text = sbi('Tier I\nBenchmark i.e. Nifty Midcap 150\nIndex TRI')
        row = docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: text)
        self.assertEqual(row['primary_benchmark'], 'Nifty Midcap 150 Index TRI')
        self.assertEqual(row.get('source_page'), 1)

    def test_sbi_other_kim_heading_cannot_hide_beside_exact_heading(self):
        text = sbi('Tier I Benchmark i.e. Nifty Midcap 150 Index TRI')
        text += '\nKIM – SBI Small Cap Fund'
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b'%PDF fixture', pdf_text_fn=lambda _: text)


    def test_real_pdf_text_extraction_preserves_scope_and_rejects_compounds(self):
        from io import BytesIO
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        for suffix in ('', ' + Nifty 50 TRI'):
            with self.subTest(suffix=suffix):
                writer = PdfWriter()
                page = writer.add_blank_page(width=600, height=800)
                font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                         NameObject('/Subtype'): NameObject('/Type1'),
                                         NameObject('/BaseFont'): NameObject('/Helvetica')})
                page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
                    DictionaryObject({NameObject('/F1'): font})})
                text = sbi('Tier I Benchmark i.e. Nifty Midcap 150 Index TRI' + suffix)
                text = text.replace('–', '-')
                lines = [line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                         for line in text.splitlines()]
                stream = DecodedStreamObject()
                stream.set_data(('BT /F1 10 Tf 12 TL 50 700 Td ' +
                                 ' T* '.join(f'({line}) Tj' for line in lines) + ' ET').encode())
                page[NameObject('/Contents')] = stream
                output = BytesIO()
                writer.write(output)
                if suffix:
                    with self.assertRaises(ValueError):
                        docs.parse_source(SBI, output.getvalue())
                else:
                    row = docs.parse_source(SBI, output.getvalue())
                    self.assertEqual(row['source_page'], 1)
                    self.assertEqual(row['primary_benchmark'], 'Nifty Midcap 150 Index TRI')

    def test_combined_report_retains_exact_inspection_evidence(self):
        from datetime import datetime, timezone
        from tracker.midcap_benchmark_readiness import reconcile
        body = absl('Benchmark: Nifty Midcap 150 TRI')
        now = datetime(2026, 9, 28, tzinfo=timezone.utc)
        item = docs.inspect_family(ABSL, docs.SOURCES[ABSL], now=now,
            fetch_fn=lambda *a, **kw: (body, None, 'text/html'))
        result = reconcile({ABSL: docs.AMCS[ABSL]}, {'results': [item]})
        proof = result['families_detail'][0]['source_evidence']
        self.assertEqual(proof, item)
        self.assertEqual(proof['parser_version'], 'explicit-benchmark-documents-v2')
        self.assertFalse(result['public_export_enabled'])
        self.assertFalse(proof['benchmark_series_verified'])


if __name__ == '__main__':
    unittest.main()
