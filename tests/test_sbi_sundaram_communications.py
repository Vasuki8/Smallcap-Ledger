"""SBI / Sundaram first-party communication recovery checks."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from tracker import sbi_sundaram_communications as comm
from tracker.publication_coverage import report as publication_report
from scripts import refresh_sbi_sundaram_communications as upgrade


def sbi_listing():
    return b"""<html><body><h1>Monthly Outlook Videos</h1>
      <a href="https://www.youtube.com/watch?v=x">04 Sep, 2026 Monthly Market Outlook September 2026</a>
    </body></html>"""


def sbi_outlook(year=2026):
    return f"""<html><body>
      <div>SBI Mutual Fund</div><h1>{year} Outlook</h1>
      <p>Published 8th January {year}</p>
      <h2>Equity Outlook</h2><h2>Fixed Income Outlook</h2>
    </body></html>""".encode()


def sundaram_hub():
    return b"<html><body><div>Sundaram Mutual Fund</div><h1>Knowledge Hub</h1></body></html>"


def sundaram_home():
    return b"""<html><body>
      <h2>Knowledge Hub</h2>
      <article>Outlook September 2026 Wondering how Equity & FI Markets did in August?</article>
      <article>E.M.I - September 2026</article>
      <article>Outlook August 2026 Wondering how Equity & FI Markets did in July?</article>
      <article>Outlook July 2026 Wondering how Equity & FI Markets did in June?</article>
    </body></html>"""


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
                    (8901,"SBI Direct Growth",comm.SBI_FAMILY,
                     "SBI Mutual Fund","Direct","Growth","test"),
                    (8902,"Sundaram Direct Growth",comm.SUNDARAM_FAMILY,
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

    def test_sources_are_registered_and_audit_recognizes_them(self):
        self.assertIsNotNone(self.source("SBI",comm.SBI_LISTING))
        self.assertIsNotNone(self.source("Sundaram",comm.SUNDARAM_HUB))
        audit=publication_report()
        rows={r["family"]:r for r in audit["funds"]}
        self.assertEqual(len(rows[comm.SBI_FAMILY]["registered_communication_sources"]),1)
        self.assertEqual(len(rows[comm.SUNDARAM_FAMILY]["registered_communication_sources"]),1)

    def test_sbi_parser_keeps_only_explicit_first_party_date(self):
        row=comm.parse_sbi_outlook(sbi_outlook(),comm.sbi_outlook_url(2026))
        self.assertEqual(row["title"],"2026 Outlook")
        self.assertEqual(row["published_at"],"2026-01-08")
        with self.assertRaises(ValueError):
            comm.parse_sbi_outlook(sbi_outlook(),"https://example.com/2026-outlook")

    def test_sbi_ingest_archives_listing_and_current_annual_outlook(self):
        def fake_fetch(url,**kwargs):
            if url==comm.SBI_LISTING:
                return self.archived(sbi_listing(),"text/html")
            if url==comm.sbi_outlook_url(2026):
                return self.archived(sbi_outlook(),"text/html")
            if url==comm.sbi_outlook_url(2025):
                raise ValueError("older page not required in fixture")
            raise AssertionError(url)
        with patch("tracker.sbi_sundaram_communications.providers.can_crawl",return_value=None):
            result=comm.ingest_sbi(fetch_fn=fake_fetch,today=date(2026,9,26))
        self.assertEqual(result["retained"],1)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (comm.SBI_FAMILY,comm.sbi_outlook_url(2026)))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-01-08")
        self.assertEqual(row["versions"],1)

    def test_sundaram_candidates_are_bound_to_visible_outlook_cards(self):
        rows=comm.sundaram_candidates(sundaram_home())
        self.assertEqual([r["title"] for r in rows],[
            "Outlook September 2026","Outlook August 2026","Outlook July 2026"])
        self.assertEqual(rows[0]["url"],
                         comm.sundaram_outlook_url("September",2026))
        self.assertTrue(all(r["published_at"] is None for r in rows))

    def test_sundaram_ingest_archives_only_verified_pdf_responses(self):
        pdf=b"%PDF-1.7 Sundaram Mutual Fund Outlook"
        def fake_fetch(url,**kwargs):
            if url==comm.SUNDARAM_HUB:
                return self.archived(sundaram_hub(),"text/html")
            if url==comm.SUNDARAM_HOME:
                return home_response
            if url.startswith(comm.SUNDARAM_PDF_PREFIX):
                return self.archived(pdf,"application/pdf")
            raise AssertionError(url)
        home_response=(sundaram_home(),None,"text/html")
        with patch("tracker.sbi_sundaram_communications.providers.can_crawl",return_value=None):
            result=comm.ingest_sundaram(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],3)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (comm.SUNDARAM_FAMILY,
                    comm.sundaram_outlook_url("September",2026)))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_disclosures_routes_both_dedicated_sources(self):
        with patch("tracker.sbi_sundaram_communications.ingest_sbi",
                   return_value={"detail":"sbi detail"}) as sbi:
            self.assertEqual(disclosures.ingest_source(
                self.source("SBI",comm.SBI_LISTING)),"sbi detail")
            sbi.assert_called_once_with()
        with patch("tracker.sbi_sundaram_communications.ingest_sundaram",
                   return_value={"detail":"sundaram detail"}) as sundaram:
            self.assertEqual(disclosures.ingest_source(
                self.source("Sundaram",comm.SUNDARAM_HUB)),"sundaram detail")
            sundaram.assert_called_once_with()

    def test_recovery_gate_is_idempotent_and_requires_anchor_evidence(self):
        def store(family,title,url,body,published=None):
            typ="application/pdf" if body.startswith(b"%PDF") else "text/html"
            digest=db.archive(body,typ)
            did=providers.save_document(
                family,title,url,"market view","AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            if source["url"]==comm.SBI_LISTING:
                store(comm.SBI_FAMILY,"2026 Outlook",upgrade.SBI_ANCHOR,
                      sbi_outlook(),published="2026-01-08")
            elif source["url"]==comm.SUNDARAM_HUB:
                for month in ("September","August","July"):
                    store(comm.SUNDARAM_FAMILY,f"Outlook {month} 2026",
                          comm.sundaram_outlook_url(month,2026),
                          b"%PDF-1.7 Sundaram")
            else:
                raise AssertionError(source["url"])
            return "communication retained; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,2)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
