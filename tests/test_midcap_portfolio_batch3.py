"""Tests for staged Mid Cap structured portfolio batch 3."""
import unittest
from datetime import date
from unittest.mock import patch

from tracker.midcap_portfolio_batch3 import _sbi_source,_scan_zip_for_family


class MidCapPortfolioBatch3Tests(unittest.TestCase):
    def test_sbi_source_selects_only_active_midcap_not_large_or_index(self):
        html=b'''<a href="/docs/sbi-large-midcap-fund-monthly-portfolio---august-2026.xlsx">SBI LARGE & MIDCAP FUND MONTHLY PORTFOLIO - AUGUST 2026</a>
        <a href="/docs/sbi-midcap-fund-monthly-portfolio---august-2026.xlsx">SBI MIDCAP FUND MONTHLY PORTFOLIO - AUGUST 2026</a>
        <a href="/docs/sbi-nifty-midcap-150-index-fund-monthly-portfolio---august-2026.xlsx">SBI NIFTY Midcap 150 Index Fund MONTHLY PORTFOLIO - AUGUST 2026</a>'''
        def fetch(url,**kwargs):return html,None,"text/html"
        with patch("tracker.midcap_portfolio_batch3.disclosures.official_publication_url",return_value=True):
            source,title=_sbi_source("2026-08-31",fetch)
        self.assertIn("sbi-midcap-fund-monthly",source)
        self.assertEqual(title,"SBI MIDCAP FUND MONTHLY PORTFOLIO - AUGUST 2026")

    def test_uti_midcap_rows_accepts_exact_all_scheme_block(self):
        from tracker.midcap_portfolio_batch3 import _uti_midcap_rows
        rows=[
            ["SCHEME: UTI MID CAP FUND",None,None,None,None,None,None,None],
            ["Portfolio as on 31/08/2026","Market value in Lacs",None,None,None,None,None,None],
            ["Name","Industry",None,"Market Value","% TO NAV",None,None,"ISIN"],
            ["EQ - Alpha Limited","Industrials",None,100,2.5,None,None,"INE000A01001"],
            ["EQ - Beta Limited","Banks",None,90,2.0,None,None,"INE000A01002"],
            ["EQ - Gamma Limited","IT",None,80,1.8,None,None,"INE000A01003"],
            ["EQ - Delta Limited","Finance",None,70,1.6,None,None,"INE000A01004"],
            ["EQ - Epsilon Limited","Retail",None,60,1.4,None,None,"INE000A01005"],
            ["TOTAL : UTI MID CAP FUND",None,None,123456,None,None,None,None],
        ]
        result=_uti_midcap_rows(rows,"2026-08-31")
        self.assertIsNotNone(result)
        self.assertEqual(result["positions_observed"],5)
        self.assertFalse(result["complete"])
        self.assertEqual(result["published_scheme_name"],"UTI MID CAP FUND")

    def test_zip_scan_requires_one_strong_exact_family(self):
        import io,zipfile
        content=io.BytesIO()
        with zipfile.ZipFile(content,"w") as z:
            z.writestr("Other.xlsx",b"PKother")
            z.writestr("Mid.xlsx",b"PKmid")
        parsed={"day":"2026-08-31","positions":[{"name":str(i)} for i in range(10)],
                "positions_observed":10,"complete":True,"unknown_rows":[]}
        def fake_parse(workbook,family,expected):
            if workbook==b"PKmid":
                return parsed
            raise ValueError("wrong family")
        with patch("tracker.midcap_portfolio_batch3._parse_workbook",side_effect=fake_parse):
            entry,workbook,row=_scan_zip_for_family(
                content.getvalue(),"ICICI Prudential Mid Cap Fund","2026-08-31","fixture")
        self.assertEqual(entry,"Mid.xlsx")
        self.assertEqual(workbook,b"PKmid")
        self.assertTrue(row["complete"])


if __name__=="__main__":
    unittest.main()
