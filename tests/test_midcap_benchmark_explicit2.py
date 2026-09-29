"""Tests for Franklin, UTI, Motilal Oswal and HSBC Mid Cap benchmark sources."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_explicit2 as explicit2

NOW=datetime(2026,9,29,2,0,tzinfo=timezone.utc)


class MidCapBenchmarkExplicit2Tests(unittest.TestCase):
    def test_franklin_reviewed_renamed_scheme_alias_and_unspecified_variant(self):
        body=(
            b"<html><body><h1>Franklin India Mid Cap Fund (Erstwhile Franklin India Prima Fund)</h1>"
            b"<div>As on July 31, 2026</div><div>BENCHMARK: Nifty Midcap 150</div>"
            b"<div>B: Nifty Midcap 150 TRI</div></body></html>"
        )
        row=explicit2.parse_source("Franklin India Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150")
        self.assertEqual(row["return_variant"],"publisher_unspecified")
        self.assertEqual(row["source_data_as_of"],"2026-07-31")
        with self.assertRaises(ValueError):
            explicit2.parse_source(
                "Franklin India Mid Cap Fund",
                body.replace(b"Franklin India Mid Cap Fund",b"Franklin India Small Cap Fund"),
            )

    def test_uti_reviewed_alias_requires_benchmark_index(self):
        body=(
            b"<html><body><h1>UTI Mid Cap Fund</h1><section>Fund Facts "
            b"Benchmark Index Nifty Midcap 150 TRI Special Facilities</section></body></html>"
        )
        row=explicit2.parse_source("UTI - Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["benchmark_role"],"primary")
        with self.assertRaises(ValueError):
            explicit2.parse_source(
                "UTI - Mid Cap Fund",
                body.replace(b"Benchmark Index Nifty Midcap 150 TRI",b"Nifty Midcap 150 TRI"),
            )

    def test_motilal_current_page_requires_explicit_benchmark(self):
        body=(
            b"<html><body><h1>Motilal Oswal Midcap Fund</h1>"
            b"<div>Benchmark Nifty Midcap 150 TRI</div>"
            b"<div>groupName: Nifty 50 TRI (SECONDARY)</div></body></html>"
        )
        row=explicit2.parse_source("Motilal Oswal Midcap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["reported_benchmarks"],["Nifty Midcap 150 TRI"])

    def test_hsbc_scheme_benchmark_is_primary_and_additional_stays_separate(self):
        text=(
            "HSBC Midcap Fund (HMCF) | Product Note [January 2026]\n"
            "Fund / Benchmark (Value of Rs 10,000 invested)\n"
            "Scheme Benchmark (NIFTY Midcap 150 TRI)\n"
            "Additional Benchmark (Nifty 50 TRI)\n"
        )
        row=explicit2.parse_source("HSBC Midcap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text)
        self.assertEqual(row["primary_benchmark"],"NIFTY Midcap 150 TRI")
        self.assertEqual(row["additional_benchmarks"],["Nifty 50 TRI"])
        self.assertEqual(row["source_document_period"],"2026-01")
        with self.assertRaises(ValueError):
            explicit2.parse_source(
                "HSBC Midcap Fund",b"%PDF fixture",
                pdf_text_fn=lambda _:text.replace(
                    "Scheme Benchmark (NIFTY Midcap 150 TRI)",
                    "Additional Benchmark (NIFTY Midcap 150 TRI)",
                ),
            )

    def test_inspect_requires_exact_url_media_type_and_provenance(self):
        family="UTI - Mid Cap Fund"
        body=b"<html><body>UTI Mid Cap Fund Benchmark Index Nifty Midcap 150 TRI</body></html>"
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            return body,None,"text/html; charset=utf-8"
        row=explicit2.inspect_family(family,explicit2.SOURCES[family],fetch_fn=fetch,now=NOW)
        self.assertEqual(row["amc"],"UTI Mutual Fund")
        self.assertEqual(row["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"],NOW.isoformat())
        self.assertFalse(calls[0][1]["archive"])
        with self.assertRaises(ValueError):
            explicit2.inspect_family(family,explicit2.SOURCES[family]+"?x=1",fetch_fn=fetch,now=NOW)
        with self.assertRaises(ValueError):
            explicit2.inspect_family(
                family,explicit2.SOURCES[family],
                fetch_fn=lambda *a,**k:(body,None,"application/pdf"),now=NOW,
            )

    def test_batch2_routes_new_sources_and_checks_amc_ownership(self):
        staged=[{"family":family,"amc":explicit2.AMCS[family]} for family in explicit2.SOURCES]
        seen=[]
        def inspector(family,url,**kwargs):
            seen.append(family)
            return {
                "family":family,"amc":explicit2.AMCS[family],"status":"recovered",
                "primary_benchmark":"Publisher benchmark",
                "reported_benchmarks":["Publisher benchmark"],
            }
        with patch.object(batch2,"SOURCES",dict(explicit2.SOURCES)), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=staged), \
             patch.object(batch2.explicit2,"inspect_family",side_effect=inspector):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertEqual(set(seen),set(explicit2.SOURCES))
        self.assertEqual(result["recovered"],4)
        self.assertEqual(result["errors"],[])

        wrong=[{"family":"UTI - Mid Cap Fund","amc":"Wrong AMC"}]
        with patch.object(batch2,"SOURCES",{"UTI - Mid Cap Fund":explicit2.SOURCES["UTI - Mid Cap Fund"]}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=wrong):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertFalse(result["results"])
        self.assertIn("ownership",result["errors"][0]["error"])


if __name__=="__main__":
    unittest.main()
