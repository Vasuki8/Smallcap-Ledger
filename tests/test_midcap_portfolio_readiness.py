"""Tests for combined staged Mid Cap portfolio readiness."""
import unittest
from datetime import datetime, timezone
from tracker.midcap_portfolio_readiness import reconcile

class MidCapPortfolioReadinessTests(unittest.TestCase):
    def test_merges_unique_and_prefers_stronger_overlap(self):
        staged={"A":"AMC A","B":"AMC B","C":"AMC C"}
        def row(family,count,complete,source):
            return dict(family=family,amc=staged[family],status="recovered",as_of="2026-08-31",
                        positions_observed=count,scope="partial" if not complete else "complete",
                        complete=complete,source=source,source_sha256="a"*64,
                        observed_at="2026-09-27T00:00:00Z")
        def batch(*rows):
            return {"results":list(rows),"errors":[],"staged_category":"mid-cap","built_at":"2026-09-27T00:00:00Z"}
        b1=batch(row("A",5,False,"https://example.com/a1"),row("B",20,False,"https://example.com/b1"))
        b2=batch(row("B",18,True,"https://example.com/b2"))
        result=reconcile(staged,b1,b2,now=datetime(2026,9,28,tzinfo=timezone.utc))
        by={x["family"]:x for x in result["families_detail"]}
        self.assertEqual(by["A"]["source"],"https://example.com/a1")
        self.assertEqual(by["B"]["source"],"https://example.com/b2")
        self.assertTrue(by["B"]["complete"])
        self.assertEqual(result["current_portfolio_evidence"],2)
        self.assertEqual(result["current_complete_portfolios"],1)
        self.assertEqual(result["remaining"],1)
        self.assertEqual(result["production_writes"],0)
        self.assertFalse(result["public_export_enabled"])

if __name__=="__main__": unittest.main()
