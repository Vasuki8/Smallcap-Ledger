"""UTI Mutual Fund first-party communication recovery checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures
from tracker import uti_communications as comm
from tracker.publication_coverage import report as publication_report


def cms_payload(category="Market Insights"):
    return json.dumps([
        {
            "nid":"91239",
            "title":"Market Insight - Equity | September 2026",
            "field_knowledge_hub_category":category,
            "field_asset_type":"Investor App web, Buddy, App, Investor Web",
            "field_date_of_publication":"2026-09-10",
            "pdf":"https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/market_insight_equity_sep_2026_fp_revised.pdf?VersionId=test",
            "s3pdf":"",
            "view_node":"/market-insight-equity-september-2026",
        },
        {
            "nid":"999",
            "title":"Generic education",
            "field_knowledge_hub_category":"Articles",
            "field_date_of_publication":"2026-09-09",
            "pdf":"https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/article.pdf",
        },
    ]).encode()


def cio_payload():
    return json.dumps([
        {
            "nid":"91014",
            "title":"Two Scoreboards, One Playbook",
            "field_knowledge_hub_category":"From the CIOs Desk",
            "field_asset_type":"Investor App web, Buddy, App",
            "field_kc_posted_date":"2026-09-03",
            "pdf":"https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/from_the_leadership_desk_september_2026_revised.pdf?VersionId=test",
            "view_node":"/two-scoreboards-one-playbook",
        }
    ]).encode()


class UtiCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as c:
            c.execute("""INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                         VALUES(?,?,?,?,?,?,?)""",
                      (8601,"UTI Direct Growth",comm.FAMILY,
                       "UTI Mutual Fund","Direct","Growth","test"))
        disclosures.seed_sources()

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def source(self):
        return db.one("""SELECT * FROM source_pages
                         WHERE lower(amc_match)=lower(?) AND url=?""",
                      ("UTI",comm.LISTING))

    def test_source_registered_and_audit_recognizes_it(self):
        self.assertIsNotNone(self.source())
        row={x["family"]:x for x in publication_report()["funds"]}[comm.FAMILY]
        self.assertEqual(len(row["registered_communication_sources"]),1)

    def test_cms_rows_keep_only_reviewed_category_and_official_cdn_pdf(self):
        rows=comm.cms_rows(cms_payload(),"Market Insights")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["title"],"Market Insight - Equity | September 2026")
        self.assertEqual(rows[0]["published_at"],"2026-09-10")
        self.assertEqual(rows[0]["category"],"Market Insights")
        bad=json.dumps([{
            "title":"Market Insight",
            "field_knowledge_hub_category":"Market Insights",
            "pdf":"https://example.com/market.pdf",
        }]).encode()
        with self.assertRaises(ValueError):
            comm.cms_rows(bad,"Market Insights")

    def test_missing_explicit_date_remains_null(self):
        payload=json.dumps([{
            "title":"Market Insight - Equity | September 2026",
            "field_knowledge_hub_category":"Market Insights",
            "pdf":"https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/market.pdf",
        }]).encode()
        self.assertIsNone(comm.cms_rows(payload,"Market Insights")[0]["published_at"])

    def test_ingest_archives_market_and_cio_pdfs(self):
        def fake_fetch(url,**kwargs):
            if url==comm.CMS_ENDPOINTS[0][0]:
                return cms_payload(),None,"application/json"
            if url==comm.CMS_ENDPOINTS[1][0]:
                return cio_payload(),None,"application/json"
            return b"%PDF-1.7 UTI first party CMS asset",None,"application/pdf"
        with patch("tracker.uti_communications.providers.can_crawl",return_value=None):
            result=comm.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],2)
        rows=db.rows("""SELECT d.title,d.kind,d.published_at,COUNT(v.id) versions
                        FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                        WHERE d.family=? AND d.kind='market view'
                        GROUP BY d.id ORDER BY d.title""",(comm.FAMILY,))
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r["kind"]=="market view" and r["versions"]==1 for r in rows))
        self.assertEqual({r["published_at"] for r in rows},{"2026-09-03","2026-09-10"})

    def test_disclosures_routes_source(self):
        with patch("tracker.uti_communications.ingest",
                   return_value={"detail":"uti detail"}) as ingest:
            self.assertEqual(disclosures.ingest_source(self.source()),"uti detail")
            ingest.assert_called_once_with()


if __name__=="__main__":
    unittest.main()
