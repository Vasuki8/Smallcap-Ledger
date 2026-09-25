"""Axis Small Cap explicit BER/TER recovery regression checks."""
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import openpyxl

from tracker import amc_expenses, db


class AxisExpenseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9902,"Axis Small Cap Direct Growth",amc_expenses.AXIS_FAMILY,
                 "Axis Mutual Fund","Direct","Growth","test"),
            )

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def api_rows(self, day="24-09-2026"):
        return [
            {
                "schemeName":amc_expenses.AXIS_FAMILY,
                "planOption":"Regular","date":day,
                "baseTer":"1.34","addExpenses2":"0.03","addExpenses3":"0.00",
                "gst":"0.31","totalTer":"1.68",
                "nsdlSchemeCode":amc_expenses.AXIS_NSDL_CODE,
            },
            {
                "schemeName":amc_expenses.AXIS_FAMILY,
                "planOption":"Direct","date":day,
                "baseTer":"0.52","addExpenses2":"0.03","addExpenses3":"0.00",
                "gst":"0.16","totalTer":"0.71",
                "nsdlSchemeCode":amc_expenses.AXIS_NSDL_CODE,
            },
        ]

    def workbook(self, rows=None, header3=None, footnote=True):
        rows=rows or [[
            amc_expenses.AXIS_NSDL_CODE,amc_expenses.AXIS_FAMILY,"24-09-2026",
            "1.34","0.03","0.00","0.31","1.68",
            "0.52","0.03","0.00","0.16","0.71","","","","","",
        ]]
        book=openpyxl.Workbook()
        sheet=book.active;sheet.title="TotalExpenseRatio"
        sheet.append(list(amc_expenses._AXIS_HEADER_1))
        sheet.append([""]*18)
        sheet.append(list(header3 or amc_expenses._AXIS_HEADER_3))
        for row in rows:sheet.append(row)
        sheet.append([""]*18)
        if footnote:
            sheet.append([
                "1. Base Expense Ratio (BER) as per Regulation 66(7) of SEBI "
                "(Mutual Funds) Regulations, 2026."
            ]+[""]*17)
        for i in range(5):
            sheet.append([f"{i+2}. Other validated disclosure note"]+[""]*17)
        out=io.BytesIO();book.save(out);book.close()
        return out.getvalue()

    def response(self, rows=None, source=None):
        source=source or (
            "https://www.axismf.com/1/5/2125/"
            "Total_Expense_Ratio_2026-09-25_05_59_10.xlsx"
        )
        return {
            "status":"success","statusCode":0,
            "data":{
                "title":"All Equity Schemes - Total Expense Ratio",
                "totalExpenseRatioData":rows or self.api_rows(),
                "s3CsvResponse":{"location":source},
            },
        }

    def test_axis_api_rows_select_latest_exact_plan_pair(self):
        rows=self.api_rows("23-09-2026")+self.api_rows("24-09-2026")
        day,plans=amc_expenses.parse_axis_records(rows,date(2026,9,25))
        self.assertEqual(day,"2026-09-24")
        self.assertEqual(plans["Regular"]["base_expense_ratio"],1.34)
        self.assertEqual(plans["Regular"]["ter"],1.68)
        self.assertEqual(plans["Direct"]["base_expense_ratio"],.52)
        self.assertEqual(plans["Direct"]["ter"],.71)

    def test_axis_api_rows_reject_wrong_identity_duplicate_and_future_only(self):
        wrong=self.api_rows()
        wrong[0]=dict(wrong[0],nsdlSchemeCode="AXIS/O/E/OTHER")
        wrong[1]=dict(wrong[1],schemeName="Axis Midcap Fund")
        with self.assertRaisesRegex(ValueError,"no dated Small Cap"):
            amc_expenses.parse_axis_records(wrong,date(2026,9,25))

        duplicate=self.api_rows()+[dict(self.api_rows()[0])]
        with self.assertRaisesRegex(ValueError,"one exact plan pair"):
            amc_expenses.parse_axis_records(duplicate,date(2026,9,25))

        with self.assertRaisesRegex(ValueError,"no dated Small Cap"):
            amc_expenses.parse_axis_records(
                self.api_rows("26-09-2026"),date(2026,9,25))

    def test_axis_workbook_retains_explicit_ber_ter_and_components(self):
        day,plans=amc_expenses.parse_axis_workbook(
            self.workbook(),date(2026,9,25))
        self.assertEqual(day,"2026-09-24")
        self.assertEqual(plans["Regular"],{
            "base_expense_ratio":1.34,"brokerage":.03,
            "transaction_cost":0.0,"statutory_levies":.31,"ter":1.68,
        })
        self.assertEqual(plans["Direct"],{
            "base_expense_ratio":.52,"brokerage":.03,
            "transaction_cost":0.0,"statutory_levies":.16,"ter":.71,
        })

    def test_axis_workbook_rejects_header_footnote_and_component_drift(self):
        changed=list(amc_expenses._AXIS_HEADER_3)
        changed[3]="Expense Ratio (%)"
        with self.assertRaisesRegex(ValueError,"metric columns changed"):
            amc_expenses.parse_axis_workbook(
                self.workbook(header3=changed),date(2026,9,25))
        with self.assertRaisesRegex(ValueError,"footnote changed"):
            amc_expenses.parse_axis_workbook(
                self.workbook(footnote=False),date(2026,9,25))
        broken=[[
            amc_expenses.AXIS_NSDL_CODE,amc_expenses.AXIS_FAMILY,"24-09-2026",
            "1.34","0.03","0.00","0.31","1.80",
            "0.52","0.03","0.00","0.16","0.71","","","","","",
        ]]
        with self.assertRaisesRegex(ValueError,"components do not reconcile"):
            amc_expenses.parse_axis_workbook(
                self.workbook(rows=broken),date(2026,9,25))

    def test_axis_api_selects_only_first_party_generated_workbook(self):
        source,day,plans=amc_expenses._axis_select_workbook(
            self.response(),date(2026,9,25))
        self.assertTrue(source.startswith(
            "https://www.axismf.com/1/5/2125/Total_Expense_Ratio_"))
        self.assertEqual(day,"2026-09-24")
        self.assertEqual(plans["Direct"]["ter"],.71)
        bad=self.response(source="https://example.com/Total_Expense_Ratio_2026-09-25_05_59_10.xlsx")
        with self.assertRaisesRegex(ValueError,"unexpected workbook URL"):
            amc_expenses._axis_select_workbook(bad,date(2026,9,25))

    @patch("tracker.amc_expenses.axis_portfolios.cms_token")
    @patch("tracker.amc_expenses.fetch")
    def test_axis_public_token_adapter_accepts_non_archiving_read_contract(
        self,mock_fetch,mock_cms_token
    ):
        mock_fetch.return_value=(b'{"token":"transport"}',"ignored","application/json")
        def exercise(read_fn):
            read_fn("https://www.axismf.com/cms/token",body={},archive=False)
            return "public-token"
        mock_cms_token.side_effect=exercise
        self.assertEqual(amc_expenses._axis_cms_token(),"public-token")
        self.assertFalse(mock_fetch.call_args.kwargs["archive"])

    @patch("tracker.amc_expenses.fetch")
    @patch("tracker.amc_expenses._axis_cms_token",return_value="public-token")
    def test_axis_disclosure_uses_current_accepted_schema_and_cross_checks_workbook(
        self,_token,mock_fetch
    ):
        source=(
            "https://www.axismf.com/1/5/2125/"
            "Total_Expense_Ratio_2026-09-25_05_59_10.xlsx"
        )
        api=json.dumps(self.response(source=source),separators=(",",":")).encode()
        workbook=self.workbook()
        mock_fetch.side_effect=[
            (api,"api-hash","application/json"),
            (workbook,"workbook-hash",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ]
        got_source,day,plans,h=amc_expenses._axis_disclosure(date(2026,9,25))
        self.assertEqual((got_source,day,h),(source,"2026-09-24","workbook-hash"))
        self.assertEqual(plans["Direct"]["ter"],.71)
        first=mock_fetch.call_args_list[0]
        body=first.kwargs["body"]
        self.assertEqual(body["fundType"],"Equity")
        self.assertEqual(body["schemeCode"],"SC")
        self.assertEqual(body["type"],"Total Expense Ratio")
        self.assertNotIn("planCode",body)
        self.assertEqual(first.kwargs["headers"]["Authorization"],"public-token")
        self.assertFalse(first.kwargs["archive"])

    @patch("tracker.amc_expenses.db.metric")
    @patch("tracker.amc_expenses._axis_disclosure")
    def test_axis_collector_stores_explicit_components_with_workbook_evidence(
        self,mock_disclosure,mock_metric
    ):
        _,plans=amc_expenses.parse_axis_workbook(
            self.workbook(),date(2026,9,25))
        source=(
            "https://www.axismf.com/1/5/2125/"
            "Total_Expense_Ratio_2026-09-25_05_59_10.xlsx"
        )
        mock_disclosure.return_value=(source,"2026-09-24",plans,"axis-ter-hash")
        result=amc_expenses.axis(today=date(2026,9,25))
        self.assertIn("2026-09-24",result)
        self.assertEqual(mock_metric.call_count,10)
        calls={(x.args[1],x.args[2]):x.args for x in mock_metric.call_args_list}
        self.assertEqual(calls[("Direct","base_expense_ratio")][4],.52)
        self.assertEqual(calls[("Direct","ter")][4],.71)
        self.assertTrue(all(x.args[6]==source for x in mock_metric.call_args_list))
        self.assertTrue(all(x.args[7]=="axis-ter-hash" for x in mock_metric.call_args_list))
        self.assertTrue(all(x.args[3]=="2026-09-24" for x in mock_metric.call_args_list))


if __name__=="__main__":
    unittest.main()
