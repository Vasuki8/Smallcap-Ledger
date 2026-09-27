"""Tests for read-only first-party Mid Cap TER recovery."""
import unittest
from datetime import date

from tracker.midcap_ter_first_party import _same_family,_reconcile


class MidCapFirstPartyTerTests(unittest.TestCase):
    def test_family_matching_is_normalized_but_exact_in_name_content(self):
        self.assertTrue(_same_family("ICICI Prudential Mid Cap Fund","ICICI Prudential Mid Cap Fund"))
        self.assertTrue(_same_family("HSBC Midcap Fund","HSBC Midcap Fund"))
        self.assertFalse(_same_family("ICICI Prudential Small Cap Fund","ICICI Prudential Mid Cap Fund"))
        self.assertFalse(_same_family("Mirae Asset Small Cap Fund","Mirae Asset Midcap Fund"))

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
