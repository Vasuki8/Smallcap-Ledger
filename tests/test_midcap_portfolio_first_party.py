"""Tests for staged Mid Cap current portfolio evidence audit."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db
from bs4 import BeautifulSoup

from tracker.midcap_factsheet_equities import validate_factsheet_context
from tracker.midcap_portfolio_first_party import inspect_family


class MidCapPortfolioFirstPartyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def test_canara_requires_exact_family_date_and_named_holdings(self):
        html="""<html><body>
        <h1>Canara Robeco Mid Cap Fund</h1><p>(as on August 31, 2026)</p>
        <h2>PORTFOLIO</h2><table>
        <tr><th>Name of the Instruments/Issuer</th><th>Market Cap</th><th>% to NAV</th></tr>
        <tr><td>A Ltd</td><td>M</td><td>2.5%</td></tr>
        <tr><td>B Bank Ltd</td><td>M</td><td>2.0%</td></tr>
        <tr><td>C Industries Ltd</td><td>L</td><td>1.8%</td></tr>
        <tr><td>D Finance Ltd</td><td>M</td><td>1.5%</td></tr>
        <tr><td>E Technologies Ltd</td><td>S</td><td>1.2%</td></tr>
        <tr><td>Banks</td><td></td><td>12.0%</td></tr>
        </table></body></html>"""
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        row=inspect_family("Canara Robeco Mid Cap Fund",{
            "url":"https://digitalassets.canararobeco.com/test.html",
            "parser":"canara","scope":"full_page_portfolio",
        },fetch_fn=fetch,today=date(2026,9,27))
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertEqual(row["positions_observed"],5)
        self.assertFalse(row["complete"])

    def test_stale_date_is_rejected(self):
        html="<html><body>Canara Robeco Mid Cap Fund as on July 31, 2026<table><tr><td>A Ltd</td><td>M</td><td>2%</td></tr></table></body></html>"
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        with self.assertRaisesRegex(ValueError,"current portfolio date"):
            inspect_family("Canara Robeco Mid Cap Fund",{
                "url":"https://digitalassets.canararobeco.com/test.html",
                "parser":"canara","scope":"full_page_portfolio",
            },fetch_fn=fetch,today=date(2026,9,27))

    def test_fewer_than_five_named_positions_is_not_coverage(self):
        html="""<html><body>Canara Robeco Mid Cap Fund as on August 31, 2026
        <table><tr><td>A Ltd</td><td>M</td><td>2%</td></tr>
        <tr><td>B Ltd</td><td>M</td><td>1%</td></tr></table></body></html>"""
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        with self.assertRaisesRegex(ValueError,"at least 5"):
            inspect_family("Canara Robeco Mid Cap Fund",{
                "url":"https://digitalassets.canararobeco.com/test.html",
                "parser":"canara","scope":"full_page_portfolio",
            },fetch_fn=fetch,today=date(2026,9,27))

    def test_reviewed_heading_alias_is_opt_in_and_exact(self):
        html=(
            "<html><body><h1>KOTAK MID CAP FUND "
            "(ERSTWHILE KNOWN AS KOTAK MIDCAP FUND)</h1>"
            "<p>Data as on 31st August, 2026</p></body></html>"
        )
        soup=BeautifulSoup(html,"html.parser")
        with self.assertRaisesRegex(ValueError,"exact staged scheme"):
            validate_factsheet_context(soup,"Kotak Mid Cap Fund","2026-08-31")
        validate_factsheet_context(
            soup,"Kotak Mid Cap Fund","2026-08-31",
            reviewed_heading_aliases=(
                "KOTAK MID CAP FUND (ERSTWHILE KNOWN AS KOTAK MIDCAP FUND)",
            ),
        )
        with self.assertRaisesRegex(ValueError,"exact staged scheme"):
            validate_factsheet_context(
                soup,"Kotak Mid Cap Fund","2026-08-31",
                reviewed_heading_aliases=("KOTAK MID CAP FUND",),
            )


    def test_iti_digital_factsheet_recovers_named_current_holdings(self):
        html="""<html><body>
        <h1>ITI Mid Cap Fund</h1>
        <p>Data is as of August 31, 2026 unless otherwise specified.</p>
        <table>
        <tr><th></th><th>Name of the Instrument</th><th>% to NAV</th><th>% to NAV Derivatives</th></tr>
        <tr><td></td><td>Equity &amp; Equity Related Total</td><td>97.39</td><td>0.63</td></tr>
        <tr><td></td><td><strong>Capital Goods</strong></td><td>14.81</td><td></td></tr>
        <tr><td></td><td><strong>Healthcare</strong></td><td>12.87</td><td></td></tr>
        <tr><td>•</td><td>Bharat Heavy Electricals Limited</td><td>1.53</td><td></td></tr>
        <tr><td></td><td>Cummins India Limited</td><td>1.45</td><td></td></tr>
        <tr><td></td><td>Apar Industries Limited</td><td>1.38</td><td></td></tr>
        <tr><td></td><td>Indian Bank</td><td>1.26</td><td></td></tr>
        <tr><td></td><td>Godfrey Phillips India Limited</td><td></td><td>0.63</td></tr>
        <tr><td></td><td>Short Term Debt &amp; Net Current Assets</td><td>1.63</td><td></td></tr>
        </table></body></html>"""
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        row=inspect_family("ITI Mid Cap Fund",{
            "url":"https://www.itiamc.com/digitalfactsheet/August2026/innerpages/Mid-Cap.html",
            "parser":"iti","scope":"digital_factsheet_named_holdings",
        },fetch_fn=fetch,today=date(2026,9,30))
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertEqual(row["positions_observed"],5)
        self.assertFalse(row["complete"])
        self.assertEqual(
            {x["name"] for x in row["positions"]},
            {
                "Bharat Heavy Electricals Limited",
                "Cummins India Limited",
                "Apar Industries Limited",
                "Indian Bank",
                "Godfrey Phillips India Limited",
            },
        )


    def test_bank_of_india_top_10_current_holdings(self):
        html="""<html><body>
        <h1>Bank of India Mid Cap Fund</h1>
        <p>The above Riskometer is based on the portfolio as on 31st August 2026.</p>
        <h3>Top 10 Portfolio Holdings</h3>
        <table>
        <tr><th>Portfolio Details</th><th>% to Net Assets</th></tr>
        <tr><td>Aurobindo Pharma Limited</td><td>5.6%</td></tr>
        <tr><td>Multi Commodity Exchange of India Limited</td><td>4.9%</td></tr>
        <tr><td>Abbott India Limited</td><td>4.4%</td></tr>
        <tr><td>Bharti Hexacom Limited</td><td>4.0%</td></tr>
        <tr><td>One 97 Communications Limited</td><td>3.4%</td></tr>
        <tr><td>Quality Power Electrical Eqp Ltd</td><td>3.1%</td></tr>
        <tr><td>UNO Minda Limited</td><td>2.9%</td></tr>
        <tr><td>Nippon Life India Asset Management Limited</td><td>2.9%</td></tr>
        <tr><td>Bank of Maharashtra</td><td>2.7%</td></tr>
        <tr><td>Mankind Pharma Limited</td><td>2.7%</td></tr>
        </table></body></html>"""
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        row=inspect_family("BANK OF INDIA MID CAP FUND",{
            "url":"https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund",
            "parser":"boi","scope":"top_10",
        },fetch_fn=fetch,today=date(2026,9,30))
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertEqual(row["positions_observed"],10)
        self.assertFalse(row["complete"])
        self.assertEqual(row["scope"],"top_10")

    def test_wrong_family_is_rejected(self):
        html="<html><body>Canara Robeco Small Cap Fund as on August 31, 2026</body></html>"
        def fetch(url,**kwargs):return html.encode(),None,"text/html"
        with self.assertRaisesRegex(ValueError,"exact staged"):
            inspect_family("Canara Robeco Mid Cap Fund",{
                "url":"https://digitalassets.canararobeco.com/test.html",
                "parser":"canara","scope":"full_page_portfolio",
            },fetch_fn=fetch,today=date(2026,9,27))


if __name__=="__main__":
    unittest.main()
