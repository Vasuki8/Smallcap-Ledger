"""Structured user imports must remain local and never cross the public publication boundary."""
import csv
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts import export_site
from tracker import db, disclosures, providers
from tracker.app import app, fund, fund_data
from tracker.coverage import report as coverage_report
from tracker.performance_coverage import _benchmark_cache


FAMILY="Boundary Small Cap Fund"
GROWTH=8801
IDCW=8802


class StructuredImportPublicationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        self.addCleanup(self.data_patch.stop)
        db.init()
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (GROWTH,FAMILY+" Direct Growth",FAMILY,"Boundary AMC","Direct","Growth","test"),
                    (IDCW,FAMILY+" Direct IDCW",FAMILY,"Boundary AMC","Direct","IDCW","test"),
                ],
            )
        for code in (GROWTH,IDCW):
            db.save_nav(
                code,
                [("2026-09-29",100.0),("2026-09-30",101.0)],
                providers.AMFI_NAV,
            )
        official_metric_source="https://example.com/official-factsheet.pdf"
        db.metric(FAMILY,"All","aum","2026-09-01",100,"INR crore",official_metric_source,"official-aum")
        db.metric(FAMILY,"Direct","ter","2026-09-01",0.50,"% p.a.",official_metric_source,"official-ter")
        db.metric(
            FAMILY,"All","benchmark","2026-09-01","Nifty Smallcap 250 TRI",
            "Reported",official_metric_source,"official-benchmark",
        )
        disclosures.portfolio(
            FAMILY,"2026-08-31",
            [{"name":"Official Holding","isin":"INE000000001","sector":"Banks",
              "weight":100.0,"quantity":100,"asset_type":"Equity"}],
            True,
            "https://example.com/official-portfolio.xlsx",
            "official-portfolio-hash",
        )
        db.save_benchmark(
            providers.BENCHMARK,
            [("2026-09-29",10000.0),("2026-09-30",10050.0)],
            providers.NIFTY_PAGE,
        )
        self.client=TestClient(app)
        self.public_url=patch("tracker.app.providers.public_url",side_effect=lambda url:url)
        self.public_url.start()
        self.addCleanup(self.public_url.stop)

    def post_csv(self,kind,name,body,**data):
        payload={"kind":kind,"source":f"https://example.com/{name}",**data}
        response=self.client.post(
            "/api/import",
            headers={"X-Smallcap-Client":"local"},
            data=payload,
            files={"file":(name,body,"text/csv")},
        )
        self.assertEqual(response.status_code,200,response.text)
        return response

    def import_all_structured_types(self):
        self.post_csv(
            "metrics","user-metrics.csv",
            b"metric,plan,as_of,value\naum,All,2026-10-01,999\nter,Direct,2026-10-01,9.99\n",
            code=str(GROWTH),
        )
        self.post_csv(
            "portfolio","user-portfolio.csv",
            b"isin,name,sector,quantity,weight,asset_type\nINE000000002,User Holding,Technology,999,100,Equity\n",
            code=str(GROWTH),as_of="2026-09-30",complete="true",
        )
        self.post_csv(
            "benchmark","user-benchmark.csv",
            b"date,value\n2026-10-01,99999\n",
            benchmark=providers.BENCHMARK,
        )
        self.post_csv(
            "distributions","user-distributions.csv",
            b"ex_date,amount,reinvestment_nav\n2026-09-15,1.25,10.5\n",
            code=str(IDCW),complete="true",
            coverage_from="2026-09-01",coverage_to="2026-09-30",
        )

    def test_schema_migration_defaults_existing_structured_rows_to_official(self):
        # Build an old-schema database separately, then let db.init() migrate it.
        old_dir=Path(self.tmp.name)/"old-schema"
        old_dir.mkdir()
        with sqlite3.connect(old_dir/"ledger.sqlite3") as c:
            c.execute("""CREATE TABLE metrics(
                id INTEGER PRIMARY KEY,family TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'All',
                metric TEXT NOT NULL,as_of TEXT NOT NULL,value TEXT NOT NULL,unit TEXT,
                source TEXT NOT NULL,hash TEXT NOT NULL DEFAULT '',observed_at TEXT NOT NULL,
                UNIQUE(family,plan,metric,as_of,value,source))""")
            c.execute(
                """INSERT INTO metrics(
                   family,plan,metric,as_of,value,unit,source,hash,observed_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                ("Old Small Cap Fund","All","aum","2026-09-01","12","INR crore",
                 "https://example.com/old","old-hash","2026-09-02T00:00:00+00:00"),
            )
        with patch.object(db,"DATA",old_dir):
            db.init()
            columns={r["name"] for r in db.rows("PRAGMA table_info(metrics)")}
            self.assertIn("origin",columns)
            self.assertEqual(
                db.one("SELECT origin FROM metrics WHERE family='Old Small Cap Fund'")["origin"],
                "Official",
            )
            for table in (
                "benchmark","benchmark_observations","metrics","portfolios",
                "distribution_coverage","distributions",
            ):
                with self.subTest(table=table):
                    self.assertIn(
                        "origin",
                        {r["name"] for r in db.rows(f"PRAGMA table_info({table})")},
                    )

    def test_all_import_types_are_marked_user_import_but_stay_visible_locally(self):
        self.import_all_structured_types()

        self.assertEqual(
            db.one("SELECT origin FROM metrics WHERE family=? AND metric='aum' AND as_of='2026-10-01'",(FAMILY,))["origin"],
            "User import",
        )
        self.assertEqual(
            db.one("SELECT origin FROM portfolios WHERE family=? AND as_of='2026-09-30'",(FAMILY,))["origin"],
            "User import",
        )
        self.assertEqual(
            db.one("SELECT origin FROM benchmark WHERE name=? AND date='2026-10-01'",(providers.BENCHMARK,))["origin"],
            "User import",
        )
        self.assertEqual(
            db.one("SELECT origin FROM distributions WHERE code=?",(IDCW,))["origin"],
            "User import",
        )
        self.assertEqual(
            db.one("SELECT origin FROM distribution_coverage WHERE code=?",(IDCW,))["origin"],
            "User import",
        )

        local=fund(GROWTH)
        self.assertEqual(local["metrics"]["aum"]["value"],"999.0")
        self.assertEqual(local["portfolios"][0]["as_of"],"2026-09-30")
        self.assertEqual(fund(IDCW)["distribution_coverage"]["origin"],"User import")

        public=fund_data(GROWTH,True)
        self.assertEqual(public["metrics"]["aum"]["value"],"100")
        self.assertEqual(public["portfolios"][0]["as_of"],"2026-08-31")
        self.assertIsNone(fund_data(IDCW,True)["distribution_coverage"])

        coverage=coverage_report()
        row=next(x for x in coverage["funds"] if x["family"]==FAMILY)
        self.assertEqual(row["aum"]["value"],"100")
        self.assertEqual(row["portfolio"]["as_of"],"2026-08-31")
        self.assertEqual(row["portfolio"]["source"],"https://example.com/official-portfolio.xlsx")

        cache=_benchmark_cache()
        self.assertNotIn("2026-10-01",{p[0] for p in cache[providers.BENCHMARK]})

    def test_user_document_parser_outputs_are_also_marked_unverified(self):
        def parsed_xml(_content,family,source,h):
            db.metric(family,"All","aum","2026-10-02",777,"INR crore",source,h)
            disclosures.portfolio(
                family,"2026-09-30",
                [{"name":"Parsed User Holding","weight":100.0,"asset_type":"Equity"}],
                True,source,h,
            )
            return 2

        with patch("tracker.disclosures.summary_xml",side_effect=parsed_xml):
            response=self.client.post(
                "/api/import",
                headers={"X-Smallcap-Client":"local"},
                data={
                    "kind":"document","code":str(GROWTH),
                    "source":"https://example.com/user-facts.xml",
                    "title":"User facts","document_kind":"factsheet","scope":"Fund",
                },
                files={"file":("user-facts.xml",b"<facts/>","application/xml")},
            )
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(
            db.one("SELECT origin FROM metrics WHERE family=? AND as_of='2026-10-02'",(FAMILY,))["origin"],
            "User import",
        )
        self.assertEqual(
            db.one("SELECT origin FROM portfolios WHERE family=? AND as_of='2026-09-30'",(FAMILY,))["origin"],
            "User import",
        )
        self.assertEqual(fund_data(GROWTH,True)["metrics"]["aum"]["value"],"100")

    def test_official_evidence_promotes_matching_imported_rows(self):
        source="https://www.niftyindices.com/reports/historical-data"
        with db.row_origin("User import"):
            db.metric(FAMILY,"All","risk","2026-09-30","Very High","Reported",source,"same-metric")
            disclosures.portfolio(
                FAMILY,"2026-09-30",
                [{"name":"Promoted Holding","weight":100.0,"asset_type":"Equity"}],
                True,source,"same-portfolio",
            )
        db.save_benchmark(
            providers.BENCHMARK,[("2026-09-28",9000.0)],source,
            authoritative=False,origin="User import",
        )

        db.metric(FAMILY,"All","risk","2026-09-30","Very High","Reported",source,"same-metric")
        disclosures.portfolio(
            FAMILY,"2026-09-30",
            [{"name":"Promoted Holding","weight":100.0,"asset_type":"Equity"}],
            True,source,"same-portfolio",
        )
        db.save_benchmark(
            providers.BENCHMARK,[("2026-09-28",9000.0)],source,
            authoritative=True,origin="Official",
        )

        self.assertEqual(
            db.one("SELECT origin FROM metrics WHERE hash='same-metric'")["origin"],
            "Official",
        )
        self.assertEqual(
            db.one("SELECT origin FROM portfolios WHERE hash='same-portfolio'")["origin"],
            "Official",
        )
        self.assertEqual(
            db.one("SELECT origin FROM benchmark WHERE name=? AND date='2026-09-28'",(providers.BENCHMARK,))["origin"],
            "Official",
        )
        self.assertEqual(
            db.one("SELECT origin FROM benchmark_observations WHERE name=? AND date='2026-09-28'",(providers.BENCHMARK,))["origin"],
            "Official",
        )

    def test_static_export_contains_only_official_structured_rows(self):
        self.import_all_structured_types()
        output=Path(self.tmp.name)/"site"
        export_site.export(output,"Vasuki8/Smallcap-Ledger")

        fund_json=json.loads((output/"data"/"funds"/f"{GROWTH}.json").read_text(encoding="utf-8"))
        self.assertEqual(fund_json["metrics"]["aum"]["value"],"100")
        self.assertEqual(fund_json["portfolios"][0]["as_of"],"2026-08-31")
        self.assertTrue(all(x["origin"]=="Official" for x in fund_json["metric_history"]))
        self.assertTrue(all(x["origin"]=="Official" for x in fund_json["portfolios"]))

        idcw_json=json.loads((output/"data"/"funds"/f"{IDCW}.json").read_text(encoding="utf-8"))
        self.assertEqual(idcw_json["distributions"],[])

        benchmarks=json.loads((output/"data"/"benchmarks.json").read_text(encoding="utf-8"))
        dates={p[0] for p in benchmarks[providers.BENCHMARK]["data"]}
        self.assertNotIn("2026-10-01",dates)
        self.assertEqual(dates,{"2026-09-29","2026-09-30"})

        coverage=json.loads((output/"data"/"coverage.json").read_text(encoding="utf-8"))
        row=next(x for x in coverage["funds"] if x["family"]==FAMILY)
        self.assertEqual(row["aum"]["value"],"100")
        self.assertEqual(row["portfolio"]["as_of"],"2026-08-31")


if __name__=="__main__":
    unittest.main()
