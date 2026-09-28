"""Tests for combined staged Mid Cap portfolio readiness."""
import unittest

from tracker.midcap_portfolio_readiness import reconcile


class MidCapPortfolioReadinessTests(unittest.TestCase):
    def test_merges_unique_and_prefers_stronger_overlap(self):
        staged={"A":"AMC A","B":"AMC B","C":"AMC C"}
        b1={"results":[
            {"family":"A","as_of":"2026-08-31","positions_observed":5,"scope":"top_5","complete":False,"source":"a1"},
            {"family":"B","as_of":"2026-08-31","positions_observed":20,"scope":"partial","complete":False,"source":"b1"},
        ],"errors":[]}
        b2={"results":[
            {"family":"B","as_of":"2026-08-31","positions_observed":18,"scope":"complete","complete":True,"source":"b2"},
        ],"errors":[]}
        r=reconcile(staged,b1,b2)
        by={x["family"]:x for x in r["families_detail"]}
        self.assertEqual(by["A"]["source"],"a1")
        self.assertEqual(by["B"]["source"],"b2")
        self.assertTrue(by["B"]["complete"])
        self.assertEqual(r["current_portfolio_evidence"],2)
        self.assertEqual(r["current_complete_portfolios"],1)
        self.assertEqual(r["remaining"],1)
        self.assertEqual(r["production_writes"],0)
        self.assertFalse(r["public_export_enabled"])


if __name__=="__main__":unittest.main()
