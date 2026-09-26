"""Bajaj/Bandhan AMC communication source recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from tracker import db,disclosures,providers
from scripts import refresh_bajaj_bandhan_communications as upgrade


class BajajBandhanCommunicationTests(unittest.TestCase):
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
                    (9501,"Bajaj Direct Growth","Bajaj Finserv Small Cap Fund",
                     "Bajaj Finserv Mutual Fund","Direct","Growth","test"),
                    (9502,"Bandhan Direct Growth","Bandhan Small Cap Fund",
                     "Bandhan Mutual Fund","Direct","Growth","test"),
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
    def archived(body,typ="text/html"):
        return body,db.archive(body,typ),typ

    def test_sources_are_registered(self):
        for amc,url in upgrade.SOURCES:
            self.assertIsNotNone(self.source(amc,url),(amc,url))

    def test_bajaj_outlook_card_binds_title_viewer_and_exact_date(self):
        html=b'''<html><body>
          <div class="bx-main text-center">
            <span class="rbn">Personalized Video</span>
            <h5 class="my-3 w-100">EQUITY OUTLOOK MAY</h5>
            <a class="lnk mb-2" href="https://cobranding.bajajamc.com/Home/dynamicvideoslide/469/6jfeX8S/454">Download</a>
            <span class="dte">21/05/2026</span>
          </div>
          <div class="bx-main text-center">
            <h5>Flexi Cap Product Note</h5>
            <a class="lnk" href="https://cobranding.bajajamc.com/Home/dynamicvideoslide/999/x/1">Download</a>
            <span class="dte">21/05/2026</span>
          </div>
        </body></html>'''
        source=self.source("Bajaj",upgrade.BAJAJ_OUTLOOK)
        rows=disclosures.bajaj_outlook_candidates(BeautifulSoup(html,"html.parser"),source)
        self.assertEqual(rows,[(
            "EQUITY OUTLOOK MAY",upgrade.BAJAJ_VIEWER,"2026-05-21"
        )])
        wrong=dict(source);wrong["url"]=wrong["url"].replace("LId=51","LId=58")
        self.assertEqual(
            disclosures.bajaj_outlook_candidates(BeautifulSoup(html,"html.parser"),wrong),[])

    def test_bajaj_ingest_archives_exact_viewer_as_market_view(self):
        catalog=f'''<html><body>
          <div class="bx-main text-center">
            <h5>EQUITY OUTLOOK MAY</h5>
            <a class="lnk" href="{upgrade.BAJAJ_VIEWER}">Download</a>
            <span class="dte">21/05/2026</span>
          </div>
        </body></html>'''.encode()
        viewer=b"<html><body>Equity outlook video viewer</body></html>"
        def fake_fetch(url,**kwargs):
            if url==upgrade.BAJAJ_OUTLOOK:return self.archived(catalog)
            if url==upgrade.BAJAJ_VIEWER:return self.archived(viewer)
            raise AssertionError(url)
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch):
            result=disclosures.ingest_source(self.source("Bajaj",upgrade.BAJAJ_OUTLOOK))
        self.assertIn("1 relevant links",result)
        row=db.one("""SELECT d.kind,d.scope,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family='Bajaj Finserv Small Cap Fund' AND d.url=?
                      GROUP BY d.id""",(upgrade.BAJAJ_VIEWER,))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["scope"],"AMC")
        self.assertEqual(row["published_at"],"2026-05-21")
        self.assertEqual(row["versions"],1)

    def test_bandhan_exact_posts_are_market_views_with_source_date(self):
        html=b'''<html><head><title>Market Outlook - Equity - September - 2026</title></head>
        <body><h1>Market Outlook - Equity - September - 2026</h1>
        <p>By Author d / September 11, 2026</p></body></html>'''
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Market Outlook - Equity - September 2026",upgrade.BANDHAN_EQUITY),
            "market view")
        self.assertEqual(disclosures.explicit_publication_date(html,"text/html"),
                         "2026-09-11")
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Market Outlook",upgrade.BANDHAN_LANDING))

        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",return_value=self.archived(html)):
            result=disclosures.ingest_source(
                self.source("Bandhan",upgrade.BANDHAN_EQUITY))
        self.assertIn("Page archived",result)
        row=db.one("""SELECT kind,published_at FROM documents
                      WHERE family='Bandhan Small Cap Fund' AND url=?""",
                   (upgrade.BANDHAN_EQUITY,))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-09-11")

    def test_bandhan_landing_remains_source_page(self):
        shell=b"<html><body>You need to enable JavaScript to run this app.</body></html>"
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",return_value=self.archived(shell)):
            result=disclosures.ingest_source(
                self.source("Bandhan",upgrade.BANDHAN_LANDING))
        self.assertIn("no automatically readable",result)
        row=db.one("""SELECT kind,published_at FROM documents
                      WHERE family='Bandhan Small Cap Fund' AND url=?""",
                   (upgrade.BANDHAN_LANDING,))
        self.assertEqual(row["kind"],"source page")
        self.assertIsNone(row["published_at"])

    def test_recovery_gate_is_idempotent_and_requires_exact_evidence(self):
        def store(family,title,url,kind,published=None):
            digest=db.archive((family+url).encode(),"text/html")
            did=providers.save_document(
                family,title,url,kind,"AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.BAJAJ_OUTLOOK:
                store("Bajaj Finserv Small Cap Fund","Market Outlook",
                      url,"source page")
                store("Bajaj Finserv Small Cap Fund","EQUITY OUTLOOK MAY",
                      upgrade.BAJAJ_VIEWER,"market view","2026-05-21")
            elif url==upgrade.BANDHAN_LANDING:
                store("Bandhan Small Cap Fund","Market Outlook",
                      url,"source page")
            elif url==upgrade.BANDHAN_EQUITY:
                store("Bandhan Small Cap Fund","Market Outlook - Equity - September 2026",
                      url,"market view","2026-09-11")
            elif url==upgrade.BANDHAN_DEBT:
                store("Bandhan Small Cap Fund","Market Outlook - Debt - September 2026",
                      url,"market view","2026-09-11")
            else:
                raise AssertionError(url)
            return "1 relevant links; 1 documents archived; 0 facts/holdings; 0 documents without extracted tables; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,4)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
