"""Tests for staged Mid Cap first-party benchmark audit."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.midcap_benchmark_first_party import PREFLIGHT_SOURCES,SOURCES,extract_benchmarks,inspect_family


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

    def test_new_official_html_sources_are_registered_for_live_preflight(self):
        self.assertEqual(
            PREFLIGHT_SOURCES,
            {
                "Nippon India Growth Mid Cap Fund": SOURCES["Nippon India Growth Mid Cap Fund"],
                "Taurus Mid Cap Fund": SOURCES["Taurus Mid Cap Fund"],
            },
        )

    def test_nippon_and_taurus_shapes_recover_publisher_wording(self):
        fixtures={
            "Nippon India Growth Mid Cap Fund": (
                b"<html><body><h1>Nippon India Growth Mid Cap Fund</h1>"
                b"<div>Benchmark Riskometer</div><div>Nifty Midcap 150 TRI</div></body></html>"
            ),
            "Taurus Mid Cap Fund": (
                b"<html><body><h1>Taurus Mid Cap Fund(G)</h1>"
                b"<div>Benchmark</div><div>Nifty Midcap 150 TRI. Benchmark Index changed w.e.f. 01/12/2021</div>"
                b"</body></html>"
            ),
        }
        for family,body in fixtures.items():
            with self.subTest(family=family):
                row=inspect_family(
                    family,SOURCES[family],
                    fetch_fn=lambda *args,body=body,**kwargs:(body,None,"text/html"),
                )
                self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
                self.assertEqual(row["reported_benchmarks"],["Nifty Midcap 150 TRI"])

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
