"""Tests for Bandhan Mid Cap benchmark evidence."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_bandhan as bandhan
from tracker import midcap_benchmark_batch2 as batch2

NOW=datetime(2026,9,29,16,45,tzinfo=timezone.utc)


def table_text(benchmark="BSE 150 Midcap TRI"):
    return (
        "Performance Table\n"
        "Bandhan Midcap Fund - Regular Plan 18-08-2022 "
        f"{benchmark} 2.66% 0.56% NA NA\n"
        "Bandhan Midcap Fund - Direct Plan 4.22% 0.56% NA NA\n"
        "Bandhan Transportation and Logistics Fund - Regular Plan "
        "27-10-2022 Nifty Transportation and Logistics TRI\n"
    )


class BandhanMidCapBenchmarkTests(unittest.TestCase):
    def test_exact_scheme_block_recovers_primary_benchmark(self):
        row=bandhan.parse_source(
            b"%PDF fixture",
            pdf_text_fn=lambda _:table_text(),
        )
        self.assertEqual(row["family"],bandhan.FAMILY)
        self.assertEqual(row["primary_benchmark"],"BSE 150 Midcap TRI")
        self.assertEqual(row["reported_benchmarks"],["BSE 150 Midcap TRI"])
        self.assertEqual(row["benchmark_role"],"primary")
        self.assertEqual(row["return_variant"],"total_return")
        self.assertEqual(row["scheme_inception_as_of"],"2022-08-18")
        self.assertFalse(row["benchmark_series_verified"])

    def test_both_regular_and_direct_plan_rows_are_required(self):
        with self.assertRaisesRegex(ValueError,"Direct Plan"):
            bandhan.parse_source(
                b"%PDF fixture",
                pdf_text_fn=lambda _:table_text().replace(
                    "Bandhan Midcap Fund - Direct Plan 4.22% 0.56% NA NA\n",""
                ),
            )
        with self.assertRaisesRegex(ValueError,"Regular Plan"):
            bandhan.parse_source(
                b"%PDF fixture",
                pdf_text_fn=lambda _:table_text().replace(
                    "Bandhan Midcap Fund - Regular Plan 18-08-2022 "
                    "BSE 150 Midcap TRI 2.66% 0.56% NA NA\n",""
                ),
            )

    def test_wrong_benchmark_is_rejected_and_identical_repeat_is_not_conflict(self):
        with self.assertRaisesRegex(ValueError,"benchmark value"):
            bandhan.parse_source(
                b"%PDF fixture",
                pdf_text_fn=lambda _:table_text("BSE 250 SmallCap TRI"),
            )
        repeated=table_text().replace(
            "Bandhan Midcap Fund - Direct Plan",
            "BSE 150 Midcap TRI Bandhan Midcap Fund - Direct Plan",
        )
        row=bandhan.parse_source(b"%PDF fixture",pdf_text_fn=lambda _:repeated)
        self.assertEqual(row["primary_benchmark"],"BSE 150 Midcap TRI")

    def test_inspect_requires_exact_url_pdf_and_records_provenance(self):
        body=b"%PDF fixture"
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            return body,None,"application/pdf"
        row=bandhan.inspect_family(
            bandhan.FAMILY,bandhan.SOURCE,
            fetch_fn=fetch,now=NOW,pdf_text_fn=lambda _:table_text(),
        )
        self.assertEqual(row["amc"],bandhan.AMC)
        self.assertEqual(row["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"],NOW.isoformat())
        self.assertFalse(calls[0][1]["archive"])
        with self.assertRaises(ValueError):
            bandhan.inspect_family(
                bandhan.FAMILY,bandhan.SOURCE+"?x=1",
                fetch_fn=fetch,now=NOW,pdf_text_fn=lambda _:table_text(),
            )
        with self.assertRaises(ValueError):
            bandhan.inspect_family(
                bandhan.FAMILY,bandhan.SOURCE,
                fetch_fn=lambda *a,**k:(body,None,"text/html"),
                now=NOW,pdf_text_fn=lambda _:table_text(),
            )

    def test_batch2_routes_bandhan_reader_and_requires_amc_ownership(self):
        staged=[{"family":bandhan.FAMILY,"amc":bandhan.AMC}]
        with patch.object(batch2,"SOURCES",{bandhan.FAMILY:bandhan.SOURCE}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=staged), \
             patch.object(batch2.bandhan,"inspect_family",return_value={
                 "family":bandhan.FAMILY,"amc":bandhan.AMC,"status":"recovered",
                 "primary_benchmark":"BSE 150 Midcap TRI",
                 "reported_benchmarks":["BSE 150 Midcap TRI"],
             }) as inspect:
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"application/pdf"))
        self.assertEqual(result["recovered"],1)
        self.assertEqual(result["errors"],[])
        inspect.assert_called_once()

        wrong=[{"family":bandhan.FAMILY,"amc":"Wrong AMC"}]
        with patch.object(batch2,"SOURCES",{bandhan.FAMILY:bandhan.SOURCE}), \
             patch.object(batch2.invesco,"sources",return_value={}), \
             patch.object(batch2.db,"rows",return_value=wrong):
            result=batch2.collect(fetch_fn=lambda *a,**k:(b"",None,"application/pdf"))
        self.assertFalse(result["results"])
        self.assertIn("ownership",result["errors"][0]["error"])


if __name__=="__main__":
    unittest.main()
