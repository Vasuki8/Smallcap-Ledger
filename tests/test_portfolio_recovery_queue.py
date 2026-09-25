"""Read-only portfolio recovery queue regression checks."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures
from tracker.portfolio_recovery_queue import report, markdown


class PortfolioRecoveryQueueTests(unittest.TestCase):
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
                    (9801,"Axis Small Cap Direct Growth","Axis Small Cap Fund","Axis Mutual Fund","Direct","Growth","test"),
                    (9802,"Bajaj Finserv Small Cap Direct Growth","Bajaj Finserv Small Cap Fund","Bajaj Finserv Mutual Fund","Direct","Growth","test"),
                    (9803,"Bandhan Small Cap Direct Growth","Bandhan Small Cap Fund","Bandhan Mutual Fund","Direct","Growth","test"),
                    (9804,"Union Small Cap Direct Growth","Union Small Cap Fund","Union Mutual Fund","Direct","Growth","test"),
                ],
            )
        self.axis_source=(
            "https://www.axismf.com/mutual-funds/equity-funds/"
            "axis-small-cap-fund/sc-dg/direct"
        )
        self.bajaj_source=(
            "https://media.bajajamc.com/wp-content/uploads/2026/02/"
            "Bajaj-Finserv-Small-Cap-Fund_August-2026.pdf"
        )
        self.bandhan_source=(
            "https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/"
            "2026/09/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx"
        )
        disclosures.portfolio(
            "Axis Small Cap Fund","2026-09-16",
            [{"name":"Axis Example Limited","weight":3.0}],
            False,self.axis_source,"axis-hash",
        )
        disclosures.portfolio(
            "Bajaj Finserv Small Cap Fund","2026-07-31",
            [{"name":"Bajaj Example Limited","weight":3.0}],
            False,self.bajaj_source,"bajaj-hash",
        )
        # More retained rows must not make a blocked precision case outrank Axis.
        disclosures.portfolio(
            "Bandhan Small Cap Fund","2026-08-31",
            [{"name":f"Bandhan Example {i} Limited","weight":0.1} for i in range(100)],
            False,self.bandhan_source,"bandhan-hash",
        )
        with db.connect() as c:
            c.execute(
                """INSERT INTO source_pages(
                   amc_match,url,label,kind,enabled,last_checked,status,detail)
                   VALUES(?,?,?,?,?,?,?,?)""",
                ("Union","https://www.unionmf.com/about-us/downloads/monthly-portfolio",
                 "Monthly portfolio","disclosure",1,"2026-09-25T04:18:00+00:00",
                 "Gap","[Errno 111] Connection refused"),
            )
            c.execute(
                """INSERT INTO fetches(url,fetched_at,status,hash,detail)
                   VALUES(?,?,?,?,?)""",
                (self.axis_source,"2026-09-25T04:00:00+00:00","ok","axis-hash",None),
            )

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_queue_ranks_actionability_before_positions_or_staleness(self):
        queue=report(today=date(2026,9,25))
        self.assertEqual(queue["summary"]["items"],4)
        self.assertEqual(queue["summary"]["actionable_now"],1)
        self.assertEqual(queue["summary"]["stale_partial"],1)
        self.assertEqual(queue["summary"]["missing"],1)
        self.assertEqual(queue["summary"]["source_changes_detected"],0)

        items={x["family"]:x for x in queue["items"]}
        self.assertEqual(queue["next_recovery_target"]["family"],"Axis Small Cap Fund")
        self.assertEqual(items["Axis Small Cap Fund"]["rank"],1)
        self.assertEqual(items["Axis Small Cap Fund"]["action"],
                         "search_fuller_first_party_disclosure")
        self.assertTrue(items["Axis Small Cap Fund"]["actionable_now"])

        self.assertEqual(items["Bajaj Finserv Small Cap Fund"]["state"],"partial_stale")
        self.assertEqual(items["Bajaj Finserv Small Cap Fund"]["action"],
                         "retry_after_source_change")
        self.assertFalse(items["Bajaj Finserv Small Cap Fund"]["actionable_now"])
        self.assertEqual(items["Bandhan Small Cap Fund"]["action"],
                         "requires_more_precise_amc_disclosure")
        self.assertFalse(items["Bandhan Small Cap Fund"]["actionable_now"])
        self.assertEqual(items["Union Small Cap Fund"]["state"],"missing")
        self.assertEqual(items["Union Small Cap Fund"]["action"],
                         "retry_after_source_change")

    def test_queue_includes_exact_source_and_retained_check_evidence(self):
        queue=report(today=date(2026,9,25))
        items={x["family"]:x for x in queue["items"]}
        axis=items["Axis Small Cap Fund"]
        self.assertEqual(axis["source_url"],self.axis_source)
        self.assertEqual(axis["reporting_date"],"2026-09-16")
        self.assertEqual(axis["limitation"]["code"],"undisclosed_constituents")
        self.assertEqual(axis["evidence"]["latest_fetch"]["status"],"ok")
        self.assertEqual(axis["evidence"]["latest_fetch"]["fetched_at"],
                         "2026-09-25T04:00:00+00:00")

        union=items["Union Small Cap Fund"]
        self.assertEqual(
            union["source_url"],
            "https://www.unionmf.com/about-us/downloads/monthly-portfolio",
        )
        self.assertEqual(union["limitation"]["code"],"upstream_source_unavailable")
        page=union["evidence"]["latest_source_page_check"]
        self.assertEqual(page["match"],"exact_url")
        self.assertEqual(page["status"],"Gap")
        self.assertIn("Connection refused",page["detail"])

    def test_union_transport_recovery_is_promoted_for_review_without_retrying(self):
        with db.connect() as c:
            c.execute(
                """UPDATE source_pages
                   SET last_checked=?,status=?,detail=?
                   WHERE amc_match='Union'""",
                ("2026-09-25T05:00:00+00:00","Checked",
                 "Official downloads page reachable; review before retry"),
            )
        queue=report(today=date(2026,9,25))
        union=next(x for x in queue["items"] if x["family"]=="Union Small Cap Fund")
        self.assertTrue(union["source_change_watch"]["changed"])
        self.assertEqual(
            union["source_change_watch"]["change_reason"],
            "recovery_url_source_check_recovered",
        )
        self.assertEqual(union["action"],"review_source_change")
        self.assertTrue(union["actionable_now"])
        self.assertEqual(union["actionability_score"],95)
        self.assertEqual(queue["summary"]["source_changes_detected"],1)
        self.assertEqual(queue["next_recovery_target"]["family"],"Union Small Cap Fund")

    def test_exact_recovery_fetch_success_promotes_bajaj_for_review(self):
        recovery="https://www.bajajamc.com/downloads"
        with db.connect() as c:
            c.execute(
                """INSERT INTO fetches(url,fetched_at,status,hash,detail)
                   VALUES(?,?,?,?,?)""",
                (recovery,"2026-09-25T05:01:00+00:00","ok","new-bajaj-page",None),
            )
        queue=report(today=date(2026,9,25))
        bajaj=next(
            x for x in queue["items"] if x["family"]=="Bajaj Finserv Small Cap Fund"
        )
        watch=bajaj["source_change_watch"]
        self.assertTrue(watch["changed"])
        self.assertEqual(watch["change_reason"],"recovery_url_fetch_succeeded")
        self.assertEqual(watch["exact_recovery_fetch"]["url"],recovery)
        self.assertEqual(bajaj["action"],"review_source_change")
        self.assertTrue(bajaj["actionable_now"])

    def test_old_recovery_success_before_review_does_not_reopen_blocker(self):
        recovery="https://www.bajajamc.com/downloads"
        with db.connect() as c:
            c.execute(
                """INSERT INTO fetches(url,fetched_at,status,hash,detail)
                   VALUES(?,?,?,?,?)""",
                (recovery,"2026-09-25T03:00:00+00:00","ok","old-bajaj-page",None),
            )
        queue=report(today=date(2026,9,25))
        bajaj=next(
            x for x in queue["items"] if x["family"]=="Bajaj Finserv Small Cap Fund"
        )
        self.assertFalse(bajaj["source_change_watch"]["changed"])
        self.assertEqual(bajaj["action"],"retry_after_source_change")
        self.assertFalse(bajaj["actionable_now"])

    def test_new_first_party_portfolio_document_after_review_triggers_review(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO documents(
                   family,title,kind,scope,url,published_at,first_seen,last_seen,origin)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                ("Bajaj Finserv Small Cap Fund","September monthly portfolio","portfolio",
                 "Scheme","https://www.bajajamc.com/new/axis-free-bajaj-portfolio.xlsx",
                 "2026-09-30","2026-09-25T05:02:00+00:00",
                 "2026-09-25T05:02:00+00:00","AMC"),
            )
        queue=report(today=date(2026,9,25))
        bajaj=next(
            x for x in queue["items"] if x["family"]=="Bajaj Finserv Small Cap Fund"
        )
        watch=bajaj["source_change_watch"]
        self.assertTrue(watch["changed"])
        self.assertEqual(watch["change_reason"],"new_first_party_portfolio_document")
        self.assertEqual(
            watch["new_portfolio_document"]["title"],"September monthly portfolio"
        )

    def test_queue_is_read_only(self):
        before={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in ("portfolios","holdings","metrics","fetches","source_pages","documents")
        }
        report(today=date(2026,9,25))
        after={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in before
        }
        self.assertEqual(after,before)

    def test_unclassified_changed_source_is_highest_priority_for_review(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9805,"Changed Small Cap Direct Growth","Changed Small Cap Fund",
                 "Changed Mutual Fund","Direct","Growth","test"),
            )
        disclosures.portfolio(
            "Changed Small Cap Fund","2026-08-31",
            [{"name":"Changed Example Limited","weight":5.0}],
            False,"https://example.com/new-source.xlsx","changed-hash",
        )
        queue=report(today=date(2026,9,25))
        first=queue["items"][0]
        self.assertEqual(first["family"],"Changed Small Cap Fund")
        self.assertEqual(first["limitation"]["code"],"partial_reason_unclassified")
        self.assertEqual(first["action"],"review_changed_partial_source")
        self.assertEqual(first["actionability_score"],100)

    def test_markdown_names_next_target_and_exact_recovery_conditions(self):
        queue=report(today=date(2026,9,25))
        rendered=markdown(queue)
        self.assertIn("**Axis Small Cap Fund**",rendered)
        self.assertIn("search_fuller_first_party_disclosure",rendered)
        self.assertIn("https://www.bajajamc.com/downloads",rendered)
        self.assertIn("retry_after_source_change",rendered)
        self.assertIn("Source change",rendered)
        self.assertIn("Read-only",rendered)


if __name__=="__main__":
    unittest.main()
