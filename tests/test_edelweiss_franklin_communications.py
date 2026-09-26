"""Edelweiss/Franklin AMC communication source recovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from tracker import franklin_communications as franklin
from scripts import refresh_edelweiss_franklin_communications as upgrade


def api_payload():
    def hit(title,day,slug,asset,document_type="INDArticleDetails"):
        return {"_source":{
            "pageType":"latest-commentaries",
            "documentType":document_type,
            "articleType":"Article",
            "pageTitle":title,
            "title":title,
            "referenceDate":day,
            "publishDate":day+"T00:00:00.000+02:00",
            "pdfURL":asset,
            "documentPath":(
                "/content/documents/global/india/sites/india/site-pages/"
                "knowledge-centre/quick-learn/latest-commentaries/article/"+slug),
        }}
    return {"results":{"response":{"hits":{"hits":[
        hit("Weekly Market Review","2026-09-18","weekly-market-review",
            "https://franklintempletonprod.widen.net/s/fj2fm6jtmf/weekly-market-review-2-en-in"),
        hit("Monthly Equity Outlook","2026-08-06","monthly-equity-outlook",
            "https://franklintempletonprod.widen.net/s/rrxmvxwmh9/ft-monthly-equity-market-outlook"),
        hit("RBI Monetary Policy Review","2026-08-05","rbi-monetary-policy-review",
            "https://franklintempletonprod.widen.net/s/pxsxvvbvmk/rbi-monetary-policy-review-en-in"),
        hit("Franklin Templeton - Union Budget Outlook - 2026-27","2026-02-01",
            "franklin-templeton---union-budget-outlook---2026-27",
            "https://franklintempletonprod.widen.net/s/7wdksbwsvk/franklin-templeton_union-budget-outlook_2026-27_web"),
        hit("India Annual Outlook 2026 - From Economic Resilience to Market Recovery",
            "2025-12-18","india-annual-outlook-2026",
            "https://franklintempletonprod.widen.net/s/vbm9sfgghw/franklin-templeton_india-annual-outlook-2026"),
        hit("India Market Outlook","2025-10-14","monthly-india-market-outlook",
            "https://franklintempletonprod.widen.net/s/c7zwblsvpg/india_market_outlook"),
        hit("Financialisation of Savings in India: From Safety to Scale","2026-09-02",
            "financialisation-of-savings-in-india-from-safety-to-scale",
            "https://franklintempletonprod.widen.net/s/bxkjrbktvv/report"),
    ]}}}}


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

    def test_sources_keep_franklin_listing_but_not_blocked_widen_viewer(self):
        rows=json.loads((db.ROOT/"tracker"/"sources.json").read_text())
        pairs={(r[0],r[1],r[2]) for r in rows}
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_INSIGHTS,"Fund & Market Insights"),pairs)
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_CURVE,"Debt Market Update - Curve"),pairs)
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_FACTOR,"Factor Investing Outlook 2026"),pairs)
        self.assertIn(("Edelweiss",upgrade.EDELWEISS_FACTOR_PDF,"Factor Investing Outlook 2026"),pairs)
        self.assertIn(("Franklin",upgrade.FRANKLIN_LATEST,"Latest Commentaries / Market Insights"),pairs)
        self.assertFalse(any(r[0]=="Franklin" and "widen.net" in r[1] for r in rows))
        self.assertFalse(disclosures.official_publication_url(
            "https://franklintempletonprod.widen.net/s/x/current","Franklin"))
        self.assertFalse(disclosures.official_publication_url(
            "https://franklintempletonprod.widen.net/s/x/current","Edelweiss"))
        parsed=franklin.parse(json.dumps(api_payload()).encode())
        self.assertTrue(all(
            not row["asset_url"] or
            row["asset_url"].startswith("https://franklintempletonprod.widen.net/")
            for row in parsed
        ))

    def test_franklin_api_parser_keeps_only_clear_market_commentaries(self):
        rows=franklin.parse(json.dumps(api_payload()).encode())
        titles=[r["title"] for r in rows]
        self.assertEqual(len(rows),6)
        self.assertIn("Monthly Equity Outlook",titles)
        self.assertIn("Weekly Market Review",titles)
        self.assertIn("RBI Monetary Policy Review",titles)
        self.assertNotIn("Financialisation of Savings in India: From Safety to Scale",titles)
        monthly=next(r for r in rows if r["title"]=="Monthly Equity Outlook")
        self.assertEqual(monthly["published_at"],"2026-08-06")
        self.assertEqual(monthly["url"],upgrade.FRANKLIN_MONTHLY)
        self.assertEqual(monthly["asset_url"],
                         "https://franklintempletonprod.widen.net/s/rrxmvxwmh9/ft-monthly-equity-market-outlook")

    def test_franklin_api_ingest_archives_source_snapshot_not_widen_originals(self):
        raw=json.dumps(api_payload()).encode()
        calls=[]
        def fake_fetch(url,**kwargs):
            calls.append((url,kwargs))
            digest=db.archive(raw,"application/json")
            return raw,digest,"application/json"

        with patch("tracker.franklin_communications.providers.can_crawl",return_value=None):
            result=franklin.ingest(fetch_fn=fake_fetch)

        self.assertEqual(result["retained"],6)
        self.assertEqual(result["unarchived_originals"],6)
        self.assertEqual(calls[0][0],franklin.ENDPOINT)
        self.assertEqual(calls[0][1]["form"]["env"],"prod")
        self.assertEqual(calls[0][1]["form"]["collection"],"pages")
        self.assertIn("application/x-www-form-urlencoded",
                      calls[0][1]["headers"]["Content-Type"])

        source=db.one("""SELECT d.kind,COUNT(v.id) versions
                         FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                         WHERE d.family=? AND d.url=? GROUP BY d.id""",
                      (franklin.FAMILY,franklin.ENDPOINT))
        self.assertEqual(source["kind"],"source page")
        self.assertEqual(source["versions"],1)

        monthly=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                          FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                          WHERE d.family=? AND d.url=? GROUP BY d.id""",
                       (franklin.FAMILY,upgrade.FRANKLIN_MONTHLY))
        self.assertEqual(monthly["kind"],"market view")
        self.assertEqual(monthly["published_at"],"2026-08-06")
        self.assertEqual(monthly["versions"],0)

    def test_listing_source_delegates_to_franklin_api_collector(self):
        row=self.source("Franklin",upgrade.FRANKLIN_LATEST)
        with patch("tracker.franklin_communications.ingest",
                   return_value={"detail":"6 Franklin records; 0 download/parser gaps"}) as ingest:
            result=disclosures.ingest_source(row)
        self.assertEqual(result,"6 Franklin records; 0 download/parser gaps")
        ingest.assert_called_once_with()

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

    def test_exact_edelweiss_factor_pdf_is_valid_direct_market_view_source(self):
        pdf=b"%PDF-1.4 exact first-party factor outlook"
        with patch("tracker.disclosures.can_crawl",return_value=None), \
             patch("tracker.disclosures.fetch",
                   return_value=self.archived(pdf,"application/pdf")), \
             patch("tracker.amc_reports.extract",return_value=0):
            result=disclosures.ingest_source(
                self.source("Edelweiss",upgrade.EDELWEISS_FACTOR_PDF))
        self.assertTrue(result.endswith("0 download/parser gaps"),result)
        row=db.one("""SELECT d.kind,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family='Edelweiss Small Cap Fund' AND d.url=?
                      GROUP BY d.id""",(upgrade.EDELWEISS_FACTOR_PDF,))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["versions"],1)

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

    def test_recovery_gate_accepts_api_metadata_and_disables_legacy_widen_source(self):
        with db.connect() as c:
            c.execute("""INSERT OR IGNORE INTO source_pages(amc_match,url,label,enabled,status)
                         VALUES('Franklin',?,'Legacy Widen',1,'Pending')""",
                      (upgrade.LEGACY_WIDEN,))

        def store(family,title,url,kind,published=None,version=True):
            did=providers.save_document(
                family,title,url,kind,"AMC",published=published,origin="AMC")
            if version:
                digest=db.archive((family+url).encode(),"text/html")
                providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==upgrade.EDELWEISS_FACTOR_PDF:
                store("Edelweiss Small Cap Fund","Factor Investing Outlook 2026",
                      url,"market view")
            elif url==upgrade.FRANKLIN_LATEST:
                store("Franklin India Small Cap Fund",franklin.SOURCE_TITLE,
                      franklin.ENDPOINT,"source page")
                for i,(title,day,slug) in enumerate([
                    ("Weekly Market Review","2026-09-18","weekly-market-review"),
                    ("Monthly Equity Outlook","2026-08-06","monthly-equity-outlook"),
                    ("RBI Monetary Policy Review","2026-08-05","rbi-monetary-policy-review"),
                    ("Union Budget Outlook","2026-02-01","budget-outlook"),
                    ("India Annual Outlook 2026","2025-12-18","annual-outlook"),
                    ("India Market Outlook","2025-10-14","india-market-outlook"),
                ]):
                    store("Franklin India Small Cap Fund",title,
                          "https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries/article/"+slug,
                          "market view",day,version=False)
            else:
                raise AssertionError(url)
            return "1 communication source retained; 0 download/parser gaps"

        with patch("tracker.disclosures.ingest_source",side_effect=fake_ingest) as ingest:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(ingest.call_count,2)

        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))
        legacy=self.source("Franklin",upgrade.LEGACY_WIDEN)
        self.assertEqual(legacy["enabled"],0)
        self.assertEqual(legacy["status"],"Excluded")


if __name__=="__main__":
    unittest.main()
