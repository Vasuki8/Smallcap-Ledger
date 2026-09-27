"""Tests for Mid Cap TER first-party batch 2."""
import unittest
from tracker.midcap_ter_first_party_batch2 import _same_family,_validate

class MidCapTerBatch2Tests(unittest.TestCase):
    def test_exact_family_isolation(self):
        self.assertTrue(_same_family("Kotak Midcap Fund","Kotak Mid Cap Fund"))
        self.assertTrue(_same_family("THE WEALTH COMPANY MID CAP FUND","The Wealth Company Mid Cap Fund"))
        self.assertFalse(_same_family("Kotak Small Cap Fund","Kotak Mid Cap Fund"))
    def test_component_reconciliation(self):
        p={"Regular":{"base_expense_ratio":1.2,"brokerage":.1,"transaction_cost":0,"statutory_levies":.2,"ter":1.5},
           "Direct":{"base_expense_ratio":.4,"brokerage":.1,"transaction_cost":0,"statutory_levies":.1,"ter":.6}}
        self.assertIs(_validate(p,"x"),p)
        p["Direct"]["ter"]=.5
        with self.assertRaisesRegex(ValueError,"reconcile"):_validate(p,"x")
if __name__=="__main__":unittest.main()
