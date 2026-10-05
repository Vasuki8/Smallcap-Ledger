"""Axis monthly portfolio CMS must be wired into the active source ingestion loop."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures
from tracker.axis_portfolios import FAMILY


class AxisPortfolioIngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                (9901,"Axis Small Cap Direct Growth",FAMILY,
                 "Axis Mutual Fund","Direct","Growth","test"),
            )

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_axis_downloads_source_uses_exact_cms_workbook_and_normal_archive_pipeline(self):
        target=(
            "https://www.axismf.com/1/5/464/560/3622/4549/"
            "Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_test.xlsx"
        )
        title="Monthly Portfolio - Axis Small Cap Fund - 31 August 2026"
        body=b"PK\x03\x04axis-workbook"
        h=db.archive(body,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        source={"amc_match":"Axis","url":"https://www.axismf.com/downloads","label":"Downloads"}

        with patch("tracker.axis_portfolios.discover",
                   return_value=iter([(FAMILY,target,title)])) as discover, \
             patch("tracker.disclosures.india_today",return_value=date(2026,9,25)), \
             patch("tracker.disclosures.can_crawl",return_value=True) as crawl, \
             patch("tracker.disclosures.fetch",
                   return_value=(body,h,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) as fetch, \
             patch("tracker.amc_reports.extract",return_value=77) as extract:
            result=disclosures.ingest_source(source)

        self.assertIn("1 exact monthly portfolio links",result)
        self.assertIn("1 documents archived",result)
        self.assertIn("77 facts/holdings",result)
        discover.assert_called_once()
        self.assertEqual(discover.call_args.kwargs["today"],date(2026,9,25))
        self.assertEqual(fetch.call_args.args[0],target)
        extract.assert_called_once_with(body,FAMILY,target,h)
        self.assertGreaterEqual(crawl.call_count,2)

        doc=db.one("SELECT title,kind,scope,origin,url FROM documents WHERE family=? AND url=?",(FAMILY,target))
        self.assertEqual(doc,{
            "title":title,
            "kind":"portfolio",
            "scope":"Fund",
            "origin":"AMC",
            "url":target,
        })

    def test_axis_discovery_defaults_use_india_calendar(self):
        from tracker import axis_portfolios
        with patch("tracker.axis_portfolios.india_today",return_value=date(2026,9,1)):
            months=list(axis_portfolios.closed_month_ends())
        self.assertEqual(months,[date(2026,8,31),date(2026,7,31)])
        source=(Path(__file__).resolve().parents[1]/"tracker"/"axis_portfolios.py").read_text(encoding="utf-8")
        self.assertNotIn("date.today()",source)


if __name__=="__main__":
    unittest.main()
