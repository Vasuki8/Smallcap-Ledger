"""Scheme-specific unitholder/admin artifacts must not enter Small Cap communications."""
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


class FalseUnitholderArtifactTests(unittest.TestCase):
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

    def old_doc(self,family,title,url,kind="unitholder letter"):
        with db.connect() as c:
            return c.execute(
                """INSERT INTO documents(
                     family,title,kind,scope,url,first_seen,last_seen,origin)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (family,title,kind,"AMC",url,db.now(),db.now(),"AMC"),
            ).lastrowid

    def test_absl_public_notice_filename_is_not_market_view(self):
        family="Aditya Birla Sun Life Small Cap Fund"
        amc="Aditya Birla Sun Life Mutual Fund"
        code=9200
        wrong_title="a"
        wrong_url=("https://mutualfund.adityabirlacapital.com/-/media/bsl/files/"
                   "resources/market-update/public-notice_abslamc-1.pdf")
        good_title="Equity Market Outlook - September 2026"
        good_url=("https://mutualfund.adityabirlacapital.com/"
                  "insights/equity-market-outlook-september-2026")
        self.scheme(code,family,amc)
        self.old_doc(family,wrong_title,wrong_url,kind="market view")
        good=providers.save_document(
            family,good_title,good_url,"market view","AMC",origin="AMC")
        h=db.archive(b"<html>ABSL equity market outlook</html>","text/html")
        providers.doc_version(good,h)

        self.assertEqual(providers.classify(wrong_title,wrong_url),"disclosure")
        self.assertEqual([d["url"] for d in documents(code)],[good_url])
        self.assertIn("public notice",exclusion_reason(amc,wrong_url,wrong_title))
        with self.assertRaisesRegex(ValueError,"public notice"):
            providers.save_document(
                family,wrong_title,wrong_url,"market view","AMC",origin="AMC")
        self.assertEqual(providers.classify(good_title,good_url),"market view")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))

    def test_dsp_foreign_scheme_letters_and_generic_foreign_page_are_hidden(self):
        family="DSP Small Cap Fund";amc="DSP Mutual Fund";code=9201
        self.scheme(code,family,amc)
        foreign=[
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP QUANT FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/fundamental-attributes-of-dsp-quant-fund-letter-final.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP US FLEXIBLE EQUITY FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/fac-of-dsp-us-flexible-equity-fund-letter-to-unitholder-july-2024.pdf"),
            ("Change in Fundamental Attributes of DSP World Gold Fund – Unitholder letter",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/change-in-fundamental-attributes-of-dsp-world-gold-fund.pdf"),
            ("Unitholder letter for Merger of DSP World Agriculture Fund into DSP World Mining Fund",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/world-agriculture-with-world-mining-unit-holder-letter.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP WORLD ENERGY FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-world-energy-fund-final.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP GOVERNMENT SECURITIES FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-government-securities-fund.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP FLOATER FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-floater-fund.pdf"),
            ("Change in Fundamental Attributes of DSP Equity Savings Fund – Unitholder Letter",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-equity-savings-fund.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP EQUITY & BOND FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-equity-bond-fund.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP DYNAMIC ASSET ALLOCATION FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-dynamic-asset-allocation-fund.pdf"),
            ("CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP GLOBAL ALLOCATION FUND – UNITHOLDER LETTER",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-global-allocation-fund.pdf"),
            ("Corrigendum to Notice cum Addenda-FA change of DSP Quant Fund",
             "https://www.dspim.com/media/pages/mandatory-disclosures/x/corrigendum-dsp-quant-fund.pdf"),
            ("UNITHOLDER LETTER FOR CHANGE IN FUNDAMENTAL ATTRIBUTE",
             "https://www.dspim.com/mandatory-disclosures/unitholder-letter-for-change-in-fundamental-attribute"),
        ]
        for title,url in foreign:self.old_doc(family,title,url)

        good_title="DSP Small Cap Fund - Letter to Unitholders"
        good_url="https://www.dspim.com/media/pages/mandatory-disclosures/dsp-small-cap-fund-letter.pdf"
        good=providers.save_document(
            family,good_title,good_url,"unitholder letter","Fund",origin="AMC")
        h=db.archive(b"%PDF-1.7 DSP Small Cap letter","application/pdf")
        providers.doc_version(good,h)

        shown=documents(code)
        self.assertEqual([d["url"] for d in shown],[good_url])
        for title,url in foreign:
            with self.subTest(title=title):
                self.assertIsNotNone(exclusion_reason(amc,url,title,'unitholder letter'))
                with self.assertRaises(ValueError):
                    providers.save_document(
                        family,title,url,"unitholder letter","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))
        self.assertEqual(db.one("SELECT COUNT(*) n FROM documents")["n"],len(foreign)+1)

    def test_hdfc_unitholder_directory_is_source_only_and_foreign_letters_are_hidden(self):
        family="HDFC Small Cap Fund";amc="HDFC Mutual Fund";code=9202
        directory="https://www.hdfcfund.com/statutory-disclosure/letter-unitholder"
        self.scheme(code,family,amc)
        # Historical pre-fix row misclassified the directory itself as a letter.
        self.old_doc(family,"Letter to Unitholders",directory)
        foreign=[
            (
                "Letter to Unitholders - Change in Fundamental attributes - HDFC Balanced Advantage Fund",
                "https://files.hdfcfund.com/s3fs-public/2026-10/HDFC-Balanced-Advantage-Fund-letter.pdf",
            ),
            (
                "Letter to Unitholders - Change in Fundamental attributes- HDFC Gold ETF",
                "https://files.hdfcfund.com/s3fs-public/2026-03/HDFC-Gold-ETF-letter.pdf",
            ),
        ]
        for title,url in foreign:self.old_doc(family,title,url)

        good_title="Letter to Unitholders - HDFC Small Cap Fund"
        good_url="https://files.hdfcfund.com/s3fs-public/2026-10/HDFC-Small-Cap-Fund-letter.pdf"
        good=providers.save_document(
            family,good_title,good_url,"unitholder letter","Fund",origin="AMC")
        h=db.archive(b"%PDF-1.7 HDFC Small Cap letter","application/pdf")
        providers.doc_version(good,h)

        shown=documents(code)
        self.assertEqual([d["url"] for d in shown],[good_url])
        self.assertIn(
            "directory",
            exclusion_reason(amc,directory,"Letter to Unitholders","unitholder letter"),
        )
        self.assertIsNone(
            exclusion_reason(amc,directory,"Letter to Unitholders","source page")
        )
        for title,url in foreign:
            with self.subTest(title=title):
                self.assertIn("non-Small-Cap",exclusion_reason(amc,url,title,"unitholder letter"))
                with self.assertRaisesRegex(ValueError,"non-Small-Cap"):
                    providers.save_document(
                        family,title,url,"unitholder letter","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title,"unitholder letter"))

        # A later source refresh can safely repair the historical directory row
        # back to source-page semantics without being blocked by ownership rules.
        providers.save_document(
            family,"Letter to Unitholders",directory,"source page","AMC",origin="AMC")
        row=db.one("SELECT kind FROM documents WHERE family=? AND url=?",(family,directory))
        self.assertEqual(row["kind"],"source page")
        audit=next(x for x in report()["funds"] if x["family"]==family)
        self.assertEqual(audit["unitholder_letter_count"],1)

    def test_quantum_other_scheme_letter_is_hidden_but_small_cap_letter_allowed(self):
        family="Quantum Small Cap Fund";amc="Quantum Mutual Fund";code=9202
        self.scheme(code,family,amc)
        wrong_title=("Letter to Unitholders for Change in Fundamental Attributes of "
                     "Quantum Diversified Equity All Cap Active FOF Jul-26")
        wrong_url="https://www.quantumamc.com/regulatory-document/Addendum-And-News/0/479"
        self.old_doc(family,wrong_title,wrong_url)

        good_title="Letter to Unitholders - Quantum Small Cap Fund"
        good_url="https://www.quantumamc.com/regulatory-document/small-cap-letter"
        good=providers.save_document(
            family,good_title,good_url,"unitholder letter","Fund",origin="AMC")
        h=db.archive(b"%PDF-1.7 Quantum Small Cap letter","application/pdf")
        providers.doc_version(good,h)

        self.assertEqual([d["url"] for d in documents(code)],[good_url])
        self.assertIn("All Cap Active FOF",exclusion_reason(amc,wrong_url,wrong_title))
        with self.assertRaisesRegex(ValueError,"All Cap Active FOF"):
            providers.save_document(
                family,wrong_title,wrong_url,"unitholder letter","AMC",origin="AMC")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))

    def test_samco_lien_request_urls_are_disclosures_not_communications(self):
        family="Samco Small Cap Fund";amc="Samco Mutual Fund";code=9203
        self.scheme(code,family,amc)
        urls=[
            "https://media1.samco.in/scomamc/amc_documents/Lienrequestletterfromunitholder_1790053774.pdf",
            "https://www.samcomf.com/amc-document-download/Lienrequestletterfromunitholder_1790053774.pdf",
        ]
        for url in urls:self.old_doc(family,"a",url)

        self.assertEqual(documents(code),[])
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(providers.classify("a",url),"disclosure")
                self.assertIn("lien-request",exclusion_reason(amc,url,"a"))
                with self.assertRaisesRegex(ValueError,"lien-request"):
                    providers.save_document(
                        family,"a",url,"unitholder letter","AMC",origin="AMC")

        good_title="Samco Small Cap Fund NFO Presentation"
        good_url=("https://media1.samco.in/scomamc/media_uploads/"
                  "SamcoSmallCapFund-SchemePresentatiom(1)_1760509070.pdf")
        self.assertEqual(providers.classify(good_title,good_url),"market view")
        self.assertIsNone(exclusion_reason(amc,good_url,good_title))

    def test_publication_coverage_ignores_false_unitholder_rows(self):
        family="DSP Small Cap Fund";amc="DSP Mutual Fund"
        self.scheme(9204,family,amc)
        self.old_doc(
            family,
            "CHANGE IN FUNDAMENTAL ATTRIBUTES OF DSP WORLD GOLD FUND – UNITHOLDER LETTER",
            "https://www.dspim.com/media/pages/mandatory-disclosures/x/dsp-world-gold-fund.pdf",
        )
        row=next(x for x in report()["funds"] if x["family"]==family)
        self.assertEqual(row["unitholder_letter_count"],0)
        self.assertEqual(row["communication_count"],0)
        self.assertIn("no_amc_communications_collected",row["issues"])


if __name__=="__main__":
    unittest.main()
