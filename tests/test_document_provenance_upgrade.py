"""Document conflict handling must preserve and upgrade reviewed AMC provenance."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers


FAMILY="Example Small Cap Fund"
URL="https://example-amc.test/report.pdf"


class DocumentProvenanceUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def row(self):
        return db.one(
            "SELECT title,kind,scope,origin,published_at FROM documents WHERE family=? AND url=?",
            (FAMILY,URL),
        )

    def test_reviewed_amc_discovery_upgrades_prior_user_import(self):
        providers.save_document(
            FAMILY,"Uploaded file",URL,"disclosure","Fund",
            origin="User import · unverified source",
        )
        providers.save_document(
            FAMILY,"September Market Outlook",URL,"market view","AMC",
            published="2026-09-10",origin="AMC",
        )
        self.assertEqual(self.row(),{
            "title":"September Market Outlook",
            "kind":"market view",
            "scope":"AMC",
            "origin":"AMC",
            "published_at":"2026-09-10",
        })

    def test_reviewed_amc_crawl_can_reclassify_existing_amc_record(self):
        providers.save_document(
            FAMILY,"September report",URL,"disclosure","Fund",origin="AMC",
        )
        providers.save_document(
            FAMILY,"September Market Outlook",URL,"market view","AMC",
            published="2026-09-10",origin="AMC",
        )
        self.assertEqual(self.row()["kind"],"market view")
        self.assertEqual(self.row()["scope"],"AMC")
        self.assertEqual(self.row()["title"],"September Market Outlook")

    def test_user_import_cannot_downgrade_or_relabel_verified_amc_record(self):
        providers.save_document(
            FAMILY,"Official Market Outlook",URL,"market view","AMC",
            published="2026-09-10",origin="AMC",
        )
        providers.save_document(
            FAMILY,"My local label",URL,"disclosure","Fund",
            origin="User import · unverified source",
        )
        self.assertEqual(self.row(),{
            "title":"Official Market Outlook",
            "kind":"market view",
            "scope":"AMC",
            "origin":"AMC",
            "published_at":"2026-09-10",
        })


if __name__=="__main__":
    unittest.main()
