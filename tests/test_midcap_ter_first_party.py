"""Tests for read-only first-party Mid Cap TER recovery."""
import unittest
from datetime import date
from unittest.mock import patch

from tracker import amc_expenses
from tracker.midcap_ter_first_party import _same_family,_reconcile,_icici,_icici_fallback_sources


class MidCapFirstPartyTerTests(unittest.TestCase):
    def test_family_matching_is_normalized_but_exact_in_name_content(self):
        self.assertTrue(_same_family("ICICI Prudential Mid Cap Fund","ICICI Prudential Mid Cap Fund"))
        self.assertTrue(_same_family("HSBC Midcap Fund","HSBC Midcap Fund"))
        self.assertFalse(_same_family("ICICI Prudential Small Cap Fund","ICICI Prudential Mid Cap Fund"))
        self.assertFalse(_same_family("Mirae Asset Small Cap Fund","Mirae Asset Midcap Fund"))

    def test_icici_reviewed_monthly_fallback_urls_are_current_then_previous(self):
        urls=list(_icici_fallback_sources(date(2026,9,29)))
        self.assertEqual(urls,[
            "https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx",
            "https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioAug2026.xlsx",
        ])
        rollover=list(_icici_fallback_sources(date(2027,4,2)))
        self.assertIn("/2027-2028/TotalExpenseRatioApr2027.xlsx",rollover[0])
        self.assertIn("/2026-2027/TotalExpenseRatioMar2027.xlsx",rollover[1])

    def test_icici_api_failure_recovers_from_exact_official_workbook(self):
        header=dict(amc_expenses._ICICI_HEADER)
        rows=[
            {"A":"Total Expense Ratio (TER) for Mutual Fund Schemes"},
            {"C":"Regular Plan","H":"Direct Plan"},
            header,
            {
                "A":"ICICI Prudential Mid Cap Fund",
                "B":"27/09/2026",
                "C":"1.52","D":"0.01","E":"0.00","F":"0.30","G":"1.83",
                "H":"0.88","I":"0.01","J":"0.00","K":"0.20","L":"1.09",
            },
        ]
        calls=[]
        def fetch(url,**kwargs):
            calls.append((url,kwargs))
            if url.endswith("TotalExpenseRatioSep2026.xlsx"):
                return b"PKfixture",None,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            raise RuntimeError("not found")
        with patch.object(amc_expenses,"_icici_api",side_effect=ValueError("API unavailable")), \
             patch("tracker.midcap_ter_first_party.providers.fetch",side_effect=fetch), \
             patch.object(amc_expenses,"_icici_inline_strings",return_value=rows):
            result=_icici("ICICI Prudential Mid Cap Fund",date(2026,9,29))
        self.assertEqual(result["as_of"],"2026-09-27")
        self.assertEqual(result["plans"]["Direct"]["ter"],1.09)
        self.assertEqual(result["plans"]["Regular"]["ter"],1.83)
        self.assertEqual(result["identity"]["scheme_name"],"ICICI Prudential Mid Cap Fund")
        self.assertEqual(result["discovery_channel"],"reviewed_monthly_workbook_fallback")
        self.assertIn("API unavailable",result["discovery_api_error"])
        self.assertTrue(result["source"].endswith("TotalExpenseRatioSep2026.xlsx"))
        self.assertFalse(calls[0][1]["archive"])

    def test_icici_fallback_still_requires_exact_midcap_row(self):
        rows=[
            {},
            {},
            dict(amc_expenses._ICICI_HEADER),
            {
                "A":"ICICI Prudential Small Cap Fund",
                "B":"27/09/2026",
                "C":"1.0","D":"0","E":"0","F":"0","G":"1.0",
                "H":"0.5","I":"0","J":"0","K":"0","L":"0.5",
            },
        ]
        with patch.object(amc_expenses,"_icici_api",side_effect=ValueError("API unavailable")), \
             patch("tracker.midcap_ter_first_party.providers.fetch",return_value=(b"PKfixture",None,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")), \
             patch.object(amc_expenses,"_icici_inline_strings",return_value=rows):
            with self.assertRaisesRegex(ValueError,"scheme name is not unique|no exact Mid Cap rows"):
                _icici("ICICI Prudential Mid Cap Fund",date(2026,9,29))

    def test_reconcile_requires_both_plans_and_component_totals(self):
        plans={
            "Regular":{"base_expense_ratio":1.0,"brokerage":0.1,"transaction_cost":0.1,"statutory_levies":0.05,"ter":1.25},
            "Direct":{"base_expense_ratio":0.5,"brokerage":0.1,"transaction_cost":0.1,"statutory_levies":0.05,"ter":0.75},
        }
        self.assertIs(_reconcile(plans,"fixture"),plans)
        broken={"Direct":plans["Direct"]}
        with self.assertRaisesRegex(ValueError,"both Regular and Direct"):
            _reconcile(broken,"fixture")
        broken={k:dict(v) for k,v in plans.items()}
        broken["Direct"]["ter"]=0.70
        with self.assertRaisesRegex(ValueError,"do not reconcile"):
            _reconcile(broken,"fixture")


if __name__=="__main__":
    unittest.main()
