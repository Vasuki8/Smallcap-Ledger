"""Kotak / Mirae Asset AMC communication recovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from tracker import kotak_communications as kotak
from scripts import refresh_kotak_mirae_communications as upgrade


def kotak_page():
    current={
        "id":6125,"reportName":"Monthly","subReportName":None,
        "pdfTitle":"Monthly Outlook PPT sept 2026",
        "pdfPath":"kotak_updates/Monthly/6125/Monthly Outlook PPT Sep 2026 V4.pdf",
        "fileName":"Monthly Outlook PPT Sep 2026 V4.pdf",
        "reportMonth":8,"reporYear":2026,"reporStatus":1,
        "publishedDate":"2026-09-09T00:00:00.000+05:30","monthString":"Sep",
    }
    august={
        "id":6066,"reportName":"Monthly","subReportName":None,
        "pdfTitle":"Monthly Outlook PPT august 2026",
        "pdfPath":"kotak_updates/Monthly/6066/DKode Market Outlook - August 2026.pdf",
        "fileName":"DKode Market Outlook - August 2026.pdf",
        "reportMonth":7,"reporYear":2026,"reporStatus":1,
        "publishedDate":"2026-08-06T00:00:00.000+05:30","monthString":"Aug",
    }
    payload={"pageData":{"data":{
        "_sfilelink":upgrade.KOTAK_CURRENT,
        "allPdfData":[current,august],
    }}}
    encoded=json.dumps(payload,separators=(",",":")).replace('"',"&q;").replace("&","&a;")
    # Restore the custom quote entity after ampersand escaping so the fixture
    # matches the live Kotak state shape (&q; and &a;).
    encoded=encoded.replace("&a;q;","&q;")
    return f"<html><body><script>{encoded}</script></body></html>".encode()


class KotakMiraeCommunicationTests(unittest.TestCase):
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
                    (9101,"Kotak Direct Growth",upgrade.KOTAK_FAMILY,
                     "Kotak Mahindra Mutual Fund","Direct","Growth","test"),
                    (9102,"Mirae Direct Growth",upgrade.MIRAE_FAMILY,
                     "Mirae Asset Mutual Fund","Direct","Growth","test"),
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
        self.assertIsNotNone(self.source("Kotak",upgrade.KOTAK_LISTING))
        self.assertIsNotNone(self.source("Mirae",upgrade.MIRAE_OUTLOOK))
        self.assertEqual(
            providers.classify("Annual Market Outlook 2026",upgrade.MIRAE_OUTLOOK),
            "market view")

    def test_kotak_state_binds_exact_current_download_title_and_date(self):
        row=kotak.current_publication(kotak_page())
        self.assertEqual(row["title"],"Monthly Outlook PPT sept 2026")
        self.assertEqual(row["published_at"],"2026-09-09")
        self.assertEqual(row["url"],upgrade.KOTAK_CURRENT)
        self.assertEqual(row["id"],6125)

    def test_kotak_state_uses_site_supplied_link_to_select_matching_record(self):
        body=kotak_page().replace(b"/6125/2026/8",b"/6066/2026/7",1)
        row=kotak.current_publication(body)
        self.assertEqual(row["id"],6066)
        self.assertEqual(row["published_at"],"2026-08-06")

    def test_kotak_state_rejects_link_without_matching_report_identity(self):
        body=kotak_page().replace(b"/6125/2026/8",b"/9999/2026/8",1)
        with self.assertRaisesRegex(ValueError,"does not uniquely identify"):
            kotak.current_publication(body)

    def test_kotak_ingest_archives_listing_and_current_pdf(self):
        page=kotak_page();pdf=b"%PDF-1.4 Kotak monthly market outlook"
        def fake_fetch(url,**kwargs):
            if url==kotak.LISTING:return self.archived(page,"text/html")
            if url==upgrade.KOTAK_CURRENT:return self.archived(pdf,"application/pdf")
            raise AssertionError(url)
        with patch("tracker.kotak_communications.providers.can_crawl",return_value=None):
            result=kotak.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],1)
        self.assertEqual(result["current"]["published_at"],"2026-09-09")
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (kotak.FAMILY,upgrade.KOTAK_CURRENT))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-09-09")
        self.assertEqual(row["versions"],1)

    def test_kotak_listing_routes_to_special_collector(self):
        with patch("tracker.kotak_communications.ingest",
                   return_value={"detail":"kotak detail"}) as ingest:
            self.assertEqual(disclosures.ingest_source(
                self.source("Kotak",upgrade.KOTAK_LISTING)),"kotak detail")
            ingest.assert_called_once_with()

    def test_mirae_direct_pdf_is_archived_without_inferred_date(self):
        pdf=b"%PDF-1.6 MIRAE ASSET Mutual Fund Annual Market Outlook 2026"
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(pdf,"application/pdf")), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(
                self.source("Mirae",upgrade.MIRAE_OUTLOOK))
        self.assertTrue(result.endswith("0 download/parser gaps"),result)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (upgrade.MIRAE_FAMILY,upgrade.MIRAE_OUTLOOK))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_recovery_gate_is_idempotent_and_requires_exact_current_shapes(self):
        kotak_pdf=b"%PDF-1.4 Kotak outlook"
        mirae_pdf=b"%PDF-1.6 Mirae outlook"

        def store(family,title,url,published,body):
            digest=db.archive(body,"application/pdf")
            did=providers.save_document(
                family,title,url,"market view","AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.KOTAK_LISTING:
                store(upgrade.KOTAK_FAMILY,"Monthly Outlook PPT sept 2026",
                      upgrade.KOTAK_CURRENT,"2026-09-09",kotak_pdf)
            elif url==upgrade.MIRAE_OUTLOOK:
                store(upgrade.MIRAE_FAMILY,"Annual Market Outlook 2026",
                      url,None,mirae_pdf)
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
