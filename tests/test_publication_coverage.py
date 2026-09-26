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

    def test_documented_source_limitation_stays_visible_and_non_actionable(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9805,"Trust Direct Growth","Trustmf Small Cap Fund",
                 "Trust Mutual Fund","Direct","Growth","test"),
            )
        audit=report()
        row=next(r for r in audit["funds"] if r["family"]=="Trustmf Small Cap Fund")
        self.assertEqual(row["communication_count"],0)
        self.assertIn("no_amc_communications_collected",row["issues"])
        self.assertIn("communication_source_limitation",row["issues"])
        self.assertEqual(
            row["source_limitation"]["code"],
            "market_outlook_embedded_in_factsheets_only",
        )
        priorities={p["code"]:p for p in audit["repair_priorities"]}
        limited=priorities["documented_communication_source_limitation"]
        self.assertFalse(limited["actionable"])
        self.assertEqual(limited["affected_funds"],["Trustmf Small Cap Fund"])
        self.assertNotIn(
            "Trustmf Small Cap Fund",
            priorities["discover_first_party_communication_sources"]["affected_funds"],
        )

    def test_robots_blocked_archives_are_non_actionable_limitations(self):
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (9806,"Franklin Direct Growth","Franklin India Small Cap Fund",
                     "Franklin Templeton Mutual Fund","Direct","Growth","test"),
                    (9807,"Kotak 2 Direct Growth","Kotak Small Cap Fund",
                     "Kotak Mahindra Mutual Fund","Direct","Growth","test"),
                ],
            )
        providers.save_document(
            "Franklin India Small Cap Fund","Weekly Market Review",
            "https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries/test",
            "market view","AMC",published="2026-09-18",origin="AMC")
        providers.save_document(
            "Kotak Small Cap Fund","Monthly Outlook PPT sept 2026",
            "https://www.kotakmf.com/kotakmf/reportupload/download/Monthly/1/2026/8",
            "market view","AMC",published="2026-09-09",origin="AMC")
        audit=report()
        rows={r["family"]:r for r in audit["funds"]}
        self.assertIn("communication_archive_limitation",rows["Franklin India Small Cap Fund"]["issues"])
        self.assertIn("communication_archive_limitation",rows["Kotak Small Cap Fund"]["issues"])
        priorities={p["code"]:p for p in audit["repair_priorities"]}
        limited=priorities["documented_communication_archive_limitation"]
        self.assertFalse(limited["actionable"])
        self.assertEqual(
            limited["affected_funds"],
            ["Franklin India Small Cap Fund","Kotak Small Cap Fund"],
        )
        repairable=priorities.get("repair_unarchived_communication_documents",{})
        self.assertNotIn("Franklin India Small Cap Fund",repairable.get("affected_funds",[]))
        self.assertNotIn("Kotak Small Cap Fund",repairable.get("affected_funds",[]))

    def test_empty_first_party_asset_is_non_actionable_archive_limitation(self):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9808,"LIC Direct Growth","LIC Mf Small Cap Fund",
                 "LIC Mutual Fund","Direct","Growth","test"),
            )
        providers.save_document(
            "LIC Mf Small Cap Fund","LICMF Monthly Market Outlook January 2025",
            "https://www.licmf.com/assets/pdfs/monthly_market_outlook_jan_2025-985953721.pdf",
            "market view","AMC",origin="AMC")
        audit=report()
        row=next(r for r in audit["funds"] if r["family"]=="LIC Mf Small Cap Fund")
        self.assertIn("communication_document_not_archived",row["issues"])
        self.assertIn("communication_archive_limitation",row["issues"])
        self.assertEqual(
            row["archive_limitation"]["code"],
            "first_party_asset_returns_empty_response",
        )
        priorities={p["code"]:p for p in audit["repair_priorities"]}
        limited=priorities["documented_communication_archive_limitation"]
        self.assertFalse(limited["actionable"])
        self.assertIn("LIC Mf Small Cap Fund",limited["affected_funds"])
        self.assertNotIn(
            "LIC Mf Small Cap Fund",
            priorities.get("repair_unarchived_communication_documents",{}).get("affected_funds",[]),
        )

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
