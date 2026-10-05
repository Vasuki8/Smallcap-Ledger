"""Abakkus cross-scheme publication ownership regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers, disclosures
from tracker.app import documents
from tracker.publication_coverage import report
from tracker.publications import exclusion_reason

FAMILY="Abakkus Small Cap Fund"
AMC="Abakkus Mutual Fund"
BAD=("https://www.abakkusmf.com/img/docs/LiquidFund/"
     "Abakkus_Liquid_Fund_Presentation.pdf")
GOOD="https://insights.abakkusinvest.com/market-outlook-august-2026/"


class AbakkusPublicationOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9911,"Abakkus Small Cap Direct Growth",FAMILY,AMC,
                 "Direct","Growth","test"),
            )
            # Simulate the retained pre-fix false association without using the
            # new save_document guard. It deliberately has no archived version.
            c.execute(
                """INSERT INTO documents(
                       family,title,kind,scope,url,published_at,first_seen,last_seen,origin)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (FAMILY,"Scheme Presentation","market view","AMC",BAD,None,
                 db.now(),db.now(),"AMC"),
            )
        good=providers.save_document(
            FAMILY,"Market Outlook - August 2026",GOOD,
            "market view","AMC",published="2026-08-11",origin="AMC")
        h=db.archive(b"<html>Abakkus market outlook</html>","text/html")
        providers.doc_version(good,h)

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_liquid_fund_presentation_is_excluded_without_deleting_retained_row(self):
        shown=documents(9911)
        self.assertEqual([d["url"] for d in shown],[GOOD])
        self.assertEqual(db.one("SELECT COUNT(*) n FROM documents")["n"],2)
        self.assertIsNotNone(db.one("SELECT id FROM documents WHERE url=?",(BAD,)))

    def test_publication_audit_does_not_treat_false_liquid_fund_row_as_archive_gap(self):
        row=next(x for x in report()["funds"] if x["family"]==FAMILY)
        self.assertEqual(row["communication_count"],1)
        self.assertEqual(row["archived_communication_count"],1)
        self.assertEqual(row["issues"],[])

    def test_future_ingestion_rejects_liquid_fund_association_but_keeps_market_outlook(self):
        reason=exclusion_reason(AMC,BAD,"Scheme Presentation")
        self.assertIn("Liquid Fund",reason)
        self.assertFalse(disclosures.official_publication_url(BAD,"Abakkus"))
        self.assertIsNone(exclusion_reason(AMC,GOOD,"Market Outlook - August 2026"))
        with self.assertRaisesRegex(ValueError,"Liquid Fund"):
            providers.save_document(FAMILY,"Scheme Presentation",BAD,"market view","AMC")


if __name__=="__main__":
    unittest.main()
