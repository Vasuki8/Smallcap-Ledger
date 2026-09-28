"""Tests for staged Mid Cap structured portfolio batch 2."""
import unittest
from unittest.mock import patch

from tracker.midcap_portfolio_structured import _discover_hdfc,_parse_workbook


class MidCapStructuredPortfolioTests(unittest.TestCase):
    def test_hdfc_discovery_requires_exact_family_and_current_date(self):
        html=b'''<html><body>
        <a href="/files/Monthly-HDFC-Small-Cap-Fund-31-August-2026.xlsx">Monthly HDFC Small Cap Fund - 31 August 2026.xlsx</a>
        <a href="https://files.hdfcfund.com/portfolio/Monthly-HDFC-Mid-Cap-Fund-31-August-2026.xlsx">Monthly HDFC Mid Cap Fund - 31 August 2026.xlsx</a>
        </body></html>'''
        def fetch(url,**kwargs):return html,None,"text/html"
        url=_discover_hdfc("2026-08-31",fetch)
        self.assertIn("Mid-Cap-Fund-31-August-2026.xlsx",url)

    def test_hdfc_discovery_rejects_ambiguous_current_files(self):
        html=b'''<a href="/a/HDFC-Mid-Cap-Fund-31-August-2026.xlsx">Monthly HDFC Mid Cap Fund - 31 August 2026.xlsx</a>
        <a href="/b/HDFC-Mid-Cap-Fund-31-August-2026.xlsx">Monthly HDFC Mid Cap Fund - 31 August 2026.xlsx</a>'''
        def fetch(url,**kwargs):return html,None,"text/html"
        with self.assertRaisesRegex(ValueError,"exactly one"):
            _discover_hdfc("2026-08-31",fetch)

    def test_in_memory_parser_requires_current_exact_snapshot(self):
        sheets=[("Mid Cap",[[1]], [[""]])]
        parsed={"day":"2026-08-31","positions":[{"name":str(i)} for i in range(12)],
                "complete":True,"unknown_rows":[],"aum":123.4}
        with patch("tracker.midcap_portfolio_structured._sheets",return_value=sheets), \
             patch("tracker.midcap_portfolio_structured.parse_sheet",return_value=parsed):
            row=_parse_workbook(b"fixture","HDFC Mid Cap Fund","2026-08-31")
        self.assertEqual(row["positions_observed"],12)
        self.assertTrue(row["complete"])
        parsed["day"]="2026-07-31"
        with patch("tracker.midcap_portfolio_structured._sheets",return_value=sheets), \
             patch("tracker.midcap_portfolio_structured.parse_sheet",return_value=parsed):
            with self.assertRaisesRegex(ValueError,"No exact current"):
                _parse_workbook(b"fixture","HDFC Mid Cap Fund","2026-08-31")


if __name__=="__main__":
    unittest.main()
