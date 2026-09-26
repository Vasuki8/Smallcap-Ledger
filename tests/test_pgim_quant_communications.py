"""PGIM India / quant Mutual AMC communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from tracker import pgim_communications as pgim
from tracker import quant_communications as quant
from tracker.publication_coverage import report as publication_report
from scripts import refresh_pgim_quant_communications as upgrade


def pgim_listing():
    return f"""<html><body>
      <a href="{upgrade.PGIM_ANCHOR}">Money for a Life in Motion</a>
      <a href="https://www.pgimindia.com/mutual-funds/domestic-insights/CEO-Letters/article/Navigating-Geopolitical-Uncertainty-Staying-the-Course">Navigating Geopolitical Uncertainty, Staying the Course</a>
      <a href="https://www.pgimindia.com/mutual-funds/domestic-insights/Outlooks-Economy/article/India-Market-Outlook">India Market Outlook</a>
      <a href="https://www.pgimindia.com/mutual-funds/forms-and-product-updates/Fund-Factsheet">Factsheets</a>
    </body></html>""".encode()


def pgim_article(title):
    return f"""<html><body><h1>{title}</h1>
      <p>Jun 2026 - 3 mins read</p>
      <p>PGIM India Mutual Fund</p>
    </body></html>""".encode()


def quant_listing():
    return b"""<html><body><table>
      <tr><td>Predictive Analytics_June 2023_Volume 3_Issue 2</td>
          <td><a href="/Admin/Pdf/Predictive Analytics_June 2023_Volume 3_Issue 2.pdf">a</a></td></tr>
      <tr><td>Predictive Analytics February 2023 Volume 3 Issue 1</td>
          <td><a href="/Admin/Pdf/Predictive_Analytics_February_2023_Volume_3_Issue_1.pdf">a</a></td></tr>
      <tr><td>Predictive Analytics June 2022 Volume 2 Issue 1</td>
          <td><a href="/Admin/Pdf/Predictive_Analytics_June_2022_Volume_2_Issue_1.pdf">a</a></td></tr>
      <tr><td>Returns of schemes by same Fund Managers</td>
          <td><a href="/Admin/Pdf/Explanation-for-Returns_2020-21.pdf">a</a></td></tr>
      <tr><td>Predictive Analytics September 2021 Volume 1 Issue 2</td>
          <td><a href="/Admin/Pdf/Predictive_Analytics_September_2021_Volume_1_Issue_2.pdf">a</a></td></tr>
      <tr><td>VLRT Outlook (July-Aug 2021)</td>
          <td><a href="/Admin/Pdf/VLRT-OUTLOOK-JULY-AUGUST2021.pdf">a</a></td></tr>
      <tr><td>VLRT Outlook (May-June 2021)</td>
          <td><a href="/Admin/Pdf/VLRT_Outlook_May_June_2021.pdf">a</a></td></tr>
      <tr><td>Predictive Analytics February 2021 Volume 1 Issue no.1</td>
          <td><a href="/Admin/Pdf/Predictive_Analytics_February_2021_Volume_1_Issue no_1.pdf">a</a></td></tr>
    </table></body></html>"""


class PgimQuantCommunicationTests(unittest.TestCase):
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
                    (9001,"PGIM Direct Growth",pgim.FAMILY,
                     "PGIM India Mutual Fund","Direct","Growth","test"),
                    (9002,"quant Direct Growth",quant.FAMILY,
                     "quant Mutual Fund","Direct","Growth","test"),
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
        self.assertIsNotNone(self.source("PGIM",pgim.LISTING))
        self.assertIsNotNone(self.source("quant Mutual",quant.LISTING))
        audit=publication_report()
        rows={r["family"]:r for r in audit["funds"]}
        self.assertEqual(len(rows[pgim.FAMILY]["registered_communication_sources"]),1)
        self.assertEqual(len(rows[quant.FAMILY]["registered_communication_sources"]),1)

    def test_pgim_homepage_only_accepts_domestic_insight_articles(self):
        rows=pgim.candidates(pgim_listing())
        urls=[url for url,_ in rows]
        self.assertEqual(len(urls),3)
        self.assertIn(upgrade.PGIM_ANCHOR,urls)
        self.assertFalse(any("factsheet" in url.lower() for url in urls))

    def test_pgim_article_keeps_month_only_date_as_missing(self):
        row=pgim.parse_article(
            pgim_article("Money for a Life in Motion"),
            upgrade.PGIM_ANCHOR,
            "Money for a Life in Motion",
        )
        self.assertEqual(row["title"],"Money for a Life in Motion")
        self.assertIsNone(row["published_at"])

    def test_pgim_ingest_archives_validated_articles(self):
        listing=pgim_listing()
        def fake_fetch(url,**kwargs):
            if url==pgim.LISTING:return self.archived(listing,"text/html")
            return self.archived(pgim_article(url.rsplit("/",1)[-1].replace("-"," ")),"text/html")
        with patch("tracker.pgim_communications.providers.can_crawl",return_value=None):
            result=pgim.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],3)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (pgim.FAMILY,upgrade.PGIM_ANCHOR))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_quant_archive_selects_only_outlook_research_pdfs(self):
        rows=quant.candidates(quant_listing())
        self.assertEqual(len(rows),7)
        urls=[r["url"] for r in rows]
        self.assertIn(upgrade.QUANT_ANCHOR,urls)
        self.assertFalse(any("Explanation-for-Returns" in url for url in urls))
        self.assertTrue(all("%20" in r["url"] or "Predictive_" in r["url"] or "VLRT" in r["url"]
                            for r in rows))

    def test_quant_ingest_archives_all_eligible_pdfs_without_inferred_dates(self):
        listing=quant_listing();pdf=b"%PDF-1.4 quant outlook"
        def fake_fetch(url,**kwargs):
            if url==quant.LISTING:return self.archived(listing,"text/html")
            return self.archived(pdf,"application/pdf")
        with patch("tracker.quant_communications.providers.can_crawl",return_value=None):
            result=quant.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],7)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (quant.FAMILY,upgrade.QUANT_ANCHOR))
        self.assertEqual(row["kind"],"market view")
        self.assertIsNone(row["published_at"])
        self.assertEqual(row["versions"],1)

    def test_disclosures_routes_both_dedicated_sources(self):
        with patch("tracker.pgim_communications.ingest",
                   return_value={"detail":"pgim detail"}) as p:
            self.assertEqual(disclosures.ingest_source(
                self.source("PGIM",pgim.LISTING)),"pgim detail")
            p.assert_called_once_with()
        with patch("tracker.quant_communications.ingest",
                   return_value={"detail":"quant detail"}) as q:
            self.assertEqual(disclosures.ingest_source(
                self.source("quant Mutual",quant.LISTING)),"quant detail")
            q.assert_called_once_with()

    def test_recovery_gate_is_idempotent_and_requires_anchor_evidence(self):
        def store(family,title,url,body,kind="market view"):
            digest=db.archive(body,"application/pdf" if body.startswith(b"%PDF") else "text/html")
            did=providers.save_document(
                family,title,url,kind,"AMC",published=None,origin="AMC")
            providers.doc_version(did,digest)

        def fake_ingest(source):
            url=source["url"]
            if url==pgim.LISTING:
                store(pgim.FAMILY,pgim.SOURCE_TITLE,url,b"<html>PGIM source</html>","source page")
                for i,target in enumerate([
                    upgrade.PGIM_ANCHOR,
                    "https://www.pgimindia.com/mutual-funds/domestic-insights/CEO-Letters/article/test-two",
                    "https://www.pgimindia.com/mutual-funds/domestic-insights/Outlooks-Economy/article/test-three",
                ]):
                    store(pgim.FAMILY,f"PGIM view {i}",target,b"<html>PGIM India view</html>")
            elif url==quant.LISTING:
                store(quant.FAMILY,quant.SOURCE_TITLE,url,b"<html>quant source</html>","source page")
                candidates=[
                    upgrade.QUANT_ANCHOR,
                    "https://www.quantmutual.com/Admin/Pdf/Predictive_Analytics_February_2023_Volume_3_Issue_1.pdf",
                    "https://www.quantmutual.com/Admin/Pdf/Predictive_Analytics_June_2022_Volume_2_Issue_1.pdf",
                    "https://www.quantmutual.com/Admin/Pdf/Predictive_Analytics_September_2021_Volume_1_Issue_2.pdf",
                    "https://www.quantmutual.com/Admin/Pdf/VLRT-OUTLOOK-JULY-AUGUST2021.pdf",
                    "https://www.quantmutual.com/Admin/Pdf/VLRT_Outlook_May_June_2021.pdf",
                    "https://www.quantmutual.com/Admin/Pdf/Predictive_Analytics_February_2021_Volume_1_Issue%20no_1.pdf",
                ]
                for i,target in enumerate(candidates):
                    store(quant.FAMILY,f"quant view {i}",target,b"%PDF-1.4 quant")
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
