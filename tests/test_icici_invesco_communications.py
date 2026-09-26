"""ICICI Prudential / Invesco India AMC communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from scripts import refresh_icici_invesco_communications as upgrade


class IciciInvescoCommunicationTests(unittest.TestCase):
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
                    (9201,"ICICI Direct Growth",upgrade.ICICI_FAMILY,
                     "ICICI Prudential Mutual Fund","Direct","Growth","test"),
                    (9202,"Invesco Direct Growth",upgrade.INVESCO_FAMILY,
                     "Invesco Mutual Fund","Direct","Growth","test"),
                ],
            )
        disclosures.seed_sources()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def source(self,amc,url):
        return db.one("""SELECT * FROM source_pages
                         WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))

    @staticmethod
    def archived(body,typ):
        return body,db.archive(body,typ),typ

    def test_sources_are_registered_as_communications(self):
        self.assertIsNotNone(self.source("ICICI",upgrade.ICICI_OUTLOOK))
        self.assertIsNotNone(self.source("Invesco",upgrade.INVESCO_OUTLOOK))
        self.assertEqual(
            providers.classify("Monthly Market Outlook - August 2026",upgrade.ICICI_OUTLOOK),
            "market view")
        self.assertEqual(
            providers.classify("Market Outlook - April 2026",upgrade.INVESCO_OUTLOOK),
            "market view")

    def test_icici_release_date_is_explicitly_bound_from_first_party_path(self):
        body=(b"<html><body><h1>Equity Market Outlook</h1>"
              b"<h2>Fixed Income Outlook</h2>"
              b"<p>ICICI Prudential Mutual Fund</p></body></html>")
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Monthly Market Outlook - August 2026",upgrade.ICICI_OUTLOOK),
            "market view")
        self.assertEqual(
            disclosures.explicit_publication_date(
                body,"text/html",upgrade.ICICI_OUTLOOK),
            "2026-08-11")

        unrelated=upgrade.ICICI_OUTLOOK.replace(
            "Release%20date%2011-08-2026","Draft%20date%2011-08-2026")
        self.assertIsNone(disclosures.explicit_publication_date(
            body,"text/html",unrelated))

    def test_icici_generic_ingest_archives_page_as_market_view_with_release_date(self):
        body=(b"<html><body><h1>Equity Market Outlook</h1>"
              b"<h2>Fixed Income Outlook</h2>"
              b"<p>ICICI Prudential Mutual Fund</p></body></html>")
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(body,"text/html")):
            result=disclosures.ingest_source(
                self.source("ICICI",upgrade.ICICI_OUTLOOK))
        self.assertIn("Page archived",result)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (upgrade.ICICI_FAMILY,upgrade.ICICI_OUTLOOK))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-08-11")
        self.assertEqual(row["versions"],1)

    def test_invesco_direct_pdf_is_market_view_without_inferred_day(self):
        pdf=b"%PDF-1.4 Invesco Market Outlook"
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(pdf,"application/pdf")), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(
                self.source("Invesco",upgrade.INVESCO_OUTLOOK))
        self.assertTrue(result.endswith("0 download/parser gaps"),result)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (upgrade.INVESCO_FAMILY,upgrade.INVESCO_OUTLOOK))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_recovery_gate_is_idempotent_and_checks_exact_source_shapes(self):
        icici=(b"<html><body><h1>Equity Market Outlook</h1>"
               b"<h2>Fixed Income Outlook</h2>"
               b"<p>ICICI Prudential Mutual Fund</p></body></html>")
        invesco=b"%PDF-1.4 Invesco Market Outlook"

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.ICICI_OUTLOOK:
                digest=db.archive(icici,"text/html")
                did=providers.save_document(
                    upgrade.ICICI_FAMILY,"Monthly Market Outlook - August 2026",
                    url,"market view","AMC",published="2026-08-11",origin="AMC")
                providers.doc_version(did,digest)
            elif url==upgrade.INVESCO_OUTLOOK:
                digest=db.archive(invesco,"application/pdf")
                did=providers.save_document(
                    upgrade.INVESCO_FAMILY,"Market Outlook - April 2026",
                    url,"market view","AMC",published=None,origin="AMC")
                providers.doc_version(did,digest)
            else:
                raise AssertionError(url)
            return "communication retained; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,2)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
