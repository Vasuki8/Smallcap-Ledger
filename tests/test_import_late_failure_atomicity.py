"""Late database failures must not leave orphan archives or partial imports."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tracker import db
from tracker.app import app


class LateImportFailureAtomicityTests(unittest.TestCase):
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
                    (8123,"Atomic Small Cap Direct Growth","Atomic Small Cap Fund",
                     "Atomic AMC","Direct","Growth","test"),
                    (8124,"Atomic Small Cap IDCW","Atomic Small Cap Fund",
                     "Atomic AMC","Direct","IDCW","test"),
                ],
            )
        self.client=TestClient(app,raise_server_exceptions=False)
        self.public=patch("tracker.providers.public_url",side_effect=lambda url:url)
        self.public.start()

    def tearDown(self):
        self.public.stop()
        self.data_patch.stop()
        self.tmp.cleanup()

    def post(self,data,payload,name="import.csv"):
        return self.client.post(
            "/api/import",
            headers={"X-Smallcap-Client":"local"},
            data=data,
            files={"file":(name,payload,"text/csv")},
        )

    def assert_no_archive_bytes(self):
        self.assertEqual(db.one("SELECT COUNT(*) n FROM archives")["n"],0)
        root=Path(self.tmp.name)/"archive"
        self.assertFalse(root.exists() and any(p.is_file() for p in root.rglob("*")))

    def test_late_benchmark_failure_rolls_back_archive_and_rows(self):
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_benchmark BEFORE INSERT ON benchmark
                         BEGIN SELECT RAISE(ABORT,'synthetic benchmark failure'); END""")
        r=self.post(
            {"kind":"benchmark","source":"https://example.com/benchmark.csv",
             "benchmark":"Example Smallcap TRI"},
            b"date,value\n2026-09-30,1234.5\n",
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM benchmark")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM benchmark_observations")["n"],0)
        self.assert_no_archive_bytes()

    def test_late_portfolio_failure_rolls_back_archive_and_rows(self):
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_portfolio BEFORE INSERT ON portfolios
                         BEGIN SELECT RAISE(ABORT,'synthetic portfolio failure'); END""")
        r=self.post(
            {"kind":"portfolio","code":"8123","source":"https://example.com/portfolio.csv",
             "as_of":"2026-09-30","complete":"true"},
            b"isin,name,sector,quantity,weight,asset_type\nINE000000001,Alpha,Banks,100,100,Equity\n",
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM portfolios")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings")["n"],0)
        self.assert_no_archive_bytes()

    def test_late_metrics_failure_rolls_back_archive_and_rows(self):
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_imported_ter BEFORE INSERT ON metrics
                         WHEN NEW.metric='ter'
                         BEGIN SELECT RAISE(ABORT,'synthetic metrics failure'); END""")
        r=self.post(
            {"kind":"metrics","code":"8123","source":"https://example.com/metrics.csv"},
            b"metric,plan,as_of,value\naum,All,2026-09-30,1500\nter,Direct,2026-09-30,0.65\n",
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM metrics")["n"],0)
        self.assert_no_archive_bytes()

    def test_late_document_failure_rolls_back_archive_and_document(self):
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_document BEFORE INSERT ON documents
                         BEGIN SELECT RAISE(ABORT,'synthetic document failure'); END""")
        r=self.client.post(
            "/api/import",
            headers={"X-Smallcap-Client":"local"},
            data={
                "kind":"document","code":"8123","source":"https://example.com/factsheet.pdf",
                "title":"Atomic Small Cap Factsheet","document_kind":"factsheet","scope":"Fund",
            },
            files={"file":("factsheet.pdf",b"%PDF-1.7 synthetic","application/pdf")},
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM documents")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM document_versions")["n"],0)
        self.assert_no_archive_bytes()

    def test_late_distribution_document_failure_rolls_back_entire_window(self):
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_distribution_document BEFORE INSERT ON documents
                         BEGIN SELECT RAISE(ABORT,'synthetic distribution document failure'); END""")
        r=self.post(
            {"kind":"distributions","code":"8124","source":"https://example.com/idcw.csv",
             "coverage_from":"2026-01-01","coverage_to":"2026-09-30","complete":"true"},
            b"ex_date,amount,reinvestment_nav\n2026-06-30,1.5,12.5\n",
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM distributions")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM distribution_coverage")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM documents")["n"],0)
        self.assert_no_archive_bytes()

    def test_failed_import_preserves_preexisting_identical_archive(self):
        payload=b"metric,plan,as_of,value\nter,Direct,2026-09-30,0.65\n"
        h=db.archive(payload,"text/csv")
        path=db.archive_binary_path(h)
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_imported_ter BEFORE INSERT ON metrics
                         BEGIN SELECT RAISE(ABORT,'synthetic metrics failure'); END""")
        r=self.post(
            {"kind":"metrics","code":"8123","source":"https://example.com/metrics.csv"},
            payload,
        )
        self.assertEqual(r.status_code,500)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM archives")["n"],1)
        self.assertTrue(path.is_file())
        self.assertEqual(db.archive_retention(h)["binary_state"],"retained")

    def test_failed_import_restores_metadata_only_retention_state(self):
        payload=b"metric,plan,as_of,value\nter,Direct,2026-09-30,0.65\n"
        h=db.archive(payload,"text/csv")
        db.set_archive_retention(
            h,classification="link_only_candidate",binary_state="metadata_only",
            reason="synthetic reviewed link-only evidence")
        path=(db.DATA/db.archive_retention(h)["path"]).resolve()
        path.unlink()
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_imported_ter BEFORE INSERT ON metrics
                         BEGIN SELECT RAISE(ABORT,'synthetic metrics failure'); END""")
        r=self.post(
            {"kind":"metrics","code":"8123","source":"https://example.com/metrics.csv"},
            payload,
        )
        self.assertEqual(r.status_code,500)
        row=db.archive_retention(h)
        self.assertEqual(row["classification"],"link_only_candidate")
        self.assertEqual(row["binary_state"],"metadata_only")
        self.assertEqual(row["reason"],"synthetic reviewed link-only evidence")
        self.assertFalse(path.exists())

    def test_archive_metadata_failure_does_not_leave_untracked_binary(self):
        payload=b"archive metadata failure"
        h=hashlib.sha256(payload).hexdigest()
        target=Path(self.tmp.name)/"archive"/h[:2]/h
        with db.connect() as c:
            c.execute("""CREATE TRIGGER fail_archive BEFORE INSERT ON archives
                         BEGIN SELECT RAISE(ABORT,'synthetic archive metadata failure'); END""")
        with self.assertRaises(Exception):
            db.archive(payload,"text/plain")
        self.assertIsNone(db.archive_retention(h))
        self.assertFalse(target.exists())


if __name__=="__main__":
    unittest.main()
