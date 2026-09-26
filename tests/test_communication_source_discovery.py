"""Abakkus/Axis AMC communication source-discovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures
from tracker import providers
from scripts import refresh_abakkus_axis_communications as upgrade


ABAKKUS_TAG="https://insights.abakkusinvest.com/tag/market-outlook/"
ABAKKUS_AUG="https://insights.abakkusinvest.com/market-outlook-august-2026/"
AXIS_TAG="https://www.axismf.com/mutual-fund-knowledge-centre/articles?tag=Market-Outlook"
AXIS_ARTICLE="https://www.axismf.com/mutual-fund-knowledge-centre/articles/union-budget-2026-impact-on-mutual-funds"
AXIS_OUTLOOK="https://www.axismf.com/cms/sites/default/files/pdf-factsheets/Axis%20MF_%20Annual%20Equity%20Outlook%202026.pdf"


class CommunicationSourceDiscoveryTests(unittest.TestCase):
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
                    (9601,"Abakkus Direct Growth","Abakkus Small Cap Fund",
                     "Abakkus Mutual Fund","Direct","Growth","test"),
                    (9602,"Axis Direct Growth","Axis Small Cap Fund",
                     "Axis Mutual Fund","Direct","Growth","test"),
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

    def test_bundled_sources_include_dynamic_and_current_evidence(self):
        rows=json.loads((db.ROOT/"tracker"/"sources.json").read_text())
        pairs={(r[0],r[1],r[2]) for r in rows}
        self.assertIn(("Abakkus",ABAKKUS_TAG,"Market Outlook"),pairs)
        self.assertIn(("Abakkus",ABAKKUS_AUG,"Market Outlook - August 2026"),pairs)
        self.assertIn(("Axis",AXIS_TAG,"Market Outlook"),pairs)
        self.assertIn(("Axis",AXIS_OUTLOOK,"Annual Equity Outlook 2026"),pairs)

    def test_abakkus_dated_outlook_is_market_view_with_explicit_date(self):
        tag_html=f'<html><body><a href="{ABAKKUS_AUG}">Market Outlook - August 2026</a></body></html>'.encode()
        article_html=b'''<html><head><title>Market Outlook - August 2026</title></head>
          <body><p>Last updated on 11 Aug 2026</p><p>Indian equities extended their recovery.</p></body></html>'''
        def fake_fetch(url,**kwargs):
            if url==ABAKKUS_TAG:return self.archived(tag_html)
            if url==ABAKKUS_AUG:return self.archived(article_html)
            raise AssertionError(url)
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch):
            result=disclosures.ingest_source(self.source("Abakkus",ABAKKUS_TAG))
        self.assertIn("1 relevant links",result)
        row=db.one("""SELECT d.kind,d.scope,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family='Abakkus Small Cap Fund' AND d.url=?
                      GROUP BY d.id""",(ABAKKUS_AUG,))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["scope"],"AMC")
        self.assertEqual(row["published_at"],"2026-08-11")
        self.assertEqual(row["versions"],1)

    def test_axis_market_outlook_category_supplies_child_context_and_date(self):
        tag_html=f'<html><body><a href="{AXIS_ARTICLE}">How Union Budget 2026 Affects Equity, Debt &amp; Hybrid Mutual Funds</a></body></html>'.encode()
        article_html=b'''<html><head><script type="application/ld+json">
          {"@type":"Article","datePublished":"2026-02-11T08:00:00+05:30"}
          </script></head><body><h1>How Union Budget 2026 Affects Mutual Funds</h1></body></html>'''
        def fake_fetch(url,**kwargs):
            if url==AXIS_TAG:return self.archived(tag_html)
            if url==AXIS_ARTICLE:return self.archived(article_html)
            raise AssertionError(url)
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch):
            result=disclosures.ingest_source(self.source("Axis",AXIS_TAG))
        self.assertIn("1 relevant links",result)
        row=db.one("""SELECT d.kind,d.scope,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family='Axis Small Cap Fund' AND d.url=?
                      GROUP BY d.id""",(AXIS_ARTICLE,))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["scope"],"AMC")
        self.assertEqual(row["published_at"],"2026-02-11")
        self.assertEqual(row["versions"],1)

    def test_market_outlook_context_is_narrow(self):
        axis=self.source("Axis",AXIS_TAG)
        self.assertEqual(
            disclosures.source_context_communication_kind(
                axis,AXIS_ARTICLE,"A title without the word outlook"),
            "market view",
        )
        self.assertIsNone(disclosures.source_context_communication_kind(
            axis,
            "https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct",
            "Axis Small Cap Fund",
        ))
        self.assertIsNone(disclosures.source_context_communication_kind(
            {"label":"Market Outlook","url":"https://example.com/outlook"},
            "https://other.example.com/article","Market article",
        ))

    def test_direct_market_view_pdf_does_not_create_parser_gap(self):
        body=b"%PDF-1.4 synthetic"
        def fake_fetch(url,**kwargs):
            self.assertEqual(url,AXIS_OUTLOOK)
            return self.archived(body,"application/pdf")
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(self.source("Axis",AXIS_OUTLOOK))
        self.assertTrue(result.endswith("0 download/parser gaps"),result)
        row=db.one("""SELECT kind FROM documents
                      WHERE family='Axis Small Cap Fund' AND url=?""",(AXIS_OUTLOOK,))
        self.assertEqual(row["kind"],"market view")

    def test_abakkus_exact_source_page_is_promotable_but_tag_directory_is_not(self):
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Market Outlook - August 2026",ABAKKUS_AUG),
            "market view",
        )
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Market Outlook",ABAKKUS_TAG))


    def test_recovery_gate_requires_both_dynamic_catalogs_and_is_idempotent(self):
        def store(family,title,url,kind,published=None):
            digest=db.archive((family+url).encode(),"text/html")
            did=providers.save_document(
                family,title,url,kind,"AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==ABAKKUS_TAG:
                store("Abakkus Small Cap Fund","Market Outlook",url,"source page")
                store("Abakkus Small Cap Fund","Market Outlook - August 2026",
                      ABAKKUS_AUG,"market view","2026-08-11")
            elif url==ABAKKUS_AUG:
                store("Abakkus Small Cap Fund","Market Outlook - August 2026",
                      url,"market view","2026-08-11")
            elif url==AXIS_TAG:
                store("Axis Small Cap Fund","Market Outlook",url,"source page")
                store("Axis Small Cap Fund","Budget market view",
                      AXIS_ARTICLE,"market view","2026-02-11")
            elif url==AXIS_OUTLOOK:
                store("Axis Small Cap Fund","Annual Equity Outlook 2026",
                      url,"market view")
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
