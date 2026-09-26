"""UTI Mutual Fund first-party communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures
from tracker import uti_communications as comm
from tracker.publication_coverage import report as publication_report


def learn_page():
    return b"""<html><body><h1>Knowledge Centre</h1>
      <div>From The Fund House</div>
      <a href="/leadership-desk">Leadership Desk</a>
      <a href="/investment-insights">Investment Insights</a>
      <a href="/market-insights">Market Insights</a>
    </body></html>"""


def category_page():
    return b"""<html><body>
      <a href="/leadership-desk/seeking-opportunity-uncrowded-market-segments">
        Seeking Opportunity in Uncrowded Market Segments
      </a>
      <a href="https://example.com/news">External News</a>
    </body></html>"""


def article(title="Seeking Opportunity in Uncrowded Market Segments"):
    return f"""<html><head>
      <meta property="article:published_time" content="2026-06-12T08:00:00+05:30">
      </head><body><div>UTI Mutual Fund</div><h1>{title}</h1>
      <p>Fund House investment perspective on markets and portfolio construction.</p>
    </body></html>""".encode()


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

    @staticmethod
    def archived(body,typ):
        return body,db.archive(body,typ),typ

    def source(self):
        return db.one("""SELECT * FROM source_pages
                         WHERE lower(amc_match)=lower(?) AND url=?""",
                      ("UTI",comm.LISTING))

    def test_source_registered_and_audit_recognizes_it(self):
        self.assertIsNotNone(self.source())
        audit=publication_report()
        row={x["family"]:x for x in audit["funds"]}[comm.FAMILY]
        self.assertEqual(len(row["registered_communication_sources"]),1)

    def test_discovery_keeps_only_first_party_fund_house_articles(self):
        def fake_fetch(url,**kwargs):
            if url.rstrip("/") in (
                "https://www.utimf.com/leadership-desk",
                "https://www.utimf.com/investment-insights",
                "https://www.utimf.com/market-insights",
            ):
                return category_page(),None,"text/html"
            raise AssertionError(url)
        with patch("tracker.uti_communications.providers.can_crawl",return_value=None):
            rows=comm.discover(learn_page(),fetch_fn=fake_fetch)
        urls=[url for url,_ in rows]
        self.assertIn(
            "https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments",
            urls)
        self.assertFalse(any("example.com" in x for x in urls))

    def test_article_keeps_explicit_source_date_only(self):
        row=comm.parse_article(
            article(),
            "https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments",
            "fallback",
        )
        self.assertEqual(row["published_at"],"2026-06-12")
        with self.assertRaises(ValueError):
            comm.parse_article(article(),"https://example.com/article","bad")

    def test_ingest_archives_validated_articles(self):
        def fake_fetch(url,**kwargs):
            if url==comm.LISTING:
                return self.archived(learn_page(),"text/html")
            if url.rstrip("/") in (
                "https://www.utimf.com/leadership-desk",
                "https://www.utimf.com/investment-insights",
                "https://www.utimf.com/market-insights",
            ):
                return category_page(),None,"text/html"
            return self.archived(article(),"text/html")
        with patch("tracker.uti_communications.providers.can_crawl",return_value=None):
            result=comm.ingest(fetch_fn=fake_fetch)
        self.assertGreaterEqual(result["retained"],1)
        row=db.one("""SELECT d.kind,d.published_at,COUNT(v.id) versions
                      FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                      WHERE d.family=? AND d.url=? GROUP BY d.id""",
                   (comm.FAMILY,
                    "https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments"))
        self.assertEqual(row["kind"],"market view")
        self.assertEqual(row["published_at"],"2026-06-12")
        self.assertEqual(row["versions"],1)

    def test_disclosures_routes_source(self):
        with patch("tracker.uti_communications.ingest",
                   return_value={"detail":"uti detail"}) as ingest:
            self.assertEqual(disclosures.ingest_source(self.source()),"uti detail")
            ingest.assert_called_once_with()


if __name__=="__main__":
    unittest.main()
