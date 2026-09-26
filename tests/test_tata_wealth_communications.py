"""Tata / The Wealth Company first-party communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures
from tracker import tata_wealth_communications as comm
from tracker.publication_coverage import report as publication_report


def tata_page():
    return b"""<html><body><h1>MARKET OUTLOOK</h1>
      <p>As on 31st August 2026</p><h3>Equity market</h3>
      <p>Market Outlook: banking and earnings discussion.</p>
    </body></html>"""


def wealth_page():
    return b"""<html><body><h1>Current Insights</h1>
      <a href="/media/daily-wealth-recap-30-april-2026.pdf">Daily Wealth Recap - 30 April 2026</a>
      <a href="/media/the-newsmaker-27-april-2026.pdf">The NewsMaker - 27 April 2026</a>
      <a href="/media/nfo-flyer.pdf">The Wealth Company Mid Cap Fund NFO Flyer - 23 June 2026</a>
    </body></html>"""


class TataWealthCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start();db.init()
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (8801,"Tata Direct Growth",comm.TATA_FAMILY,
                     "Tata Mutual Fund","Direct","Growth","test"),
                    (8802,"Wealth Direct Growth",comm.WEALTH_FAMILY,
                     "The Wealth Company Mutual Fund","Direct","Growth","test"),
                ],
            )
        disclosures.seed_sources()

    def tearDown(self):
        self.data_patch.stop();self.tmp.cleanup()

    def source(self,amc,url):
        return db.one("""SELECT * FROM source_pages
                         WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))

    @staticmethod
    def archived(body,typ):
        return body,db.archive(body,typ),typ

    def test_sources_registered_and_audit_recognizes_them(self):
        self.assertIsNotNone(self.source("Tata",comm.TATA_OUTLOOK))
        self.assertIsNotNone(self.source("The Wealth",comm.WEALTH_INSIGHTS))
        audit=publication_report()
        rows={r["family"]:r for r in audit["funds"]}
        self.assertEqual(len(rows[comm.TATA_FAMILY]["registered_communication_sources"]),1)
        self.assertEqual(len(rows[comm.WEALTH_FAMILY]["registered_communication_sources"]),1)

    def test_tata_retains_market_view_without_turning_as_of_into_publish_date(self):
        row=comm.parse_tata(tata_page())
        self.assertEqual(row["as_of"],"2026-08-31")
        self.assertIsNone(row["published_at"])
        with patch("tracker.tata_wealth_communications.providers.can_crawl",return_value=None):
            result=comm.ingest_tata(fetch_fn=lambda *a,**k:self.archived(tata_page(),"text/html"))
        self.assertEqual(result["retained"],1)
        doc=db.one("""SELECT kind,published_at FROM documents
                      WHERE family=? AND url=?""",(comm.TATA_FAMILY,comm.TATA_OUTLOOK))
        self.assertEqual(doc["kind"],"market view")
        self.assertIsNone(doc["published_at"])

    def test_wealth_filters_to_recap_and_newsmaker_with_explicit_dates(self):
        rows=comm.wealth_candidates(wealth_page())
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["published_at"],"2026-04-30")
        self.assertTrue(all(
            r["title"].startswith(("Daily Wealth Recap","The NewsMaker")) for r in rows
        ))

    def test_wealth_archives_only_validated_pdfs(self):
        def fake_fetch(url,**kwargs):
            if url==comm.WEALTH_INSIGHTS:return self.archived(wealth_page(),"text/html")
            return self.archived(b"%PDF-1.7 Wealth insight","application/pdf")
        with patch("tracker.tata_wealth_communications.providers.can_crawl",return_value=None):
            result=comm.ingest_wealth(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],2)
        count=db.one("""SELECT COUNT(*) n FROM documents WHERE family=? AND kind='market view'""",
                     (comm.WEALTH_FAMILY,))["n"]
        self.assertEqual(count,2)

    def test_disclosures_routes_both_sources(self):
        with patch("tracker.tata_wealth_communications.ingest_tata",
                   return_value={"detail":"tata detail"}) as tata:
            self.assertEqual(disclosures.ingest_source(
                self.source("Tata",comm.TATA_OUTLOOK)),"tata detail")
            tata.assert_called_once_with()
        with patch("tracker.tata_wealth_communications.ingest_wealth",
                   return_value={"detail":"wealth detail"}) as wealth:
            self.assertEqual(disclosures.ingest_source(
                self.source("The Wealth",comm.WEALTH_INSIGHTS)),"wealth detail")
            wealth.assert_called_once_with()


if __name__=="__main__":
    unittest.main()
