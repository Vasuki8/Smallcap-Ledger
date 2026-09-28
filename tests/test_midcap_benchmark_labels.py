"""Synthetic fixtures matching observed AMC label structures; never copied fee/holding values."""
import importlib
import hashlib
import unittest
from datetime import datetime, timezone

AXIS = "Axis Midcap Fund"
MIRAE = "Mirae Asset Midcap Fund"
NOW = datetime(2026, 9, 28, 13, 0, tzinfo=timezone.utc)

def mirae(value="NIFTY Midcap 150 (TRI)"):
    return f'''<html><body><h1>Mirae Asset Midcap Fund</h1>
    <h2>Fund facts</h2><div class="fund_fact_text">
    <span class="test">benchmark index</span><p>{value}</p></div>
    <p>AUM as on August 31, 2026</p></body></html>'''

def axis(value="BSE Midcap 150 TRI", additional="Nifty 50 TRI"):
    return f'''<html><body><h1 class="scheme-name">Axis Mid Cap Fund</h1>
    <div class="since-inception"><label class="benchmark-returns">Benchmark Returns</label>
    <label class="nifty-multicap-text">{value}</label></div>
    <h4>Performance of Axis Mid Cap Fund - Regular Growth as of September 16, 2026</h4>
    <table><tr class="header-title"><th>{value}<br/><span>Benchmark(%)</span></th>
    <th>{additional}<br/><span>Additional Benchmark(%)</span></th>
    <th>{value}<br/><span>Benchmark(₹)</span></th></tr></table></body></html>'''

class LabeledBenchmarkTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("tracker.midcap_benchmark_labels"),
                             "The fund-specific benchmark label parser is not implemented")
        return importlib.import_module("tracker.midcap_benchmark_labels")

    def parse(self, family=MIRAE, text=None):
        return self.module().parse_page(family, (text or mirae()).encode())

    def test_mirae_accepts_only_the_designated_fund_fact(self):
        r=self.parse()
        self.assertEqual(r["primary_benchmark"], "NIFTY Midcap 150 (TRI)")
        self.assertEqual(r["reported_benchmarks"], ["NIFTY Midcap 150 (TRI)"])
        self.assertEqual(r["benchmark_role"], "primary")

    def test_axis_preserves_bse_word_order_and_separates_additional_index(self):
        r=self.parse(AXIS, axis())
        self.assertEqual(r["primary_benchmark"], "BSE Midcap 150 TRI")
        self.assertEqual(r["additional_benchmarks"], ["Nifty 50 TRI"])
        self.assertNotIn("Nifty 50 TRI", r["reported_benchmarks"])

    def test_no_tri_is_added_when_publisher_does_not_state_it(self):
        r=self.parse(text=mirae("NIFTY Midcap 150"))
        self.assertEqual(r["primary_benchmark"], "NIFTY Midcap 150")
        self.assertEqual(r["return_variant"], "unspecified")

    def test_financial_dates_are_not_borrowed_for_benchmark_effective_date(self):
        r=self.parse()
        self.assertIsNone(r["source_data_as_of"])
        self.assertIsNone(r["benchmark_effective_as_of"])

    def test_nav_menu_and_script_family_mentions_cannot_pass_heading_gate(self):
        for html in (mirae().replace("<h1>Mirae Asset Midcap Fund</h1>","<nav><h1>Mirae Asset Midcap Fund</h1></nav>"),
                     mirae().replace("<h1>Mirae Asset Midcap Fund</h1>","<script>Mirae Asset Midcap Fund</script>")):
            with self.subTest(html=html), self.assertRaises(ValueError):self.parse(text=html)

    def test_wrong_scheme_with_target_in_navigation_is_rejected(self):
        html=mirae().replace("<h1>Mirae Asset Midcap Fund</h1>","<nav>Mirae Asset Midcap Fund</nav><h1>Mirae Asset Large &amp; Midcap Fund</h1>")
        with self.assertRaises(ValueError):self.parse(text=html)

    def test_multiple_conflicting_scheme_headings_are_rejected(self):
        with self.assertRaises(ValueError):self.parse(text=mirae()+"<h1>Other Fund</h1>")

    def test_missing_explicit_label_is_rejected_even_when_index_is_present(self):
        with self.assertRaises(ValueError):self.parse(text=mirae().replace("benchmark index","comparison"))

    def test_additional_benchmark_label_is_not_the_primary_label(self):
        with self.assertRaises(ValueError):self.parse(text=mirae().replace("benchmark index","additional benchmark index"))

    def test_duplicate_identical_mirae_cards_are_safe_but_conflicts_reject(self):
        card='<div class="fund_fact_text"><span>benchmark index</span><p>NIFTY Midcap 150 (TRI)</p></div>'
        self.assertEqual(self.parse(text=mirae()+card)["primary_benchmark"],"NIFTY Midcap 150 (TRI)")
        with self.assertRaises(ValueError):self.parse(text=mirae()+card.replace("150","100"))

    def test_missing_and_non_index_values_are_not_success(self):
        for value in ("", "NA", "-", "12.5%", "See factsheet", "NIFTY Midcap 150 (TRI) and Nifty 50 TRI"):
            with self.subTest(value=value),self.assertRaises(ValueError):self.parse(text=mirae(value))

    def test_mirae_card_cannot_have_multiple_values(self):
        with self.assertRaises(ValueError):self.parse(text=mirae().replace("</p></div>","</p><p>Nifty 50 TRI</p></div>"))

    def test_axis_banner_must_match_explicit_primary_columns(self):
        with self.assertRaises(ValueError):self.parse(AXIS,axis().replace('<label class="nifty-multicap-text">BSE Midcap 150 TRI','<label class="nifty-multicap-text">NIFTY Midcap 150 TRI'))

    def test_axis_additional_column_before_primary_does_not_change_role(self):
        html=axis().replace('<tr class="header-title">','<tr class="header-title"><th>Nifty 50 TRI<br/><span>Additional Benchmark(%)</span></th>')
        self.assertEqual(self.parse(AXIS,html)["primary_benchmark"],"BSE Midcap 150 TRI")

    def test_axis_requires_primary_percentage_and_rupee_labels(self):
        with self.assertRaises(ValueError):self.parse(AXIS,axis().replace('Benchmark(₹)','Comparison(₹)'))

    def test_axis_requires_exact_performance_family_heading(self):
        with self.assertRaises(ValueError):self.parse(AXIS,axis().replace('Performance of Axis Mid Cap Fund','Performance of Axis Small Cap Fund'))

    def test_axis_rejects_conflicting_responsive_tables(self):
        html=axis()+ '<table><tr class="header-title"><th>NIFTY Midcap 150 TRI<span>Benchmark(%)</span></th></tr></table>'
        with self.assertRaises(ValueError):self.parse(AXIS,html)

    def test_axis_ignores_historical_prose_as_primary_evidence(self):
        html=axis()+"<p>January performance (Benchmark - NIFTY Midcap 100 TRI).</p>"
        self.assertEqual(self.parse(AXIS,html)["primary_benchmark"],"BSE Midcap 150 TRI")

    def test_unknown_family_fails_before_fetch(self):
        m=self.module()
        def fetch(*a,**kw):self.fail("Must not fetch an unregistered family")
        with self.assertRaises(ValueError):m.inspect_family("Unknown Fund","https://example.com",fetch_fn=fetch,now=NOW)

    def test_exact_registered_url_is_required_before_fetch(self):
        m=self.module()
        def fetch(*a,**kw):self.fail("Must not fetch a nonregistered URL")
        with self.assertRaises(ValueError):m.inspect_family(MIRAE,m.SOURCES[MIRAE]+"?other=1",fetch_fn=fetch,now=NOW)

    def test_fetch_is_read_only_and_retains_exact_source_provenance(self):
        m=self.module(); body=mirae().encode(); calls=[]
        def fetch(url,**kwargs):calls.append((url,kwargs));return body,None,"text/html; charset=utf-8"
        r=m.inspect_family(MIRAE,m.SOURCES[MIRAE],fetch_fn=fetch,now=NOW)
        self.assertFalse(calls[0][1]["archive"])
        self.assertEqual(r["source_sha256"],hashlib.sha256(body).hexdigest())
        self.assertEqual(r["observed_at"],NOW.isoformat())
        self.assertEqual(r["status"],"recovered")
        self.assertEqual(r["source_heading"],MIRAE)
        self.assertIn("benchmark index",r["evidence_excerpt"].lower())
        self.assertIsNone(r["benchmark_effective_as_of"])
        self.assertFalse(r["benchmark_series_verified"])

    def test_fetch_rejects_unexpected_content_and_oversized_responses(self):
        m=self.module()
        for body,typ in ((b'{}',"application/json"),(b'%PDF','application/pdf'),(b'x'*(m.MAX_BYTES+1),'text/html')):
            with self.subTest(typ=typ),self.assertRaises(ValueError):
                m.inspect_family(MIRAE,m.SOURCES[MIRAE],fetch_fn=lambda *a,**kw:(body,None,typ),now=NOW)

    def test_naive_evaluation_clock_is_rejected(self):
        m=self.module()
        with self.assertRaises(ValueError):
            m.inspect_family(MIRAE,m.SOURCES[MIRAE],fetch_fn=lambda *a,**kw:(mirae().encode(),None,'text/html'),now=datetime(2026,9,28))

if __name__=="__main__": unittest.main()
