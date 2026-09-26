"""Union Mutual Fund communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures
from tracker import union_communications as comm

def listing():
    return b"""<html><body><h1>Research Notes</h1><div>Fund Manager's Desk</div>
      <a href="/docs/default-source/knowledge-hub/research-notes/state-of-the-market-outlook-september-2026.pdf">State of the Market & Outlook - September 2026</a>
      <a href="/docs/default-source/knowledge-hub/research-notes/cio-note.pdf">From the CIO's Desk - When Unknown Unknowns Dominate Investing Through</a>
      <a href="/docs/default-source/knowledge-hub/research-notes/product.pdf">Union MF PF Presentation</a>
    </body></html>"""

class UnionCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as c:
            c.execute("""INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                         VALUES(?,?,?,?,?,?,?)""",
                      (8701,"Union Direct Growth",comm.FAMILY,"Union Mutual Fund","Direct","Growth","test"))
        disclosures.seed_sources()
    def tearDown(self):
        self.p.stop();self.tmp.cleanup()
    @staticmethod
    def archived(body,typ):return body,db.archive(body,typ),typ
    def source(self):
        return db.one("""SELECT * FROM source_pages WHERE lower(amc_match)=lower(?) AND url=?""",
                      ("Union",comm.LISTING))
    def test_filters_research_notes(self):
        rows=comm.candidates(listing())
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r["published_at"] is None for r in rows))
    def test_archives_validated_pdfs(self):
        def fake_fetch(url,**kwargs):
            if url==comm.LISTING:return self.archived(listing(),"text/html")
            return self.archived(b"%PDF-1.7 Union note","application/pdf")
        with patch("tracker.union_communications.providers.can_crawl",return_value=None):
            result=comm.ingest(fetch_fn=fake_fetch)
        self.assertEqual(result["retained"],2)
    def test_routing(self):
        with patch("tracker.union_communications.ingest",return_value={"detail":"union detail"}) as ingest:
            self.assertEqual(disclosures.ingest_source(self.source()),"union detail")
            ingest.assert_called_once_with()

if __name__=="__main__":unittest.main()
