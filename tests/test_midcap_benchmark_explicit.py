"""Tests for five reviewed explicit Mid Cap benchmark sources."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_explicit as explicit

NOW = datetime(2026, 9, 29, 1, 0, tzinfo=timezone.utc)


class MidCapBenchmarkExplicitTests(unittest.TestCase):
    def test_quant_exact_benchmark_index_field(self):
        body=(
            b"<html><body><h1>quant Mid Cap Fund</h1>"
            b"<div>Benchmark Index</div><div>Nifty Mid Cap 150 TRI</div></body></html>"
        )
        row=explicit.parse_source("Quant Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Mid Cap 150 TRI")
        self.assertEqual(row["benchmark_role"],"primary")
        self.assertFalse(row["benchmark_series_verified"])
        with self.assertRaises(ValueError):
            explicit.parse_source("Quant Mid Cap Fund",body.replace(b"Nifty Mid Cap 150 TRI",b"Nifty 50 TRI"))

    def test_samco_exact_scheme_question_and_answer(self):
        body=(
            b"<html><body><div>Samco Mid Cap Fund</div>"
            b"<div>What is the benchmark for Samco Mid Cap Fund?</div>"
            b"<div>Image: Arrow</div>"
            b"<div>The benchmark for this scheme is the Nifty Midcap 150 Total Returns Index.</div>"
            b"</body></html>"
        )
        row=explicit.parse_source("Samco Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 Total Returns Index")
        with self.assertRaises(ValueError):
            explicit.parse_source("Samco Mid Cap Fund",body.replace(
                b"What is the benchmark for Samco Mid Cap Fund?",
                b"What is the benchmark for Samco Small Cap Fund?",
            ))

    def test_edelweiss_factsheet_requires_about_scheme_benchmark(self):
        text=(
            "Data as on April 30, 2026\n"
            "Benchmark Nifty Midcap 150 TRI\n"
            "About the Scheme\n"
            "Edelweiss Mid Cap Fund\n"
            "An open ended equity scheme predominantly investing in mid cap stocks\n"
            "Additional Benchmark Nifty 50 TRI"
        )
        row=explicit.parse_source("Edelweiss Mid Cap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["source_data_as_of"],"2026-04-30")

    def test_lic_sid_requires_tier_i_role(self):
        text=(
            "SCHEME INFORMATION DOCUMENT\nSECTION I\nLIC MF Mid Cap Fund\n"
            "Benchmark Riskometer\n"
            "As per AMFI Tier I Benchmark i.e. Nifty Midcap 150 TRI\n"
            "Additional Benchmark Nifty 50 TRI"
        )
        row=explicit.parse_source("LIC MF Mid Cap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["reported_benchmarks"],["Nifty Midcap 150 TRI"])
        with self.assertRaises(ValueError):
            explicit.parse_source("LIC MF Mid Cap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text.replace("Tier I Benchmark","Additional Benchmark"))

    def test_inspect_requires_registered_url_media_type_and_records_provenance(self):
        family="Quant Mid Cap Fund"
        body=b"<html><body>quant Mid Cap Fund Benchmark Index Nifty Mid Cap 150 TRI</body></html>"
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            return body,None,"text/html; charset=utf-8"
        row=explicit.inspect_family(family,explicit.SOURCES[family],fetch_fn=fetch,now=NOW)
        self.assertEqual(row["amc"],"quant Mutual Fund")
        self.assertEqual(row["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"],NOW.isoformat())
        self.assertFalse(calls[0][1]["archive"])
        with self.assertRaises(ValueError):
            explicit.inspect_family(family,explicit.SOURCES[family]+"?x=1",fetch_fn=fetch,now=NOW)
        with self.assertRaises(ValueError):
            explicit.inspect_family(family,explicit.SOURCES[family],
                                    fetch_fn=lambda *a,**k:(body,None,"application/pdf"),now=NOW)

    def test_live_preflight_excludes_known_flaky_edelweiss_transport(self):
        self.assertEqual(
            set(explicit.PREFLIGHT_SOURCES),
            {"Quant Mid Cap Fund","Samco Mid Cap Fund","LIC MF Mid Cap Fund"},
        )
        self.assertIn("Edelweiss Mid Cap Fund",explicit.SOURCES)
        self.assertNotIn("Edelweiss Mid Cap Fund",explicit.PREFLIGHT_SOURCES)

    def test_batch2_routes_explicit_sources_and_requires_registered_amc(self):
        staged=[{"family":family,"amc":explicit.AMCS[family]} for family in explicit.SOURCES]
        seen=[]
        def inspector(family,url,**kwargs):
            seen.append(family)
            return {
                "family":family,"amc":explicit.AMCS[family],"status":"recovered",
                "primary_benchmark":"Publisher benchmark",
                "reported_benchmarks":["Publisher benchmark"],
            }
        with patch.object(batch2,"SOURCES",dict(explicit.SOURCES)), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=staged), \
             patch.object(batch2.explicit,"inspect_family",side_effect=inspector):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertEqual(set(seen),set(explicit.SOURCES))
        self.assertEqual(result["recovered"],4)
        self.assertEqual(result["errors"],[])

        wrong=[{"family":"Quant Mid Cap Fund","amc":"Wrong AMC"}]
        with patch.object(batch2,"SOURCES",{"Quant Mid Cap Fund":explicit.SOURCES["Quant Mid Cap Fund"]}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=wrong):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertFalse(result["results"])
        self.assertIn("ownership",result["errors"][0]["error"])


if __name__=="__main__":
    unittest.main()
