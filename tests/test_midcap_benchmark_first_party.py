"""Tests for staged Mid Cap first-party benchmark audit."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.midcap_benchmark_first_party import extract_benchmarks,inspect_family


class MidCapBenchmarkFirstPartyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def test_tier1_is_first_and_tri_is_not_inferred(self):
        text="Kotak Mid Cap Fund Benchmark: NIFTY Midcap 150 TRI (Tier 1), Nifty Midcap 100 TRI (Tier 2)"
        values=extract_benchmarks(text)
        self.assertEqual(values[0],"NIFTY Midcap 150 TRI")
        self.assertIn("Nifty Midcap 100 TRI",values)
        self.assertEqual(extract_benchmarks("Franklin India Mid Cap Fund Benchmark(s): Nifty Midcap 150")[0],
                         "Nifty Midcap 150")

    def test_exact_family_required(self):
        def fetch(url,**kwargs):
            body=b"<html><body>Canara Robeco Small Cap Fund Benchmark: BSE 150 Mid Cap TRI</body></html>"
            return body,None,"text/html"
        with self.assertRaisesRegex(ValueError,"exact staged"):
            inspect_family("Canara Robeco Mid Cap Fund",
                           "https://digitalassets.canararobeco.com/test.html",fetch_fn=fetch)

    def test_explicit_midcap_benchmark_is_recovered_read_only(self):
        def fetch(url,**kwargs):
            body=b"<html><body>Canara Robeco Mid Cap Fund\nBENCHMARK : BSE 150 Mid Cap TRI\nas on 31 August 2026</body></html>"
            return body,None,"text/html"
        row=inspect_family("Canara Robeco Mid Cap Fund",
                           "https://digitalassets.canararobeco.com/test.html",fetch_fn=fetch)
        self.assertEqual(row["primary_benchmark"],"BSE 150 Mid Cap TRI")
        self.assertEqual(row["source_data_as_of"],"2026-08-31")


if __name__=="__main__":
    unittest.main()
