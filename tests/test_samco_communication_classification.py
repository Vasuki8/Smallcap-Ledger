"""Samco communication classification regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,providers
from tracker.publication_coverage import report
from scripts import repair_samco_communication_classification as repair


class SamcoCommunicationClassificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (8401,"Samco Direct",repair.FAMILY,"Samco Mutual Fund","Direct","Growth","test"),
            )

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def test_classifier_does_not_treat_lien_request_form_as_unitholder_letter(self):
        self.assertEqual(
            providers.classify(
                "Lien Request Letter from Unit holder",
                "https://media1.samco.in/scomamc/amc_documents/Lienrequestletterfromunitholder.pdf",
            ),
            "disclosure",
        )
        self.assertEqual(
            providers.classify("Letter to Unitholders","https://example.com/letter.pdf"),
            "unitholder letter",
        )

    def test_migration_reclassifies_existing_lien_forms_only(self):
        # Simulate the retained pre-fix false association without invoking the
        # current ingestion guard, which correctly rejects this URL now.
        with db.connect() as c:
            lien=c.execute(
                """INSERT INTO documents(
                     family,title,kind,scope,url,first_seen,last_seen,origin)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (repair.FAMILY,"Lien Request Letter from Unit holder","unitholder letter","AMC",
                 "https://media1.samco.in/scomamc/amc_documents/Lienrequestletterfromunitholder_1.pdf",
                 db.now(),db.now(),"AMC"),
            ).lastrowid
        genuine=providers.save_document(
            repair.FAMILY,"Letter to Unitholders",
            "https://www.samcomf.com/letters/genuine.pdf",
            "unitholder letter","AMC",origin="AMC")
        self.assertTrue(repair.run())
        self.assertTrue(repair.run())
        self.assertEqual(db.one("SELECT kind FROM documents WHERE id=?",(lien,))["kind"],"disclosure")
        self.assertEqual(db.one("SELECT kind FROM documents WHERE id=?",(genuine,))["kind"],"unitholder letter")

    def test_audit_treats_remaining_samco_original_as_archive_limitation(self):
        did=providers.save_document(
            repair.FAMILY,"Samco Small Cap Fund - Scheme Presentation",
            "https://media1.samco.in/scomamc/media_uploads/SamcoSmallCapFund-SchemePresentatiom.pdf",
            "market view","AMC",origin="AMC")
        row=next(x for x in report()["funds"] if x["family"]==repair.FAMILY)
        self.assertEqual(row["communication_count"],1)
        self.assertEqual(row["archived_communication_count"],0)
        self.assertIn("communication_archive_limitation",row["issues"])
        priorities={p["code"]:p for p in report()["repair_priorities"]}
        self.assertIn(repair.FAMILY,priorities["documented_communication_archive_limitation"]["affected_funds"])
        self.assertNotIn(
            repair.FAMILY,
            priorities.get("repair_unarchived_communication_documents",{}).get("affected_funds",[]),
        )


if __name__=="__main__":
    unittest.main()
