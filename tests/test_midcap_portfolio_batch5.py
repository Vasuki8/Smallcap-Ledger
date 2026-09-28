"""Tests for staged Mid Cap current portfolio batch 5."""
import unittest
from unittest.mock import patch

from tracker.midcap_portfolio_batch5 import _invesco_source,_jm_source,_mahindra_positions


class MidCapPortfolioBatch5Tests(unittest.TestCase):
    def test_invesco_source_requires_exact_midcap_scheme(self):
        import json
        rows=[
            {"Name":"Invesco India Large & Mid Cap Fund","AugUrl":"https://www.invescomutualfund.com/a.xlsx","AugName":"08/26"},
            {"Name":"Invesco India Mid Cap Fund","AugUrl":"https://www.invescomutualfund.com/mid.xlsx","AugName":"08/26"},
        ]
        def fetch(url,**kwargs):return json.dumps(rows).encode(),None,"application/json"
        with patch("tracker.midcap_portfolio_batch5.disclosures.official_publication_url",return_value=True):
            source,title=_invesco_source(fetch,"2026-08-31")
        self.assertEqual(source,"https://www.invescomutualfund.com/mid.xlsx")
        self.assertIn("08/26",title)

    def test_jm_source_ignores_smallcap_and_large_midcap(self):
        listing=[
            {"CategoryID":2,"SubCategoryID":9,"SubCategoryName":"Monthly Portfolio of Schemes",
             "Title":"Monthly Portfolio - JM Small Cap Fund - August 31, 2026",
             "FileName":"/small.xlsx","FileEXT":".xlsx"},
            {"CategoryID":2,"SubCategoryID":9,"SubCategoryName":"Monthly Portfolio of Schemes",
             "Title":"Monthly Portfolio - JM Mid Cap Fund - August 31, 2026",
             "FileName":"/mid.xlsx","FileEXT":".xlsx"},
        ]
        with patch("tracker.midcap_portfolio_batch5.jm_portfolios._monthly_subcategory",return_value=9), \
             patch("tracker.midcap_portfolio_batch5.jm_portfolios._decrypt",side_effect=[listing]), \
             patch("tracker.midcap_portfolio_batch5.disclosures.official_publication_url",return_value=True):
            def fetch(url,**kwargs):
                if url.endswith("GetDownloadDrop"):return b"drop",None,"application/json"
                return b"listing",None,"application/json"
            source,title=_jm_source(fetch,"2026-08-31")
        self.assertTrue(source.endswith("/mid.xlsx"))
        self.assertIn("JM Mid Cap Fund",title)

    def test_mahindra_parser_excludes_sector_totals(self):
        from bs4 import BeautifulSoup
        # Use the publisher's actual sector/holding distinction and a coherent
        # synthetic subtotal; an unbalanced fragment must no longer pass.
        html="""<table><tr><th>Company / Issuer</th><th>% of Net Assets</th></tr>
        <tr style="font-weight:bold"><td>Financial Services</td><td>12.73%</td></tr>
        <tr style="f ont-weight:bold"><td>IndusInd Bank Limited</td><td>3.37%</td></tr>
        <tr><td>L&amp;T Finance Limited</td><td>2.79%</td></tr>
        <tr><td>PB Fintech Limited</td><td>2.52%</td></tr>
        <tr><td>Max Financial Services Limited</td><td>2.05%</td></tr>
        <tr><td>Bank of Maharashtra</td><td>2.00%</td></tr>
        <tr><td>Equity and Equity Related Total</td><td>12.73%</td></tr></table>"""
        rows=_mahindra_positions(BeautifulSoup(html,"html.parser"))
        self.assertEqual(len(rows),5)
        self.assertNotIn("Financial Services",{x["name"] for x in rows})


if __name__=="__main__":
    unittest.main()
