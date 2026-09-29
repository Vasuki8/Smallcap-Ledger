"""Tests for reviewed ITI and JM Mid Cap benchmark sources."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_iti_jm as iti_jm

NOW=datetime(2026,9,29,3,0,tzinfo=timezone.utc)


class MidCapBenchmarkItiJmTests(unittest.TestCase):
    def test_iti_requires_exact_scheme_and_benchmark_field(self):
        body=(
            b"<html><body><h1>ITI Mid Cap Fund</h1>"
            b"<div>Benchmark: Nifty Midcap 150 TRI</div>"
            b"<div>Additional Benchmark: Nifty 50 TRI</div>"
            b"<div>Data is as of August 31, 2026</div></body></html>"
        )
        row=iti_jm.parse_source("ITI Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["additional_benchmarks"],["Nifty 50 TRI"])
        self.assertEqual(row["source_data_as_of"],"2026-08-31")
        with self.assertRaises(ValueError):
            iti_jm.parse_source(
                "ITI Mid Cap Fund",
                body.replace(b"ITI Mid Cap Fund",b"ITI Large Cap Fund"),
            )

    def test_jm_reviewed_alias_and_primary_role(self):
        body=(
            b"<html><body><h1>JM Midcap Fund</h1>"
            b"<div>Benchmark Index: Nifty Midcap 150 TRI</div>"
            b"<div>Additional Benchmark Index: Nifty 50 TRI</div></body></html>"
        )
        row=iti_jm.parse_source("JM Mid Cap Fund",body)
        self.assertEqual(row["primary_benchmark"],"Nifty Midcap 150 TRI")
        self.assertEqual(row["additional_benchmarks"],["Nifty 50 TRI"])
        with self.assertRaises(ValueError):
            iti_jm.parse_source(
                "JM Mid Cap Fund",
                body.replace(b"JM Midcap Fund",b"JM Small Cap Fund"),
            )

    def test_jm_additional_benchmark_cannot_replace_primary(self):
        body=(
            b"<html><body>JM Midcap Fund "
            b"Additional Benchmark Index: Nifty 50 TRI</body></html>"
        )
        with self.assertRaisesRegex(ValueError,"Benchmark Index"):
            iti_jm.parse_source("JM Mid Cap Fund",body)

    def test_inspect_requires_exact_url_html_and_records_provenance(self):
        family="ITI Mid Cap Fund"
        body=b"<html><body>ITI Mid Cap Fund Benchmark: Nifty Midcap 150 TRI</body></html>"
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            return body,None,"text/html; charset=utf-8"
        row=iti_jm.inspect_family(family,iti_jm.SOURCES[family],fetch_fn=fetch,now=NOW)
        self.assertEqual(row["amc"],"ITI Mutual Fund")
        self.assertEqual(row["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"],NOW.isoformat())
        self.assertFalse(calls[0][1]["archive"])
        with self.assertRaises(ValueError):
            iti_jm.inspect_family(family,iti_jm.SOURCES[family]+"?x=1",fetch_fn=fetch,now=NOW)
        with self.assertRaises(ValueError):
            iti_jm.inspect_family(
                family,iti_jm.SOURCES[family],
                fetch_fn=lambda *a,**k:(body,None,"application/pdf"),now=NOW,
            )

    def test_batch2_routes_iti_jm_and_checks_amc_ownership(self):
        staged=[{"family":family,"amc":iti_jm.AMCS[family]} for family in iti_jm.SOURCES]
        seen=[]
        def inspector(family,url,**kwargs):
            seen.append(family)
            return {
                "family":family,"amc":iti_jm.AMCS[family],"status":"recovered",
                "primary_benchmark":"Publisher benchmark",
                "reported_benchmarks":["Publisher benchmark"],
            }
        with patch.object(batch2,"SOURCES",dict(iti_jm.SOURCES)), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=staged), \
             patch.object(batch2.iti_jm,"inspect_family",side_effect=inspector):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertEqual(set(seen),set(iti_jm.SOURCES))
        self.assertEqual(result["recovered"],2)
        self.assertEqual(result["errors"],[])

        wrong=[{"family":"JM Mid Cap Fund","amc":"Wrong AMC"}]
        with patch.object(batch2,"SOURCES",{"JM Mid Cap Fund":iti_jm.SOURCES["JM Mid Cap Fund"]}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=wrong):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"text/html"))
        self.assertFalse(result["results"])
        self.assertIn("ownership",result["errors"][0]["error"])


if __name__=="__main__":
    unittest.main()
