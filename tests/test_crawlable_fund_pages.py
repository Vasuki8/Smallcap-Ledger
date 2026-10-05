"""Crawlable public fund-page generation regressions."""
import tempfile
import unittest
from pathlib import Path

from scripts.export_site import fund_slug, github_pages_root, write_crawlable_fund_pages


class CrawlableFundPageTests(unittest.TestCase):
    def index(self):
        return {"funds":[
            {
                "code":101,"family":"Example Small Cap Fund","amc":"Example Mutual Fund",
                "plan":"Regular","option":"Growth","option_label":"Growth",
                "nav":{"date":"2026-10-05","value":12.34},
                "returns":{"1":5.1,"3":8.2,"5":None},
                "metrics":{"aum":{"value":"1234.5","as_of":"2026-10-04","source":"https://example.com/aum"},
                           "ter":{"value":"1.45","as_of":"2026-10-05","source":"https://example.com/ter"},
                           "benchmark":{"value":"Nifty Smallcap 250 TRI","as_of":"2026-09-30","source":"https://example.com/benchmark"}},
            },
            {
                "code":102,"family":"Example Small Cap Fund","amc":"Example Mutual Fund",
                "plan":"Direct","option":"Growth","option_label":"Growth",
                "nav":{"date":"2026-10-05","value":13.45},
                "returns":{"1":6.1,"3":9.2,"5":10.0},
                "metrics":{"aum":{"value":"1234.5","as_of":"2026-10-04","source":"https://example.com/aum"},
                           "ter":{"value":"0.65","as_of":"2026-10-05","source":"https://example.com/ter"},
                           "benchmark":{"value":"Nifty Smallcap 250 TRI","as_of":"2026-09-30","source":"https://example.com/benchmark"}},
            },
            {
                "code":201,"family":"Second & Special Small Cap Fund","amc":"Second AMC",
                "plan":"Direct","option":"Growth","option_label":"Growth",
                "nav":None,"returns":{},"metrics":{},
            },
        ]}

    def test_slug_and_pages_root_are_stable(self):
        self.assertEqual(fund_slug("Second & Special Small Cap Fund"),"second-special-small-cap-fund")
        self.assertEqual(github_pages_root("Vasuki8/Smallcap-Ledger"),
                         "https://vasuki8.github.io/Smallcap-Ledger/")
        self.assertEqual(github_pages_root("Vasuki8/Vasuki8.github.io"),
                         "https://vasuki8.github.io/")

    def test_generator_writes_one_page_per_family_and_prefers_direct_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            result=write_crawlable_fund_pages(root,self.index(),"Vasuki8/Smallcap-Ledger")
            self.assertEqual(result["fund_pages"],2)
            page=(root/"funds"/"example-small-cap-fund"/"index.html").read_text(encoding="utf-8")
            self.assertIn("Example Small Cap Fund – NAV, AUM, Expense Ratio &amp; Returns",page)
            self.assertIn("₹13.45",page)
            self.assertIn("0.65%",page)
            self.assertIn('href="../../#/fund/102"',page)
            self.assertNotIn('href="../../#/fund/101"',page)
            self.assertIn('<link rel="canonical" href="https://vasuki8.github.io/Smallcap-Ledger/funds/example-small-cap-fund/">',page)

    def test_sitemap_and_robots_reference_crawlable_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_crawlable_fund_pages(root,self.index(),"Vasuki8/Smallcap-Ledger")
            sitemap=(root/"sitemap.xml").read_text(encoding="utf-8")
            robots=(root/"robots.txt").read_text(encoding="utf-8")
            self.assertIn("https://vasuki8.github.io/Smallcap-Ledger/",sitemap)
            self.assertIn("/funds/example-small-cap-fund/",sitemap)
            self.assertIn("/funds/second-special-small-cap-fund/",sitemap)
            self.assertIn("Sitemap: https://vasuki8.github.io/Smallcap-Ledger/sitemap.xml",robots)


if __name__=="__main__":
    unittest.main()
