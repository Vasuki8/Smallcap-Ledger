"""Machine-readable portfolio limitation regression checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tracker import db,disclosures,coverage
from tracker.app import app
from tracker.portfolio_limitations import portfolio_limitation


class PortfolioLimitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (9701,"Axis Small Cap Direct Growth","Axis Small Cap Fund","Axis Mutual Fund","Direct","Growth","test"),
                    (9702,"Union Small Cap Direct Growth","Union Small Cap Fund","Union Mutual Fund","Direct","Growth","test"),
                ],
            )
        self.axis_source=(
            "https://www.axismf.com/mutual-funds/equity-funds/"
            "axis-small-cap-fund/sc-dg/direct"
        )
        self.axis_id=disclosures.portfolio(
            "Axis Small Cap Fund","2026-09-16",
            [{"name":"Example Limited","weight":3.0,"asset_type":"Equity"}],
            False,self.axis_source,"axis-partial",
        )
        self.client=TestClient(app)

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_verified_partial_family_classifications_are_stable(self):
        cases={
            "Axis Small Cap Fund":(
                "https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct",
                "undisclosed_constituents","source_aggregate"),
            "Bajaj Finserv Small Cap Fund":(
                "https://media.bajajamc.com/wp-content/uploads/2026/02/Bajaj-Finserv-Small-Cap-Fund_August-2026.pdf",
                "named_subset_only","source_subset"),
            "Bandhan Small Cap Fund":(
                "https://storage.googleapis.com/example/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx",
                "non_numeric_source_weight","source_precision"),
            "Edelweiss Small Cap Fund":(
                "https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf",
                "named_subset_only","source_subset"),
            "ICICI Prudential Small Cap Fund":(
                "https://www.icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf",
                "undisclosed_constituents","source_aggregate"),
            "Sundaram Small Cap Fund":(
                "https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx",
                "non_numeric_source_weight","source_precision"),
            "UTI Small Cap Fund":(
                "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip",
                "non_numeric_source_weight","source_precision"),
        }
        for family,(source,code,kind) in cases.items():
            with self.subTest(family=family):
                limitation=portfolio_limitation(
                    family,{"complete":0,"source":source}
                )
                self.assertEqual(limitation["code"],code)
                self.assertEqual(limitation["kind"],kind)
                self.assertEqual(limitation["scope"],"partial_portfolio")
                self.assertTrue(limitation["basis"])
                self.assertTrue(limitation["detail"])

    def test_complete_snapshot_has_no_limitation_and_changed_source_is_not_guessed(self):
        self.assertIsNone(portfolio_limitation(
            "Axis Small Cap Fund",{"complete":1,"source":self.axis_source}
        ))
        changed=portfolio_limitation(
            "Axis Small Cap Fund",
            {"complete":0,"source":"https://www.axismf.com/new-structured-workbook.xlsx"},
        )
        self.assertEqual(changed["code"],"partial_reason_unclassified")
        self.assertEqual(changed["kind"],"unclassified")

    def test_missing_union_is_classified_as_upstream_transport(self):
        limitation=portfolio_limitation(
            "Union Small Cap Fund",None,{"reason":"no_official_document"}
        )
        self.assertEqual(limitation["code"],"upstream_source_unavailable")
        self.assertEqual(limitation["kind"],"upstream_transport")
        self.assertEqual(limitation["scope"],"missing_portfolio")

    def test_coverage_exposes_partial_and_missing_limitations_without_changing_counts(self):
        payload=coverage.report()
        axis=next(x for x in payload["funds"] if x["family"]=="Axis Small Cap Fund")
        union=next(x for x in payload["funds"] if x["family"]=="Union Small Cap Fund")
        self.assertEqual(axis["portfolio_limitation"]["code"],"undisclosed_constituents")
        self.assertEqual(axis["portfolio"]["limitation"]["code"],"undisclosed_constituents")
        self.assertEqual(union["portfolio_limitation"]["code"],"upstream_source_unavailable")
        self.assertIsNotNone(union["portfolio_gap"])
        self.assertEqual(payload["counts"]["portfolio"],1)
        self.assertEqual(payload["counts"]["portfolio_partial"],1)
        self.assertEqual(payload["counts"]["portfolio_complete"],0)
        self.assertEqual(payload["portfolio_limitation_reasons"]["undisclosed_constituents"],1)
        self.assertEqual(payload["portfolio_limitation_reasons"]["upstream_source_unavailable"],1)

    def test_api_exposes_limitation_on_fund_and_snapshot(self):
        fund=self.client.get("/api/funds/9701")
        self.assertEqual(fund.status_code,200)
        body=fund.json()
        self.assertEqual(body["portfolio_limitation"]["code"],"undisclosed_constituents")
        self.assertEqual(body["portfolios"][0]["limitation"]["code"],"undisclosed_constituents")

        snapshot=self.client.get(f"/api/portfolios/{self.axis_id}")
        self.assertEqual(snapshot.status_code,200)
        self.assertEqual(snapshot.json()["limitation"]["code"],"undisclosed_constituents")

        missing=self.client.get("/api/funds/9702")
        self.assertEqual(missing.status_code,200)
        self.assertEqual(missing.json()["portfolio_limitation"]["code"],"upstream_source_unavailable")


if __name__=="__main__":
    unittest.main()
