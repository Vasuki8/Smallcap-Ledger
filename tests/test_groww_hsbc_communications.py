"""Groww/HSBC AMC communication source recovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from tracker import groww_communications as groww
from tracker import hsbc_communications as hsbc
from tracker.publication_coverage import report as publication_report
from scripts import refresh_groww_hsbc_communications as upgrade


def groww_page():
    data=[
        {
            "id":1,
            "attributes":{
                "heading":"Fixed Income Weekly Wrap Up",
                "subheading":"Weekly snapshot of the key developments shaping India's fixed income markets.",
                "date":"2026-09-18",
                "report_type":"Fixed Income Weekly Wrapup",
                "file":{"data":{"attributes":{
                    "name":"Fixed Income Weekly Wrap (Sep 18).pdf",
                    "mime":"application/pdf",
                    "url":"https://cms-resources.growwmf.in/uploads/Fixed_Income_Weekly_Wrap_Sep_18_ec9832772c.pdf",
                }}},
            },
        },
        {
            "id":2,
            "attributes":{
                "heading":"Daily Market Pulse",
                "subheading":"Overview of key index movements and macroeconomic indicators.",
                "date":"2026-09-21",
                "report_type":"Daily Market Pulse",
                "file":{"data":{"attributes":{
                    "name":"daily_report (4).pdf",
                    "mime":"application/pdf",
                    "url":upgrade.GROWW_DAILY,
                }}},
            },
        },
        {
            "id":3,
            "attributes":{
                "heading":"Weekly Market Pulse",
                "subheading":"Weekly overview of key index movements and macroeconomic indicators.",
                "date":"2026-09-19",
                "report_type":"Weekly Market Pulse",
                "file":{"data":{"attributes":{
                    "name":"weekly_report (8).pdf",
                    "mime":"application/pdf",
                    "url":"https://cms-resources.growwmf.in/uploads/weekly_report_8_6345528cb0.pdf",
                }}},
            },
        },
    ]
    payload={"props":{"pageProps":{"data":data}},"page":"/distributor/knowledge-hub/publications"}
    return ("<html><head><title>Publications - Groww mutual fund</title></head>"
            "<body><h1>Reports & newsletters</h1>"
            f"<script id='__NEXT_DATA__' type='application/json'>{json.dumps(payload)}</script>"
            "</body></html>").encode()


def hsbc_listing():
    return f"""<html><body>
      <a href="{upgrade.HSBC_CURRENT}">RBI Monetary Policy Review - August 2026</a>
      <a href="https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-june-2026">RBI Monetary Policy Review - June 2026</a>
      <a href="https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/compelling-valuations-emerge-after-recent-market-corrections">Compelling valuations emerge after recent market corrections</a>
      <a href="https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights">See all News and insights</a>
    </body></html>""".encode()


def hsbc_article(title,day,category="Local Market Commentary"):
    return f"""<html><body><main>
      <h1>{title}</h1><p>Market subtitle</p><p>{day}</p>
      <a>{category}</a><p>Commentary body with older data date 05 August 2025.</p>
    </main></body></html>""".encode()


class GrowwHsbcCommunicationTests(unittest.TestCase):
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
                    (9301,"Groww Direct Growth","Groww Small Cap Fund",
                     "Groww Mutual Fund","Direct","Growth","test"),
                    (9302,"HSBC Direct Growth","HSBC Small Cap Fund",
                     "HSBC Mutual Fund","Direct","Growth","test"),
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

    def test_sources_and_groww_asset_host_are_registered(self):
        self.assertIsNotNone(self.source("Groww",groww.LISTING))
        self.assertIsNotNone(self.source("HSBC",hsbc.LISTING))
        self.assertTrue(disclosures.official_publication_url(
            upgrade.GROWW_DAILY,"Groww"))
        self.assertFalse(disclosures.official_publication_url(
            upgrade.GROWW_DAILY,"HSBC"))

    def test_groww_structured_payload_binds_title_date_and_exact_pdf(self):
        rows=groww.parse(groww_page())
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["title"],"Daily Market Pulse")
        self.assertEqual(rows[0]["published_at"],"2026-09-21")
        self.assertEqual(rows[0]["url"],upgrade.GROWW_DAILY)

        bad=groww_page().replace(b"cms-resources.growwmf.in",b"example.com",1)
        with self.assertRaisesRegex(ValueError,"unexpected file identity"):
            groww.parse(bad)

    def test_groww_ingest_archives_all_current_reports(self):
        listing=groww_page()
        pdf=b"%PDF-1.4 Groww market intelligence"
        calls=[]
        def fake_fetch(url,**kwargs):
            calls.append(url)
            if url==groww.LISTING:
                return self.archived(listing,"text/html")
            if url.startswith("https://cms-resources.growwmf.in/uploads/"):
                return self.archived(pdf,"application/pdf")
            raise AssertionError(url)

        with patch("tracker.groww_communications.providers.can_crawl",return_value=None):
            result=groww.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],3)
        self.assertEqual(result["errors"],[])
        row=db.one("""SELECT kind,published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (groww.FAMILY,upgrade.GROWW_DAILY))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-09-21")
        self.assertEqual(row["versions"],1)

    def test_hsbc_article_date_is_bound_to_heading_region_and_category(self):
        row=hsbc.parse_article(
            hsbc_article("RBI Monetary Policy Review - August 2026","11 August 2026"),
            upgrade.HSBC_CURRENT,
            "RBI Monetary Policy Review - August 2026")
        self.assertEqual(row["published_at"],"2026-08-11")
        self.assertEqual(row["title"],"RBI Monetary Policy Review - August 2026")

        self.assertIsNone(hsbc.parse_article(
            hsbc_article("A blog","11 August 2026","Blog"),
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/a-blog",
            "A blog"))

    def test_hsbc_ingest_retains_only_valid_local_market_commentary(self):
        listing=hsbc_listing()
        current=hsbc_article("RBI Monetary Policy Review - August 2026","11 August 2026")
        june=hsbc_article("RBI Monetary Policy Review - June 2026","10 June 2026")
        blog=hsbc_article("Compelling valuations emerge after recent market corrections",
                          "02 April 2026","Blog")
        mapping={
            hsbc.LISTING:(listing,"text/html"),
            upgrade.HSBC_CURRENT:(current,"text/html"),
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-june-2026":(june,"text/html"),
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/compelling-valuations-emerge-after-recent-market-corrections":(blog,"text/html"),
        }
        def fake_fetch(url,**kwargs):
            body,typ=mapping[url]
            if kwargs.get("archive",True):
                return self.archived(body,typ)
            return body,None,typ

        with patch("tracker.hsbc_communications.providers.can_crawl",return_value=None):
            result=hsbc.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],2)
        self.assertEqual(result["errors"],[])
        current_row=db.one("""SELECT kind,published_at,COUNT(v.id) versions
                              FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                              WHERE d.family=? AND d.url=? GROUP BY d.id""",
                           (hsbc.FAMILY,upgrade.HSBC_CURRENT))
        self.assertEqual(current_row["kind"],"market view")
        self.assertEqual(current_row["published_at"],"2026-08-11")
        self.assertEqual(current_row["versions"],1)

    def test_disclosures_routes_dedicated_sources_to_special_collectors(self):
        with patch("tracker.groww_communications.ingest",
                   return_value={"detail":"groww detail"}) as gi:
            self.assertEqual(disclosures.ingest_source(
                self.source("Groww",groww.LISTING)),"groww detail")
            gi.assert_called_once_with()
        with patch("tracker.hsbc_communications.ingest",
                   return_value={"detail":"hsbc detail"}) as hi:
            self.assertEqual(disclosures.ingest_source(
                self.source("HSBC",hsbc.LISTING)),"hsbc detail")
            hi.assert_called_once_with()

    def test_publication_audit_recognizes_both_registered_sources(self):
        audit=publication_report()
        rows={r["family"]:r for r in audit["funds"]}
        self.assertEqual(len(rows[groww.FAMILY]["registered_communication_sources"]),1)
        self.assertEqual(len(rows[hsbc.FAMILY]["registered_communication_sources"]),1)

    def test_recovery_gate_is_idempotent_and_requires_current_evidence(self):
        def store(family,title,url,day):
            digest=db.archive((family+url).encode(),"text/html")
            did=providers.save_document(
                family,title,url,"market view","AMC",published=day,origin="AMC")
            providers.doc_version(did,digest)

        def source_doc(family,title,url):
            digest=db.archive((family+url).encode(),"text/html")
            did=providers.save_document(
                family,title,url,"source page","AMC",origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==groww.LISTING:
                source_doc(groww.FAMILY,groww.SOURCE_TITLE,url)
                store(groww.FAMILY,"Daily Market Pulse",upgrade.GROWW_DAILY,"2026-09-21")
                store(groww.FAMILY,"Weekly Market Pulse",
                      "https://cms-resources.growwmf.in/uploads/weekly.pdf","2026-09-19")
                store(groww.FAMILY,"Fixed Income Weekly Wrap Up",
                      "https://cms-resources.growwmf.in/uploads/fixed.pdf","2026-09-18")
            elif url==hsbc.LISTING:
                source_doc(hsbc.FAMILY,hsbc.SOURCE_TITLE,url)
                for i in range(8):
                    target=(upgrade.HSBC_CURRENT if i==0 else
                            f"https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/test-{i}")
                    day="2026-08-11" if i==0 else "2026-06-10"
                    store(hsbc.FAMILY,
                          "RBI Monetary Policy Review - August 2026" if i==0 else f"Market commentary {i}",
                          target,day)
            else:
                raise AssertionError(url)
            return "communication recovery; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,2)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
