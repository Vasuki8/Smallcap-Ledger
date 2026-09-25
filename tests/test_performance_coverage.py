"""Read-only historical performance/benchmark coverage audit checks."""
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.performance_coverage import (
    BSE_SERIES, benchmark_identity, markdown, report
)
from tracker import providers


class PerformanceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()

        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(
                   code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (9901,"Nifty Small Cap Direct Growth","Nifty Test Small Cap Fund",
                     "Nifty AMC","Direct","Growth","test"),
                    (9902,"BSE Small Cap Direct Growth","BSE Test Small Cap Fund",
                     "BSE AMC","Direct","Growth","test"),
                    (9903,"Unclear Small Cap Direct Growth","Unclear Test Small Cap Fund",
                     "Unclear AMC","Direct","Growth","test"),
                    (9904,"Nifty Small Cap Direct IDCW","Nifty Test Small Cap Fund",
                     "Nifty AMC","Direct","IDCW","test"),
                ],
            )

        start=date(2020,9,24);end=date(2026,9,24)
        points=[];d=start;i=0
        while d<=end:
            points.append((d.isoformat(),100+i*.1))
            d+=timedelta(days=7);i+=1
        if points[-1][0]!=end.isoformat():
            points.append((end.isoformat(),100+i*.1))
        for code in (9901,9902,9903,9904):
            db.save_nav(code,points,"https://www.amfiindia.com/spages/NAVAll.txt")

        db.save_benchmark(
            providers.BENCHMARK,
            [(d,v*2) for d,v in points],
            providers.NIFTY_PAGE,
        )
        db.metric(
            "Nifty Test Small Cap Fund","All","benchmark","2026-09-24",
            "NIFTY SmallCap 250 TRI","Reported","https://example.com/nifty","nifty-hash",
        )
        db.metric(
            "BSE Test Small Cap Fund","All","benchmark","2026-09-24",
            "BSE 250 SmallCap Index TRI","Reported","https://example.com/bse","bse-hash",
        )
        db.metric(
            "Unclear Test Small Cap Fund","All","benchmark","2026-09-24",
            "Nifty Smallcap 250","Reported","https://example.com/unclear","unclear-hash",
        )

    def tearDown(self):
        self.data_patch.stop();self.tmp.cleanup()

    def test_benchmark_identity_requires_explicit_total_return(self):
        nifty=benchmark_identity("Nifty Small Cap 250 Total Return Index (TRI)")
        self.assertEqual(nifty["canonical_tri_series"],providers.BENCHMARK)
        self.assertTrue(nifty["explicit_total_return"])

        bse=benchmark_identity("BSE 250 SmallCap Index TRI")
        self.assertEqual(bse["canonical_tri_series"],BSE_SERIES)
        self.assertTrue(bse["explicit_total_return"])

        unclear=benchmark_identity("Nifty Smallcap 250")
        self.assertIsNone(unclear["canonical_tri_series"])
        self.assertFalse(unclear["explicit_total_return"])

    def test_audit_separates_nav_eligibility_from_relevant_benchmark_series(self):
        audit=report()
        plans={x["code"]:x for x in audit["plans"]}

        nifty=plans[9901]
        self.assertTrue(nifty["display_returns_supported"])
        self.assertTrue(all(nifty["nav"]["horizons"][f"{y}Y"]["eligible"] for y in (1,3,5)))
        self.assertEqual(nifty["benchmark"]["status"],"reported_tri_ready")
        self.assertTrue(nifty["benchmark"]["reported_series"]["available"])
        self.assertEqual(nifty["benchmark"]["alternate_comparisons"],[])
        self.assertTrue(all(nifty["benchmark"]["overlap_horizons"][f"{y}Y"]["eligible"] for y in (1,3,5)))

        bse=plans[9902]
        self.assertEqual(bse["benchmark"]["reported_identity"]["canonical_tri_series"],BSE_SERIES)
        self.assertEqual(bse["benchmark"]["status"],"reported_tri_series_missing")
        self.assertFalse(bse["benchmark"]["reported_series"]["available"])
        self.assertEqual(len(bse["benchmark"]["alternate_comparisons"]),1)
        alternate=bse["benchmark"]["alternate_comparisons"][0]
        self.assertEqual(alternate["name"],providers.BENCHMARK)
        self.assertEqual(alternate["role"],"alternate_comparison")
        self.assertTrue(alternate["available"])
        self.assertGreater(alternate["overlap"]["observations"],2)
        self.assertIn("reported_tri_series_missing",bse["issues"])
        self.assertNotIn("website_default_benchmark_mismatch",bse["issues"])

        unclear=plans[9903]
        self.assertEqual(unclear["benchmark"]["status"],"benchmark_identity_not_explicit_tri")
        self.assertIn("benchmark_identity_not_explicit_tri",unclear["issues"])

        idcw=plans[9904]
        self.assertFalse(idcw["display_returns_supported"])
        self.assertNotIn("nav_1y_return_unavailable",idcw["issues"])

    def test_repair_priority_prefers_missing_bse_tri_history(self):
        audit=report()
        priorities=audit["repair_priorities"]
        self.assertEqual(priorities[0]["code"],"collect_bse_250_smallcap_tri")
        self.assertEqual(priorities[0]["affected_funds"],["BSE Test Small Cap Fund"])
        self.assertEqual(priorities[0]["affected_growth_plans"],1)
        self.assertFalse(priorities[0]["actionable"])
        self.assertEqual(priorities[1]["code"],"verify_non_tri_benchmark_identity")
        self.assertEqual(priorities[1]["affected_funds"],["Unclear Test Small Cap Fund"])

    def test_large_nav_gap_is_reported_without_filling_it(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(
                   code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9905,"Gap Small Cap Direct Growth","Gap Test Small Cap Fund",
                 "Gap AMC","Direct","Growth","test"),
            )
        db.save_nav(
            9905,
            [("2025-01-01",100),("2025-01-02",101),("2025-01-20",102),("2026-01-20",110)],
            "https://www.amfiindia.com/spages/NAVAll.txt",
        )
        db.metric(
            "Gap Test Small Cap Fund","All","benchmark","2026-01-20",
            "Nifty Smallcap 250 TRI","Reported","https://example.com/gap","gap-hash",
        )
        audit=report()
        row=next(x for x in audit["plans"] if x["code"]==9905)
        self.assertGreaterEqual(row["nav"]["gap_count_gt_7d"],1)
        self.assertGreaterEqual(row["nav"]["max_gap_days"],18)
        self.assertIn("nav_large_gap",row["issues"])
        priority=next(x for x in audit["repair_priorities"] if x["code"]=="review_nav_history_gaps")
        self.assertEqual(priority["affected_growth_plans"],1)
        self.assertEqual(len(db.rows("SELECT * FROM nav WHERE code=9905")),4)

    def test_reviewed_official_history_gap_is_visible_but_not_actionable(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(
                   code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (105989,"DSP Small Cap Fund Regular Growth","DSP Small Cap Fund",
                 "DSP Mutual Fund","Regular","Growth","test"),
            )
        db.save_nav(
            105989,
            [("2010-04-07",14.166),("2010-04-15",14.455),("2010-04-16",14.5)],
            "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx",
        )
        db.metric(
            "DSP Small Cap Fund","All","benchmark","2026-09-25",
            "BSE 250 SmallCap TRI","Reported","https://example.com/dsp-benchmark","dsp-benchmark",
        )
        audit=report()
        row=next(x for x in audit["plans"] if x["code"]==105989)
        self.assertEqual(row["nav"]["raw_gap_count_gt_7d"],1)
        self.assertEqual(row["nav"]["official_history_gap_count"],1)
        self.assertEqual(row["nav"]["gap_count_gt_7d"],0)
        self.assertEqual(row["nav"]["official_history_gaps"][0]["from"],"2010-04-07")
        self.assertEqual(row["nav"]["official_history_gaps"][0]["to"],"2010-04-15")
        self.assertNotIn("nav_large_gap",row["issues"])
        self.assertFalse(any(p["code"]=="review_nav_history_gaps" for p in audit["repair_priorities"]))
        rendered=markdown(audit)
        self.assertIn("Verified official-history NAV gaps",rendered)
        self.assertIn("2010-04-07",rendered)
        self.assertEqual(len(db.rows("SELECT * FROM nav WHERE code=105989")),3)

    def test_audit_is_read_only_and_markdown_uses_evidence_aware_policy(self):
        before={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in ("nav","benchmark","metrics","schemes")
        }
        audit=report();rendered=markdown(audit)
        after={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in before
        }
        self.assertEqual(before,after)
        self.assertIn("Historical performance and benchmark coverage audit",rendered)
        self.assertIn("collect_bse_250_smallcap_tri",rendered)
        self.assertNotIn("website_default",rendered)
        self.assertNotIn("website_default",str(audit))
        self.assertEqual(audit["comparison_policy"],{
            "default_role":"reported_benchmark",
            "automatic_substitution":False,
            "alternate_comparisons":"explicit_request_only",
        })
        self.assertEqual(audit["summary"]["reported_tri_series_missing_growth_plans"],1)
        self.assertEqual(audit["summary"]["retained_alternate_comparison_growth_plans"],1)
        self.assertNotIn("website_default_benchmark_mismatch",audit["summary"]["issue_counts"])


if __name__=="__main__":
    unittest.main()
