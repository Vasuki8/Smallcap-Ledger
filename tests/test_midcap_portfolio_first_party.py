"""Tests for staged Mid Cap current portfolio evidence audit."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db
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
