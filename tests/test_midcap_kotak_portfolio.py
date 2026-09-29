"""Focused tests for the reviewed Kotak Mid Cap factsheet alias."""
import unittest

from tracker.midcap_portfolio_batch5 import _kotak_result


class KotakMidCapPortfolioTests(unittest.TestCase):
    def test_reviewed_renamed_heading_recovers_current_equity_evidence(self):
        html="""<html><body>
        <h1>KOTAK MID CAP FUND (ERSTWHILE KNOWN AS KOTAK MIDCAP FUND)</h1>
        <div>Data as on 31st August, 2026</div>
        <table>
          <tr><th>Issuer/Instrument</th><th>% to Net Assets</th></tr>
          <tr style="font-weight:bold"><td>Financial Services</td><td>10.00</td></tr>
          <tr><td>Alpha Bank Limited</td><td>6.00</td></tr>
          <tr><td>Beta Finance Limited</td><td>4.00</td></tr>
          <tr style="font-weight:bold"><td>Information Technology</td><td>15.00</td></tr>
          <tr><td>Gamma Technologies Limited</td><td>5.00</td></tr>
          <tr><td>Delta Systems Limited</td><td>5.00</td></tr>
          <tr><td>Epsilon Services Limited</td><td>5.00</td></tr>
          <tr><td>Equity and Equity Related Total</td><td>25.00</td></tr>
        </table></body></html>"""
        row=_kotak_result(
            lambda *a,**k:(html.encode(),None,"text/html; charset=utf-8"),
            "2026-08-31",
        )
        self.assertEqual(row["family"],"Kotak Mid Cap Fund")
        self.assertEqual(row["positions_observed"],5)
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertFalse(row["complete"])
        self.assertEqual(row["scope"],"factsheet_equity_only")

    def test_unreviewed_heading_stays_rejected(self):
        html="""<html><body>
        <h1>KOTAK EMERGING EQUITY FUND</h1>
        <div>Data as on 31st August, 2026</div>
        </body></html>"""
        with self.assertRaisesRegex(ValueError,"reviewed alias"):
            _kotak_result(
                lambda *a,**k:(html.encode(),None,"text/html"),
                "2026-08-31",
            )


if __name__=="__main__":
    unittest.main()
