"""Bounded repair of retained unarchived AMC communication originals."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,providers
from scripts import repair_unarchived_communications as repair


class CommunicationArchiveRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (8501,"LIC Direct",repair.FAMILIES[0][0],"LIC Mutual Fund","Direct","Growth","test"),
                    (8502,"Nippon Direct",repair.FAMILIES[1][0],"Nippon India Mutual Fund","Direct","Growth","test"),
                    (8503,"Samco Direct",repair.FAMILIES[2][0],"Samco Mutual Fund","Direct","Growth","test"),
                ],
            )
        self.urls={
            repair.FAMILIES[0][0]:"https://www.licmf.com/insights/lic-market-outlook.pdf",
            repair.FAMILIES[1][0]:"https://mf.nipponindiaim.com/LearnAndInvest/MarketOutlook/test.html",
            repair.FAMILIES[2][0]:"https://media1.samco.in/samco-market-view.pdf",
        }
        self.ids={}
        for family,url in self.urls.items():
            self.ids[family]=providers.save_document(
                family,"Market Outlook",url,"market view","AMC",origin="AMC")

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    @staticmethod
    def archived(body,typ):
        return body,db.archive(body,typ),typ

    def test_missing_returns_only_zero_version_communications(self):
        rows=repair.missing(repair.FAMILIES[0][0])
        self.assertEqual([r["id"] for r in rows],[self.ids[repair.FAMILIES[0][0]]])
        digest=db.archive(b"%PDF-1.7 existing","application/pdf")
        providers.doc_version(self.ids[repair.FAMILIES[0][0]],digest)
        self.assertEqual(repair.missing(repair.FAMILIES[0][0]),[])

    def test_repair_archives_exact_retained_first_party_urls(self):
        def fake_fetch(url,**kwargs):
            if url.endswith(".html"):
                return self.archived(b"<html><body>Nippon market outlook</body></html>","text/html")
            return self.archived(b"%PDF-1.7 market view","application/pdf")
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=True):
            result=repair.repair(fetch_fn=fake_fetch,can_crawl_fn=lambda u:None)
        self.assertEqual(result["repaired"],3)
        for family,_ in repair.FAMILIES:
            self.assertEqual(repair.missing(family),[])

    def test_canonical_fetch_url_encodes_spaces_without_changing_identity(self):
        original="https://www.licmf.com/assets/pdfs/LICMF Monthly Market Outlook March 2025.pdf"
        canonical=repair.canonical_fetch_url(original)
        self.assertEqual(
            canonical,
            "https://www.licmf.com/assets/pdfs/LICMF%20Monthly%20Market%20Outlook%20March%202025.pdf",
        )

    def test_repair_fetches_canonical_url_but_keeps_original_document_identity(self):
        family=repair.FAMILIES[0][0]
        original=self.urls[family]
        with db.connect() as c:
            c.execute("UPDATE documents SET url=? WHERE id=?",
                      ("https://www.licmf.com/assets/pdfs/LICMF Monthly Market Outlook March 2025.pdf",
                       self.ids[family]))
        requested=[]
        def fake_fetch(url,**kwargs):
            requested.append(url)
            return b"%PDF-1.7 LIC outlook",None,"application/pdf"
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=True):
            result=repair.repair(fetch_fn=fake_fetch,can_crawl_fn=lambda u:None)
        self.assertTrue(any("%20" in u for u in requested))
        row=db.one("SELECT url FROM documents WHERE id=?",(self.ids[family],))
        self.assertIn("LICMF Monthly Market Outlook March 2025.pdf",row["url"])
        lic=result["families"][family]
        self.assertEqual(lic["repaired"],1)
        self.assertIn("%20",lic["repaired_rows"][0]["request_url"])

    def test_lic_retries_invalid_asset_with_first_party_referer(self):
        family=repair.LIC_FAMILY
        with db.connect() as c:
            c.execute("UPDATE documents SET url=? WHERE id=?",
                      ("https://www.licmf.com/assets/pdfs/LICMF Monthly Market Outlook March 2025.pdf",
                       self.ids[family]))
        calls=[]
        def fake_fetch(url,**kwargs):
            calls.append((url,kwargs.get("headers")))
            if kwargs.get("headers"):
                return b"%PDF-1.7 LIC outlook",None,"application/pdf"
            return b"<html><body>asset shell</body></html>",None,"text/html"
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=True):
            result=repair.repair(fetch_fn=fake_fetch,can_crawl_fn=lambda u:None)
        lic=result["families"][family]
        self.assertEqual(lic["repaired"],1)
        self.assertEqual(calls[1][1],{"Referer":repair.LIC_REFERER})
        self.assertTrue(lic["repaired_rows"][0]["used_referer"])

    def test_failed_lic_attempts_persist_response_diagnostics(self):
        family=repair.LIC_FAMILY
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=True):
            result=repair.repair(
                fetch_fn=lambda *a,**k:(b"<html><body>Not a PDF</body></html>",None,"text/html"),
                can_crawl_fn=lambda u:None,
            )
        lic=result["families"][family]
        row=lic["failed_rows"][0]
        self.assertEqual(len(row["attempts"]),2)
        self.assertEqual(row["attempts"][0]["media_type"],"text/html")
        self.assertGreater(row["attempts"][0]["bytes"],0)
        self.assertIn("Not a PDF",row["attempts"][0]["text_prefix"])

    def test_invalid_response_does_not_attach_document_version(self):
        family=repair.FAMILIES[0][0]
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=True):
            result=repair.repair(
                fetch_fn=lambda *a,**k:self.archived(b"<html>error</html>","text/html"),
                can_crawl_fn=lambda u:None,
            )
        self.assertGreaterEqual(result["failed"],1)
        self.assertEqual(len(repair.missing(family)),1)

    def test_report_persists_exact_failure_details(self):
        result={
            "families":{
                "LIC Mf Small Cap Fund":{
                    "before":1,"repaired":0,"failed":1,"skipped":0,"remaining":1,
                    "repaired_rows":[],
                    "failed_rows":[{"url":"https://www.licmf.com/old.pdf","error":"404 Not Found"}],
                    "skipped_rows":[],
                }
            },
            "repaired":0,"failed":1,"skipped":0,
        }
        target=Path(self.tmp.name)/"repair.json"
        repair.write_report(result,target)
        import json
        saved=json.loads(target.read_text())
        self.assertEqual(saved["families"]["LIC Mf Small Cap Fund"]["failed_rows"][0]["error"],"404 Not Found")
        self.assertEqual(saved["mode"],"exact_retained_urls_best_effort")
        self.assertIn("prepared_at",saved)

    def test_non_official_url_is_skipped_without_fetch(self):
        family=repair.FAMILIES[0][0]
        with patch("scripts.repair_unarchived_communications.official_publication_url",return_value=False), \
             patch("scripts.repair_unarchived_communications.providers.fetch") as fetch:
            result=repair.repair(can_crawl_fn=lambda u:None)
        self.assertGreaterEqual(result["skipped"],1)
        fetch.assert_not_called()
        self.assertEqual(len(repair.missing(family)),1)


if __name__=="__main__":
    unittest.main()
