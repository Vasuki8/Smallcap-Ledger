"""Tests for reviewed Aditya Birla Sun Life and SBI Mid Cap benchmark sources."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_documents as docs

ABSL = "Aditya Birla Sun Life Midcap Fund"
SBI = "SBI MIDCAP FUND"
NOW = datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc)


def absl(value="Nifty Midcap 150 TRI"):
    return f"""<html><body>
    <h1>Aditya Birla Sun Life Midcap Fund</h1>
    <section><h2>Fund Snapshot</h2><p>Benchmark: {value}</p></section>
    </body></html>""".encode()


def sbi_text(value="Nifty Midcap 150 Index TRI"):
    return (
        "KEY INFORMATION MEMORANDUM "
        "KIM – SBI Midcap Fund "
        "This Key Information Memorandum is dated 26th September, 2026 "
        f"Tier I Benchmark i.e. {value} "
        "Tier II Benchmark Nifty 50 TRI"
    )


class BenchmarkDocumentTests(unittest.TestCase):
    def test_absl_requires_exact_scheme_heading_and_explicit_benchmark(self):
        row = docs.parse_source(ABSL, absl())
        self.assertEqual(row["primary_benchmark"], "Nifty Midcap 150 TRI")
        self.assertEqual(row["reported_benchmarks"], ["Nifty Midcap 150 TRI"])
        self.assertEqual(row["benchmark_role"], "primary")
        self.assertFalse(row["benchmark_series_verified"])
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl().replace(b"Aditya Birla Sun Life Midcap Fund", b"Aditya Birla Sun Life Small Cap Fund"))
        with self.assertRaises(ValueError):
            docs.parse_source(ABSL, absl("Nifty Midcap 150"))

    def test_absl_ignores_unlabelled_or_additional_indices(self):
        body = absl().replace(
            b"</section>",
            b"<p>Additional Benchmark: Nifty 50 TRI</p><p>Nifty Midcap 100 TRI</p></section>",
        )
        row = docs.parse_source(ABSL, body)
        self.assertEqual(row["primary_benchmark"], "Nifty Midcap 150 TRI")
        self.assertEqual(row["additional_benchmarks"], [])

    def test_sbi_requires_kim_identity_and_tier_i_label(self):
        row = docs.parse_source(SBI, b"%PDF fixture", pdf_text_fn=lambda _: sbi_text())
        self.assertEqual(row["primary_benchmark"], "Nifty Midcap 150 Index TRI")
        self.assertEqual(row["source_document_as_of"], "2026-09-26")
        self.assertFalse(row["benchmark_series_verified"])
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b"%PDF fixture", pdf_text_fn=lambda _: sbi_text().replace("SBI Midcap Fund", "SBI Small Cap Fund"))
        with self.assertRaises(ValueError):
            docs.parse_source(SBI, b"%PDF fixture", pdf_text_fn=lambda _: sbi_text().replace("Tier I Benchmark i.e.", "Benchmark"))

    def test_sbi_does_not_promote_tier_ii(self):
        text = sbi_text().replace("Tier I Benchmark i.e. Nifty Midcap 150 Index TRI", "Tier I Benchmark i.e. Nifty Midcap 150 Index TRI Tier II Benchmark Nifty 50 TRI")
        row = docs.parse_source(SBI, b"%PDF fixture", pdf_text_fn=lambda _: text)
        self.assertEqual(row["reported_benchmarks"], ["Nifty Midcap 150 Index TRI"])
        self.assertEqual(row["additional_benchmarks"], [])

    def test_registered_url_content_type_and_provenance_are_strict(self):
        body = absl()
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            return body, None, "text/html; charset=utf-8"
        row = docs.inspect_family(ABSL, docs.SOURCES[ABSL], fetch_fn=fetch, now=NOW)
        self.assertFalse(calls[0][1]["archive"])
        self.assertEqual(row["source_sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(row["observed_at"], NOW.isoformat())
        with self.assertRaises(ValueError):
            docs.inspect_family(ABSL, docs.SOURCES[ABSL] + "?x=1", fetch_fn=fetch, now=NOW)
        with self.assertRaises(ValueError):
            docs.inspect_family(ABSL, docs.SOURCES[ABSL], fetch_fn=lambda *a, **k: (body, None, "application/pdf"), now=NOW)
        with self.assertRaises(ValueError):
            docs.inspect_family(SBI, docs.SOURCES[SBI], fetch_fn=lambda *a, **k: (b"x", None, "text/html"), now=NOW)

    def test_batch_routes_document_sources_and_requires_registered_amc(self):
        staged = [
            {"family": family, "amc": docs.AMCS.get(family, "Legacy AMC")}
            for family in batch2.SOURCES
        ]
        seen = []
        def document_inspector(family, url, **kwargs):
            seen.append(family)
            return {"family": family, "status": "recovered", "primary_benchmark": "Publisher index"}
        def legacy(family, url, **kwargs):
            return {"family": family, "status": "recovered", "primary_benchmark": "Legacy index"}
        with patch.object(batch2.db, "rows", return_value=staged), \
             patch.object(batch2.documents, "inspect_family", side_effect=document_inspector), \
             patch.object(batch2.labeled, "inspect_family", side_effect=legacy), \
             patch.object(batch2, "inspect_family", side_effect=legacy):
            result = batch2.collect(fetch_fn=lambda *a, **k: (b"", None, "text/html"))
        self.assertEqual(set(seen), set(docs.SOURCES))
        self.assertFalse(result["public_export_enabled"])
        self.assertEqual(result["production_writes"], 0)

        wrong = [{"family": ABSL, "amc": "Wrong AMC"}]
        with patch.object(batch2.db, "rows", return_value=wrong):
            result = batch2.collect(fetch_fn=lambda *a, **k: (absl(), None, "text/html"))
        self.assertFalse(result["results"])
        self.assertIn("ownership", result["errors"][0]["error"])


if __name__ == "__main__":
    unittest.main()
