"""Document periods must be attached to a scheme banner, not page-level prose."""
import unittest
from tracker import midcap_benchmark_documents as docs
from test_midcap_benchmark_document_roles import ABSL, absl


class DocumentPeriodScopeTests(unittest.TestCase):
    def test_bare_heading_does_not_borrow_page_level_month(self):
        body = absl('Benchmark: Nifty Midcap 150 TRI') + b'<p>September 2026</p>'
        self.assertIsNone(docs.parse_source(ABSL, body)['source_document_period'])

    def test_body_heading_does_not_borrow_unscoped_month(self):
        body = b'<html><body>' + absl('Benchmark: Nifty Midcap 150 TRI')
        body += b'<p>September 2026</p></body></html>'
        self.assertIsNone(docs.parse_source(ABSL, body)['source_document_period'])


if __name__ == '__main__':
    unittest.main()
