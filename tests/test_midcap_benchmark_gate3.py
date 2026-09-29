"""Tests for UTI and ICICI Prudential Mid Cap benchmark documents."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_gate3 as gate3

NOW=datetime(2026,9,29,16,30,tzinfo=timezone.utc)


class MidCapBenchmarkGate3Tests(unittest.TestCase):
    def test_uti_requires_base_benchmark_and_matching_total_return_variant(self):
        text=(
            "UTI Mid Cap Fund\n"
            "HIGHLIGHTS\nBenchmark Nifty Midcap 150\n"
            "The performance of the scheme is benchmarked to the Total Return Variant "
            "of the benchmark index that is Nifty Midcap 150 TRI.\n"
        )
        row=gate3.parse_source("UTI - Mid Cap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["return_variant"],"total_return")
        self.assertEqual(row["source_document_as_of"],"2021-10-29")
        with self.assertRaises(ValueError):
            gate3.parse_source(
                "UTI - Mid Cap Fund",b"%PDF fixture",
                pdf_text_fn=lambda _:text.replace("Nifty Midcap 150 TRI","Nifty Midcap 100 TRI"),
            )

    def test_icici_primary_and_additional_benchmark_roles_are_separate(self):
        text=(
            "ICICI Prudential Midcap Fund\n"
            "Returns of ICICI Prudential Midcap Fund - Growth Option as on August 31, 2024\n"
            "Nifty Midcap 150 TRI (Benchmark)\n"
            "Nifty 50 TRI (Additional Benchmark)\n"
        )
        row=gate3.parse_source("ICICI Prudential Mid Cap Fund",b"%PDF fixture",pdf_text_fn=lambda _:text)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["additional_benchmarks"],["Nifty 50 TRI"])
        self.assertEqual(row["source_data_as_of"],"2024-08-31")
        with self.assertRaises(ValueError):
            gate3.parse_source(
                "ICICI Prudential Mid Cap Fund",b"%PDF fixture",
                pdf_text_fn=lambda _:text.replace(
                    "Nifty Midcap 150 TRI (Benchmark)",
                    "Nifty Midcap 150 TRI (Additional Benchmark)",
                ),
            )

    def test_inspect_requires_exact_registered_url_pdf_and_records_provenance(self):
        family="ICICI Prudential Mid Cap Fund"
        body=b"%PDF fixture"
        text=(
            "ICICI Prudential Midcap Fund\n"
            "Nifty Midcap 150 TRI (Benchmark)\n"
            "Nifty 50 TRI (Additional Benchmark)\n"
        )
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            return body,None,"application/pdf"
        row=gate3.inspect_family(
            family,gate3.SOURCES[family],
            fetch_fn=fetch,now=NOW,pdf_text_fn=lambda _:text,
        )
        self.assertEqual(row["amc"],"ICICI Prudential Mutual Fund")
        self.assertEqual(row["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"],NOW.isoformat())
        self.assertFalse(calls[0][1]["archive"])
        with self.assertRaises(ValueError):
            gate3.inspect_family(
                family,gate3.SOURCES[family]+"?x=1",
                fetch_fn=fetch,now=NOW,pdf_text_fn=lambda _:text,
            )
        with self.assertRaises(ValueError):
            gate3.inspect_family(
                family,gate3.SOURCES[family],
                fetch_fn=lambda *a,**k:(body,None,"text/html"),
                now=NOW,pdf_text_fn=lambda _:text,
            )

    def test_batch2_routes_gate3_sources_and_requires_amc_ownership(self):
        staged=[{"family":family,"amc":gate3.AMCS[family]} for family in gate3.SOURCES]
        seen=[]
        def inspector(family,url,**kwargs):
            seen.append(family)
            return {
                "family":family,"amc":gate3.AMCS[family],"status":"recovered",
                "primary_benchmark":"Publisher benchmark",
                "reported_benchmarks":["Publisher benchmark"],
            }
        with patch.object(batch2,"SOURCES",dict(gate3.SOURCES)), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=staged), \
             patch.object(batch2.gate3,"inspect_family",side_effect=inspector):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"application/pdf"))
        self.assertEqual(set(seen),set(gate3.SOURCES))
        self.assertEqual(result["recovered"],2)
        self.assertEqual(result["errors"],[])

        wrong=[{"family":"UTI - Mid Cap Fund","amc":"Wrong AMC"}]
        with patch.object(batch2,"SOURCES",{"UTI - Mid Cap Fund":gate3.SOURCES["UTI - Mid Cap Fund"]}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=wrong):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"application/pdf"))
        self.assertFalse(result["results"])
        self.assertIn("ownership",result["errors"][0]["error"])


if __name__=="__main__":
    unittest.main()
