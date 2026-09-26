"""SBI / Sundaram AMC communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from scripts import refresh_sbi_sundaram_communications as upgrade


class SbiSundaramCommunicationTests(unittest.TestCase):
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
                    (8901,"SBI Direct Growth",upgrade.SBI_FAMILY,
                     "SBI Mutual Fund","Direct","Growth","test"),
                    (8902,"Sundaram Direct Growth",upgrade.SUNDARAM_FAMILY,
                     "Sundaram Mutual Fund","Direct","Growth","test"),
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

    def test_sources_are_registered(self):
        self.assertIsNotNone(self.source("SBI",upgrade.SBI_OUTLOOK))
        self.assertIsNotNone(self.source("Sundaram",upgrade.SUNDARAM_OUTLOOK))
        self.assertTrue(disclosures.official_publication_url(
            upgrade.SUNDARAM_OUTLOOK,"Sundaram"))

    def test_sbi_exact_page_is_market_view_with_explicit_published_date(self):
        body=(b"<html><body><h1>2026 Outlook</h1>"
              b"<p>Published 8th January 2026</p>"
              b"<h2>Executive Summary</h2>"
              b"<p>Rajeev Radhakrishnan, CFA, CIO - Fixed Income</p></body></html>")
        self.assertEqual(
            disclosures.dated_communication_source_kind("2026 Outlook",upgrade.SBI_OUTLOOK),
            "market view")
        self.assertEqual(
            disclosures.explicit_publication_date(body,"text/html",upgrade.SBI_OUTLOOK),
            "2026-01-08")

    def test_sbi_generic_ingest_retains_exact_page(self):
        body=(b"<html><body><h1>2026 Outlook</h1>"
              b"<p>Published 8th January 2026</p>"
              b"<h2>Executive Summary</h2>"
              b"<p>Rajeev Radhakrishnan, CFA, CIO - Fixed Income</p></body></html>")
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(body,"text/html")):
            disclosures.ingest_source(self.source("SBI",upgrade.SBI_OUTLOOK))
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (upgrade.SBI_FAMILY,upgrade.SBI_OUTLOOK))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-01-08")
        self.assertEqual(row["versions"],1)

    def test_sundaram_direct_outlook_pdf_is_market_view_without_inferred_day(self):
        pdf=b"%PDF-1.6 Sundaram Mutual Fund EQUITY OUTLOOK FIXED INCOME OUTLOOK"
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(pdf,"application/pdf")), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(
                self.source("Sundaram",upgrade.SUNDARAM_OUTLOOK))
        self.assertTrue(result.endswith("0 download/parser gaps"),result)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (upgrade.SUNDARAM_FAMILY,upgrade.SUNDARAM_OUTLOOK))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_recovery_gate_is_idempotent_and_requires_exact_evidence(self):
        sbi=(b"<html><body><h1>2026 Outlook</h1>"
             b"<p>Published 8th January 2026</p><h2>Executive Summary</h2>"
             b"<p>Rajeev Radhakrishnan</p></body></html>")
        sundaram=b"%PDF-1.6 Sundaram outlook"

        def store(family,title,url,published,body,typ):
            digest=db.archive(body,typ)
            did=providers.save_document(
                family,title,url,"market view","AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.SBI_OUTLOOK:
                store(upgrade.SBI_FAMILY,"2026 Outlook",url,"2026-01-08",sbi,"text/html")
            elif url==upgrade.SUNDARAM_OUTLOOK:
                store(upgrade.SUNDARAM_FAMILY,"Market Outlook - June 2026",
                      url,None,sundaram,"application/pdf")
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
