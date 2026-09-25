"""Axis Small Cap public monthly-portfolio discovery and parser checks."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures, coverage
from tracker.axis_portfolios import (
    FAMILY, DOCUMENTS_ENDPOINT, NESTED_ENDPOINT, TOKEN_ENDPOINT,
    document_candidates, discover, validate_monthly_branch,
)
from tracker.portfolio_parser import parse_sheet


def _formats(rows):
    out=[]
    for row in rows:
        current=["General"]*len(row)
        if len(row)>6 and isinstance(row[6],(int,float)):
            current[6]="0.00%"
        out.append(current)
    return out


class AxisPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_axis_complete_rows_reconcile_without_balancing_guess(self):
        rows=[
            ["AXISSCF",FAMILY,None,None,None,None,None],
            [None,None,None,None,None,None,None],
            [None,"Monthly Portfolio Statement as on August 31, 2026",None,None,None,None,None],
            [None,"Name of the Instrument","ISIN","Industry","Quantity",
             "Market/Fair Value (Rs. in Lakhs)","% to Net Assets"],
            [None,"Equity & Equity related",None,None,None,None,None],
            ["ALPH01","Alpha Limited","INE123456789","Banks",100,9152,0.9152],
            [None,"Total",None,None,None,9152,0.9152],
            [None,"Derivatives",None,None,None,None,None],
            [None,"(a) Index / Stock Futures",None,None,None,None,None],
            ["NIFTYFSEP26","NIFTY September 2026 Future",None,None,109655,85,0.0085],
            [None,"Total",None,None,None,85,0.0085],
            [None,"Money Market Instruments",None,None,None,None,None],
            [None,"Treasury Bill",None,None,None,None,None],
            ["TBIL2587","364 Days Tbill (MD 12/11/2026)","IN002025Z336",
             "Sovereign",15000000,47,0.0047],
            [None,"Reverse Repo / TREPS",None,None,None,None,None],
            ["TRP_010926","Clearing Corporation of India Ltd",None,None,None,505,0.0505],
            ["TRP_020926_VAL","Clearing Corporation of India Ltd",None,None,None,159,0.0159],
            ["TRP_010926_VAL","Clearing Corporation of India Ltd",None,None,None,79,0.0079],
            [None,"Net Receivables / (Payables)",None,None,None,-27,-0.0027],
            [None,"GRAND TOTAL",None,None,None,10000,1.0],
        ]
        parsed=parse_sheet(rows,_formats(rows),FAMILY)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["day"],"2026-08-31")
        self.assertEqual(parsed["aum"],100)
        self.assertTrue(parsed["complete"])
        self.assertEqual(parsed["unknown_rows"],[])
        self.assertEqual(len(parsed["positions"]),7)
        self.assertAlmostEqual(sum(x["weight"] for x in parsed["positions"]),100,places=8)
        derivative=next(x for x in parsed["positions"] if x["asset_type"]=="Derivative")
        self.assertEqual(derivative["name"],"NIFTY September 2026 Future")
        self.assertEqual(derivative["quantity"],109655)
        repos=[x for x in parsed["positions"] if x["asset_type"]=="Money market"]
        self.assertEqual(len(repos),3)
        self.assertEqual(
            {x["name"] for x in repos},
            {
                "Clearing Corporation of India Ltd · TRP_010926",
                "Clearing Corporation of India Ltd · TRP_020926_VAL",
                "Clearing Corporation of India Ltd · TRP_010926_VAL",
            },
        )

    def test_axis_unknown_non_isin_row_stays_incomplete(self):
        rows=[
            ["AXISSCF",FAMILY,None,None,None,None,None],
            [None,"Monthly Portfolio Statement as on August 31, 2026",None,None,None,None,None],
            [None,"Name of the Instrument","ISIN","Industry","Quantity",
             "Market/Fair Value (Rs. in Lakhs)","% to Net Assets"],
            [None,"Money Market Instruments",None,None,None,None,None],
            [None,"Reverse Repo / TREPS",None,None,None,None,None],
            ["NOT_A_REVIEWED_CODE","Clearing Corporation of India Ltd",None,None,None,10000,1.0],
            [None,"GRAND TOTAL",None,None,None,10000,1.0],
        ]
        parsed=parse_sheet(rows,_formats(rows),FAMILY)
        self.assertIsNotNone(parsed)
        self.assertFalse(parsed["complete"])
        self.assertEqual(parsed["unknown_rows"],["Clearing Corporation of India Ltd"])

    def test_coverage_prefers_current_complete_month_end_over_later_partial(self):
        with db.connect() as connection:
            connection.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9901,"Axis Small Cap Direct Growth",FAMILY,
                 "Axis Mutual Fund","Direct","Growth","test"),
            )
        disclosures.portfolio(
            FAMILY,"2026-09-16",
            [{"name":"Top Holding Limited","weight":10}],
            False,
            "https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct",
            "axis-intraday-partial",
        )
        disclosures.portfolio(
            FAMILY,"2026-08-31",
            [{"name":"Full Monthly Holding Limited","weight":100}],
            True,
            ("https://www.axismf.com/1/5/464/560/3622/4549/"
             "Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_test.xlsx"),
            "axis-monthly-complete",
        )
        from tracker.app import fund, funds
        with patch("tracker.coverage.expected_portfolio_as_of",return_value="2026-08-31"), \
             patch("tracker.app.expected_portfolio_as_of",return_value="2026-08-31"):
            row=next(x for x in coverage.report()["funds"] if x["family"]==FAMILY)
            detail=fund(9901)
            summary=next(x for x in funds()["funds"] if x["code"]==9901)
        self.assertEqual(row["portfolio"]["as_of"],"2026-08-31")
        self.assertTrue(row["portfolio_complete"])
        self.assertTrue(row["portfolio_fresh"])
        self.assertIsNone(row["portfolio_limitation"])
        self.assertEqual(detail["portfolios"][0]["as_of"],"2026-08-31")
        self.assertEqual(detail["portfolios"][0]["complete"],1)
        self.assertIsNone(detail["portfolios"][0]["limitation"])
        self.assertEqual(summary["portfolio"]["as_of"],"2026-08-31")
        self.assertEqual(summary["portfolio"]["complete"],1)
        self.assertIsNone(summary["portfolio_limitation"])

    def test_nested_branch_requires_exact_monthly_portfolio_identity(self):
        body=json.dumps({
            "status":"success","statusCode":0,
            "data":{"sdNestedList":[
                {"sdNestedType":"yearMonthSchemeDocs","parentId":"sdPortfolios",
                 "sdNestedId":"sdMonthSchemePortfolio",
                 "sdNestedTitle":"Monthly Scheme Portfolios",
                 "isHavingRedirectionUrl":False,"redirectionUrl":None},
                {"sdNestedType":"yearMonthSchemeDocs","parentId":"sdPortfolios",
                 "sdNestedId":"sdFortnightlyPortfolio",
                 "sdNestedTitle":"Fortnightly Portfolio Disclosure for Debt Schemes",
                 "isHavingRedirectionUrl":False,"redirectionUrl":None},
            ]},
        }).encode()
        row=validate_monthly_branch(body)
        self.assertEqual(row["sdNestedId"],"sdMonthSchemePortfolio")
        changed=json.loads(body)
        changed["data"]["sdNestedList"][0]["sdNestedTitle"]="Monthly Factsheets"
        with self.assertRaisesRegex(ValueError,"no unique monthly branch"):
            validate_monthly_branch(json.dumps(changed).encode())

    def test_document_candidates_select_only_exact_small_cap_closed_months(self):
        aug=("https://www.axismf.com/1/5/464/560/3622/4549/"
             "Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_4a112f9ef0.xlsx")
        jul=("https://www.axismf.com/1/5/464/560/3622/4548/"
             "Monthly_Portfolio_Axis_Small_Cap_Fund_31_July_2026_xlsx_1234567890.xlsx")
        passive=("https://www.axismf.com/1/5/464/560/3622/4549/"
                 "Monthly_Portfolio_Axis_Nifty_Smallcap_50_Index_Fund_31_August_2026.xlsx")
        payload={
            "status":"success","statusCode":0,
            "data":{
                "schemeCategories":[
                    {"schemeName":FAMILY,"schemeCode":"SC"},
                    {"schemeName":"Axis Nifty Smallcap 50 Index Fund","schemeCode":"NS"},
                ],
                "years":["2025","2026"],
                "months":["July","August"],
                "documentList":[
                    {"docuementURL":aug,"documentName":
                     "Monthly Portfolio - Axis Small Cap Fund - 31 August 2026",
                     "documentPostedDate":"2026-08-31","redirectionUrl":None},
                    {"docuementURL":jul,"documentName":
                     "Monthly Portfolio - Axis Small Cap Fund - 31 July 2026",
                     "documentPostedDate":"2026-07-31","redirectionUrl":None},
                    {"docuementURL":passive,"documentName":
                     "Monthly Portfolio - Axis Nifty Smallcap 50 Index Fund - 31 August 2026",
                     "documentPostedDate":"2026-08-31","redirectionUrl":None},
                ],
            },
        }
        found=document_candidates(json.dumps(payload).encode(),date(2026,9,25))
        self.assertEqual([(x[0].isoformat(),x[1]) for x in found],
                         [("2026-08-31",aug),("2026-07-31",jul)])

    def test_discovery_replays_public_token_flow_without_archiving_token(self):
        token="public-cms-token"
        nested=json.dumps({
            "status":"success","statusCode":0,
            "data":{"sdNestedList":[{
                "sdNestedType":"yearMonthSchemeDocs","parentId":"sdPortfolios",
                "sdNestedId":"sdMonthSchemePortfolio",
                "sdNestedTitle":"Monthly Scheme Portfolios",
                "isHavingRedirectionUrl":False,"redirectionUrl":None,
            }]},
        }).encode()
        aug=("https://www.axismf.com/1/5/464/560/3622/4549/"
             "Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_4a112f9ef0.xlsx")
        docs=json.dumps({
            "status":"success","statusCode":0,
            "data":{
                "schemeCategories":[{"schemeName":FAMILY,"schemeCode":"SC"}],
                "years":["2026"],"months":["July","August"],
                "documentList":[{
                    "docuementURL":aug,
                    "documentName":"Monthly Portfolio - Axis Small Cap Fund - 31 August 2026",
                    "documentPostedDate":"2026-08-31","redirectionUrl":None,
                }],
            },
        }).encode()
        calls=[]
        def read(url,**kwargs):
            calls.append((url,kwargs))
            if url==TOKEN_ENDPOINT:
                return json.dumps({"status":"success","statusCode":0,
                                   "data":{"token":token}}).encode(),None,"application/json"
            if url==NESTED_ENDPOINT:return nested,"nested-hash","application/json"
            if url==DOCUMENTS_ENDPOINT:return docs,"docs-hash","application/json"
            raise AssertionError(url)

        rows=list(discover(read,today=date(2026,9,25)))
        self.assertEqual(rows,[(FAMILY,aug,
            "Monthly Portfolio - Axis Small Cap Fund - 31 August 2026")])
        self.assertEqual(calls[0][1],{"body":{},"archive":False})
        self.assertEqual(calls[1][1]["headers"],{"Authorization":token})
        self.assertEqual(calls[2][1]["headers"],{"Authorization":token})
        self.assertEqual(calls[1][1]["body"],{"sdParentID":"sdPortfolios"})
        self.assertEqual(calls[2][1]["body"],
                         {"sdType":"yearMonthSchemeDocs","sdID":"sdMonthSchemePortfolio"})


if __name__=="__main__":
    unittest.main()
