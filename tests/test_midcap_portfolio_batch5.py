"""Tests for staged Mid Cap current portfolio batch 5."""
import unittest
from unittest.mock import patch

from tracker.midcap_portfolio_batch5 import _invesco_source,_jm_source,_mahindra_positions,_samco_result


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

    def test_samco_current_all_holdings_are_partial_evidence(self):
        html="""<html><body>
        <h1>Samco Mid Cap Fund</h1>
        <h2>All Holdings (as on 2026-08-31)</h2>
        <table>
          <tr><th>Issuers</th><th>Industry</th><th>% Of Net Assets</th></tr>
          <tr><td>Indian Equity and Equity Related Total</td><td></td><td>98.54</td></tr>
          <tr><td>National Aluminium Company Ltd.</td><td>Metals</td><td>5.78</td></tr>
          <tr><td>Laurus Labs Ltd.</td><td>Pharma</td><td>5.05</td></tr>
          <tr><td>Apar Industries Ltd.</td><td>Capital Goods</td><td>4.68</td></tr>
          <tr><td>L&amp;T Finance Ltd.</td><td>Finance</td><td>4.46</td></tr>
          <tr><td>Federal Bank Ltd.</td><td>Bank</td><td>4.30</td></tr>
          <tr><td>TREPS, Cash &amp; Cash Equivalents</td><td></td><td>1.46</td></tr>
          <tr><td>Grand Total</td><td></td><td>100.00</td></tr>
        </table></body></html>"""
        def fetch(url,**kwargs):
            self.assertEqual(kwargs.get("archive"),False)
            return html.encode(),None,"text/html; charset=utf-8"
        row=_samco_result(fetch,"2026-08-31")
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertEqual(row["positions_observed"],5)
        self.assertFalse(row["complete"])
        self.assertEqual(row["scope"],"publisher_all_holdings_html")
        names={x["name"] for x in row["positions"]}
        self.assertNotIn("Indian Equity and Equity Related Total",names)
        self.assertNotIn("TREPS, Cash & Cash Equivalents",names)
        self.assertNotIn("Grand Total",names)

    def test_samco_rejects_wrong_family_or_stale_date(self):
        def run(body):
            return _samco_result(lambda *a,**k:(body.encode(),None,"text/html"),"2026-08-31")
        with self.assertRaisesRegex(ValueError,"exact staged"):
            run("<html><body>Samco Small Cap Fund All Holdings (as on 2026-08-31)</body></html>")
        with self.assertRaisesRegex(ValueError,"current all-holdings date"):
            run("<html><body>Samco Mid Cap Fund All Holdings (as on 2026-07-31)</body></html>")

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
