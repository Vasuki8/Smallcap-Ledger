"""Verified cross-scheme/directory publication ownership regressions."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["SMALLCAP_NO_SCHEDULER"]="1"

from tracker import db, providers
from tracker.app import documents
from tracker.publication_coverage import report
from tracker.publications import exclusion_reason


class CrossSchemePublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def scheme(self,code,family,amc):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (code,family+" Direct Growth",family,amc,"Direct","Growth","test"),
            )

    def old_doc(self,family,title,url):
        with db.connect() as c:
            return c.execute(
                """INSERT INTO documents(
                     family,title,kind,scope,url,first_seen,last_seen,origin)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (family,title,"market view","AMC",url,db.now(),db.now(),"AMC"),
            ).lastrowid

    def test_axis_greater_china_article_is_not_small_cap_communication(self):
        family="Axis Small Cap Fund";amc="Axis Mutual Fund";code=9902
        wrong_title="Axis Greater China Equity Fund of Fund: Making Sense..."
        wrong_url=("https://www.axismf.com/mutual-fund-knowledge-centre/articles/"
                   "everything-you-need-to-know-about-axis-greater-china-fund-of-fund")
        good_title="How Union Budget 2026 Affects Equity, Debt & Hybrid Funds"
        good_url=("https://www.axismf.com/mutual-fund-knowledge-centre/articles/"
                  "union-budget-2026-impact-on-mutual-funds")
        self.scheme(code,family,amc)
        self.old_doc(family,wrong_title,wrong_url)
        good=providers.save_document(
            family,good_title,good_url,"market view","AMC",
            published="2026-02-11",origin="AMC")
        h=db.archive(b"<html>Axis budget commentary</html>","text/html")
        providers.doc_version(good,h)

        self.assertEqual([d["url"] for d in documents(code)],[good_url])
        self.assertIn("Greater China",exclusion_reason(amc,wrong_url,wrong_title))
        with self.assertRaisesRegex(ValueError,"Greater China"):
            providers.save_document(
                family,wrong_title,wrong_url,"market view","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))

    def test_helios_other_fund_product_material_is_hidden_and_rejected(self):
        family="Helios Small Cap Fund";amc="Helios Mutual Fund";code=9903
        self.scheme(code,family,amc)
        foreign=[
            ("Helios Flexi Cap Fund","https://www.heliosmf.in/wp-content/uploads/2025/04/FLexicap-Fund-Product-Note_.pdf"),
            ("Helios Overnight Fund","https://www.heliosmf.in/wp-content/uploads/2025/04/Overnight-Fund-Product-Note.pdf"),
            ("Helios Mid Cap Fund","https://www.heliosmf.in/wp-content/uploads/2025/04/Mid-Cap-Fund-Product-Note_.pdf"),
            ("Helios Large & Mid Cap Fund","https://www.heliosmf.in/wp-content/uploads/2025/04/Large-Mid-Cap-Fund-Product-Note_.pdf"),
            ("Helios Financial Services Fund","https://www.heliosmf.in/wp-content/uploads/2025/04/Financial-Services-Fund-Product-Note.pdf"),
            ("Helios Arbitrage Fund","https://www.heliosmf.in/wp-content/uploads/2026/03/Helios-Arbitrage-Fund-NFO-Presentation.pdf"),
        ]
        own=("Helios Small Cap Fund",
             "https://www.heliosmf.in/wp-content/uploads/2025/10/Helios-Small-Cap-Fund-Product-Note.pdf")
        for title,url in foreign+[own]:
            self.old_doc(family,title,url)

        self.assertEqual([(d["title"],d["url"]) for d in documents(code)],[own])
        for title,url in foreign:
            with self.subTest(url=url):
                self.assertIn("non-Small-Cap",exclusion_reason(amc,url,title))
                with self.assertRaisesRegex(ValueError,"non-Small-Cap"):
                    providers.save_document(family,title,url,"market view","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,own[1],own[0]))

    def test_bandhan_and_hsbc_false_communication_rows_are_hidden(self):
        cases=[
            (
                "Bandhan Small Cap Fund",9904,"Bandhan Mutual Fund",
                "Next Presentation on Bandhan Nifty Midcap150 Index Fund – May’26>Partners>Fund House>Presentation",
                "https://cmsnew.bandhanmutual.com/presentation-on-bandhan-nifty-midcap150-index-fund-may26partnersfund-housepresentation/",
                "Midcap150 Index Fund",
            ),
            (
                "HSBC Small Cap Fund",9905,"HSBC Mutual Fund",
                "Performance - Equity Hybrid Debt Global Funds",
                "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources?Date=&Cap=&Doc=product-note-and-deck#&module-17=1",
                "product-note/deck directory",
            ),
        ]
        for family,code,amc,title,url,reason in cases:
            self.scheme(code,family,amc);self.old_doc(family,title,url)
            with self.subTest(family=family):
                self.assertEqual(documents(code),[])
                self.assertIn(reason,exclusion_reason(amc,url,title))
                with self.assertRaises(ValueError):
                    providers.save_document(family,title,url,"market view","AMC",origin="AMC")
                # Historical association remains auditable in storage.
                self.assertEqual(db.one("SELECT COUNT(*) n FROM documents WHERE family=?",(family,))["n"],1)

        self.assertIsNone(exclusion_reason(
            "Bandhan Mutual Fund",
            "https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-equity-september-2026/",
            "Market Outlook - Equity - September 2026"))
        self.assertIsNone(exclusion_reason(
            "HSBC Mutual Fund",
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-august-2026",
            "RBI Monetary Policy Review - August 2026"))

    def test_sundaram_corporate_presentation_is_not_small_cap_communication(self):
        family="Sundaram Small Cap Fund";amc="Sundaram Mutual Fund";code=9906
        wrong_title="Corporate Presentation"
        wrong_url="https://www.sundarammutual.com/Report/AMCP"
        good_title="Market Outlook / Knowledge Hub"
        good_url="https://www.sundarammutual.com/knowledge-hub"
        self.scheme(code,family,amc)
        self.old_doc(family,wrong_title,wrong_url)
        good=providers.save_document(
            family,good_title,good_url,"market view","AMC",origin="AMC")
        h=db.archive(b"<html>Sundaram market outlook</html>","text/html")
        providers.doc_version(good,h)

        self.assertEqual([d["url"] for d in documents(code)],[good_url])
        self.assertIn("corporate presentation",exclusion_reason(amc,wrong_url,wrong_title))
        with self.assertRaisesRegex(ValueError,"corporate presentation"):
            providers.save_document(
                family,wrong_title,wrong_url,"market view","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))

    def test_quant_nfos_and_mirae_directory_are_hidden_and_rejected(self):
        cases=[
            (
                "Quant Small Cap Fund",9906,"quant Mutual Fund","a",
                "https://www.quantmutual.com/Admin/Pdf/quan_%20Silver_ETF-NFO_Presentation.pdf",
                "non-Small-Cap NFO presentation",
            ),
            (
                "Quant Small Cap Fund",9907,"quant Mutual Fund","a",
                "https://www.quantmutual.com/Admin/Pdf/quant_Income_Plus_Arbitrage_Active_FOF_presentation.pdf",
                "non-Small-Cap NFO presentation",
            ),
            (
                "Quant Small Cap Fund",9908,"quant Mutual Fund","NFO Presentation",
                "https://quantmutual.com/distributorhub/NFOPresentation.aspx",
                "generic NFO-presentation directory",
            ),
            (
                "Mirae Asset Small Cap Fund",9909,"Mirae Asset Mutual Fund","Product Presentations",
                "https://www.miraeassetmf.co.in/downloads/product-presentations",
                "generic product-presentations directory",
            ),
        ]
        for family,code,amc,title,url,reason in cases:
            if not db.one("SELECT code FROM schemes WHERE family=?",(family,)):
                self.scheme(code,family,amc)
            self.old_doc(family,title,url)
            with self.subTest(url=url):
                self.assertIn(reason,exclusion_reason(amc,url,title))
                with self.assertRaises(ValueError):
                    providers.save_document(family,title,url,"market view","AMC",origin="AMC")

        for family in ("Quant Small Cap Fund","Mirae Asset Small Cap Fund"):
            code=db.one("SELECT MIN(code) code FROM schemes WHERE family=?",(family,))["code"]
            self.assertEqual(documents(code),[])

        self.assertIsNone(exclusion_reason(
            "quant Mutual Fund",
            "https://www.quantmutual.com/Admin/Pdf/VLRT-OUTLOOK-JULY-AUGUST2021.pdf",
            "VLRT Outlook (July-Aug 2021)"))
        self.assertIsNone(exclusion_reason(
            "Mirae Asset Mutual Fund",
            "https://www.miraeassetmf.co.in/docs/default-source/marketing-insights/annual-outlook-2025.pdf",
            "Annual Market Outlook 2026"))

    def test_publication_coverage_ignores_cross_scheme_rows(self):
        family="Helios Small Cap Fund";amc="Helios Mutual Fund"
        self.scheme(9910,family,amc)
        self.old_doc(
            family,"Helios Flexi Cap Fund",
            "https://www.heliosmf.in/wp-content/uploads/2025/04/FLexicap-Fund-Product-Note_.pdf")
        row=next(x for x in report()["funds"] if x["family"]==family)
        self.assertEqual(row["communication_count"],0)
        self.assertIn("no_amc_communications_collected",row["issues"])


if __name__=="__main__":
    unittest.main()
