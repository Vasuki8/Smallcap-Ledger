"""Edelweiss/Franklin AMC communication source recovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from scripts import refresh_edelweiss_franklin_communications as upgrade


class EdelweissFranklinCommunicationTests(unittest.TestCase):
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
                    (9401,"Edelweiss Direct Growth","Edelweiss Small Cap Fund",
                     "Edelweiss Mutual Fund","Direct","Growth","test"),
                    (9402,"Franklin Direct Growth","Franklin India Small Cap Fund",
                     "Franklin Templeton Mutual Fund","Direct","Growth","test"),
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

    def test_sources_and_franklin_cdn_are_registered(self):
        rows=json.loads((db.ROOT/"tracker"/"sources.json").read_text())
        pairs={(r[0],r[1],r[2]) for r in rows}
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_INSIGHTS,"Fund & Market Insights"),pairs)
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_CURVE,"Debt Market Update - Curve"),pairs)
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_FACTOR,"Factor Investing Outlook 2026"),pairs)
        self.assertIn(("Franklin",upgrade.FRANKLIN_LATEST,"Latest Commentaries / Market Insights"),pairs)
        self.assertIn(("Franklin",upgrade.FRANKLIN_OUTLOOK,"Monthly Equity Outlook - August 2026"),pairs)
        self.assertTrue(disclosures.official_publication_url(
            "https://franklintempletonprod.widen.net/content/a/original/file.pdf","Franklin"))
        self.assertFalse(disclosures.official_publication_url(
            "https://franklintempletonprod.widen.net/content/a/original/file.pdf","Edelweiss"))

    def test_explicit_edelweiss_and_franklin_pages_are_market_views(self):
        self.assertEqual(
            providers.classify("Factor Investing Outlook 2026",upgrade.EDELWEISS_FACTOR),
            "market view")
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Factor Investing Outlook 2026",upgrade.EDELWEISS_FACTOR),
            "market view")
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Debt Market Update - Curve",upgrade.EDELWEISS_CURVE),
            "market view")
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Monthly Equity Outlook - August 2026",upgrade.FRANKLIN_OUTLOOK),
            "market view")
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Fund & Market Insights",upgrade.EDELWEISS_INSIGHTS))
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Latest Commentaries / Market Insights",upgrade.FRANKLIN_LATEST))

    def test_edelweiss_factor_page_promotes_first_party_viewpoint_pdf(self):
        html=f'''<html><head><meta property="article:published_time"
          content="2026-01-20T12:00:00+05:30"></head><body>
          <a href="{upgrade.EDELWEISS_FACTOR_PDF}">Click here</a></body></html>'''.encode()
        pdf=b"%PDF-1.4 factor outlook"
        def fake_fetch(url,**kwargs):
            if url==upgrade.EDELWEISS_FACTOR:return self.archived(html)
            if url==upgrade.EDELWEISS_FACTOR_PDF:return self.archived(pdf,"application/pdf")
            raise AssertionError(url)
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(self.source("Edelweiss",upgrade.EDELWEISS_FACTOR))
        self.assertIn("1 relevant links",result)
        page=db.one("""SELECT kind,published_at FROM documents
                       WHERE family='Edelweiss Small Cap Fund' AND url=?""",
                    (upgrade.EDELWEISS_FACTOR,))
        self.assertEqual(page["kind"],"market view")
        self.assertEqual(page["published_at"],"2026-01-20")
        child=db.one("""SELECT kind,COUNT(v.id) versions FROM documents d
                        LEFT JOIN document_versions v ON v.document_id=d.id
                        WHERE family='Edelweiss Small Cap Fund' AND url=?
                        GROUP BY d.id""",(upgrade.EDELWEISS_FACTOR_PDF,))
        self.assertEqual(child["kind"],"market view")
        self.assertEqual(child["versions"],1)

    def test_edelweiss_fund_market_context_is_narrow(self):
        source=self.source("Edelweiss",upgrade.EDELWEISS_INSIGHTS)
        self.assertEqual(
            disclosures.source_context_communication_kind(
                source,
                "https://www.edelweissmf.com/investor-insights/fund-market/factor-investing-2026-outlook",
                "Factor page"),
            "market view",
        )
        self.assertIsNone(disclosures.source_context_communication_kind(
            source,
            "https://www.edelweissmf.com/investor-insights/mutual-fund-investment-tips-and-articles/basics-of-mutual-fund",
            "Basics of Mutual Fund",
        ))

    def test_franklin_widen_viewer_archives_underlying_pdf_as_market_view(self):
        pdf_url=("https://franklintempletonprod.widen.net/content/iumw5bsyug/original/"
                 "ft-monthly-equity-market-outlook.pdf?u=sc3tep&download=true")
        html=f'<html><body><a href="{pdf_url}">Download</a></body></html>'.encode()
        pdf=b"%PDF-1.4 monthly equity outlook"
        def fake_fetch(url,**kwargs):
            if url==upgrade.FRANKLIN_OUTLOOK:return self.archived(html)
            if url==pdf_url:return self.archived(pdf,"application/pdf")
            raise AssertionError(url)
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",side_effect=fake_fetch), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(self.source("Franklin",upgrade.FRANKLIN_OUTLOOK))
        self.assertIn("1 relevant links",result)
        viewer=db.one("""SELECT kind,COUNT(v.id) versions FROM documents d
                         LEFT JOIN document_versions v ON v.document_id=d.id
                         WHERE family='Franklin India Small Cap Fund' AND url=?
                         GROUP BY d.id""",(upgrade.FRANKLIN_OUTLOOK,))
        self.assertEqual(viewer["kind"],"market view")
        self.assertEqual(viewer["versions"],1)
        child=db.one("""SELECT kind,COUNT(v.id) versions FROM documents d
                        LEFT JOIN document_versions v ON v.document_id=d.id
                        WHERE family='Franklin India Small Cap Fund' AND url=?
                        GROUP BY d.id""",(pdf_url,))
        self.assertEqual(child["kind"],"market view")
        self.assertEqual(child["versions"],1)

    def test_recovery_gate_requires_exact_evidence_and_is_idempotent(self):
        franklin_pdf=("https://franklintempletonprod.widen.net/content/iumw5bsyug/original/"
                      "ft-monthly-equity-market-outlook.pdf?u=sc3tep&download=true")
        curve_pdf="https://www.edelweissmf.com/Files/Insigths/viewpoint/curve-current.pdf"

        def store(family,title,url,kind,published=None):
            digest=db.archive((family+url).encode(),"text/html")
            did=providers.save_document(
                family,title,url,kind,"AMC",published=published,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.EDELWEISS_INSIGHTS:
                store("Edelweiss Small Cap Fund","Fund & Market Insights",url,"source page")
            elif url==upgrade.EDELWEISS_CURVE:
                store("Edelweiss Small Cap Fund","Debt Market Update - Curve",url,"market view")
                store("Edelweiss Small Cap Fund","Curve download",curve_pdf,"market view")
            elif url==upgrade.EDELWEISS_FACTOR:
                store("Edelweiss Small Cap Fund","Factor Investing Outlook 2026",url,"market view")
                store("Edelweiss Small Cap Fund","Factor download",upgrade.EDELWEISS_FACTOR_PDF,"market view")
            elif url==upgrade.FRANKLIN_LATEST:
                store("Franklin India Small Cap Fund","Latest Commentaries / Market Insights",url,"source page")
            elif url==upgrade.FRANKLIN_OUTLOOK:
                store("Franklin India Small Cap Fund","Monthly Equity Outlook - August 2026",url,"market view")
                store("Franklin India Small Cap Fund","Download",franklin_pdf,"market view")
            else:
                raise AssertionError(url)
            return "1 relevant links; 1 documents archived; 0 facts/holdings; 0 documents without extracted tables; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,5)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
