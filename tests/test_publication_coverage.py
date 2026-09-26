"""AMC-origin communication coverage audit checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers
from tracker.publication_coverage import markdown, report


class PublicationCoverageTests(unittest.TestCase):
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
                    (9801,"Alpha Direct Growth","Alpha Small Cap Fund","Alpha AMC","Direct","Growth","test"),
                    (9802,"Beta Direct Growth","Beta Small Cap Fund","Beta AMC","Direct","Growth","test"),
                    (9803,"Gamma Direct Growth","Gamma Small Cap Fund","Gamma AMC","Direct","Growth","test"),
                    (9804,"Kotak Direct Growth","Kotak Small Cap Fund","Kotak Mahindra Mutual Fund","Direct","Growth","test"),
                ],
            )
            c.execute("""INSERT INTO source_pages(amc_match,url,label,status)
                         VALUES(?,?,?,?)""",
                      ("Beta AMC","https://beta.example.com/market-outlook","Market Outlook","Checked"))
            c.execute("""INSERT INTO source_pages(amc_match,url,label,status)
                         VALUES(?,?,?,?)""",
                      ("Mahindra","https://mahindra.example.com/outlook","Market Outlook","Checked"))

        digest=db.archive(b"alpha-view","application/pdf")
        doc=providers.save_document(
            "Alpha Small Cap Fund","September Market Outlook",
            "https://alpha.example.com/market-outlook-september.pdf",
            "market view","AMC",published="2026-09-10",origin="AMC")
        providers.doc_version(doc,digest)

        # Third-party/user-import material must not satisfy AMC communication coverage.
        providers.save_document(
            "Gamma Small Cap Fund","External commentary",
            "https://example.net/commentary.pdf",
            "market view","AMC",published="2026-09-12",origin="User import")

    def tearDown(self):
        self.data_patch.stop();self.tmp.cleanup()

    def test_audit_counts_only_amc_origin_communication_classes(self):
        audit=report()
        rows={r["family"]:r for r in audit["funds"]}
        alpha=rows["Alpha Small Cap Fund"]
        beta=rows["Beta Small Cap Fund"]
        gamma=rows["Gamma Small Cap Fund"]
        kotak=rows["Kotak Small Cap Fund"]

        self.assertEqual(alpha["communication_count"],1)
        self.assertEqual(alpha["market_view_count"],1)
        self.assertEqual(alpha["archived_communication_count"],1)
        self.assertEqual(alpha["published_date_count"],1)
        self.assertEqual(alpha["issues"],[])

        self.assertEqual(beta["communication_count"],0)
        self.assertEqual(len(beta["registered_communication_sources"]),1)
        self.assertIn("no_amc_communications_collected",beta["issues"])

        self.assertEqual(gamma["communication_count"],0)
        self.assertEqual(gamma["registered_communication_sources"],[])
        self.assertIn("no_amc_communications_collected",gamma["issues"])
        self.assertEqual(kotak["registered_communication_sources"],[])
        self.assertIn("no_amc_communications_collected",kotak["issues"])

        self.assertEqual(audit["summary"]["funds_with_amc_communications"],1)
        self.assertEqual(audit["summary"]["funds_without_amc_communications"],3)
        self.assertEqual(audit["summary"]["communication_documents"],1)
        self.assertEqual(audit["summary"]["archived_communication_documents"],1)
        self.assertFalse(audit["policy"]["third_party_news_included"])

    def test_repair_priorities_separate_registered_from_discovery_work(self):
        priorities={p["code"]:p for p in report()["repair_priorities"]}
        self.assertEqual(
            priorities["review_registered_communication_sources"]["affected_funds"],
            ["Beta Small Cap Fund"])
        self.assertEqual(
            priorities["discover_first_party_communication_sources"]["affected_funds"],
            ["Gamma Small Cap Fund","Kotak Small Cap Fund"])
        self.assertTrue(priorities["review_registered_communication_sources"]["actionable"])

    def test_missing_published_date_is_visible_without_using_first_seen(self):
        digest=db.archive(b"letter","application/pdf")
        doc=providers.save_document(
            "Alpha Small Cap Fund","Letter to Unitholders",
            "https://alpha.example.com/unitholder-letter.pdf",
            "unitholder letter","Fund",published=None,origin="AMC")
        providers.doc_version(doc,digest)
        row=next(r for r in report()["funds"] if r["family"]=="Alpha Small Cap Fund")
        self.assertEqual(row["communication_count"],2)
        self.assertEqual(row["published_date_count"],1)
        self.assertIn("publication_date_missing",row["issues"])
        self.assertEqual(row["latest_published_at"],"2026-09-10")

    def test_audit_is_read_only_and_markdown_is_explicit_about_scope(self):
        before={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in ("documents","document_versions","source_pages","archives")
        }
        audit=report();rendered=markdown(audit)
        after={
            table:db.one(f"SELECT COUNT(*) n FROM {table}")["n"]
            for table in before
        }
        self.assertEqual(before,after)
        self.assertIn("AMC communication coverage audit",rendered)
        self.assertIn("third-party news is excluded",rendered)
        self.assertIn("review_registered_communication_sources",rendered)


if __name__=="__main__":
    unittest.main()
