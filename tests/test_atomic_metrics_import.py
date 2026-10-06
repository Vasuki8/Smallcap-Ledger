"""Metrics CSV imports must commit all structured rows or none."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tracker import db
from tracker.app import app


class AtomicMetricsImportTests(unittest.TestCase):
    def test_database_failure_rolls_back_every_metric_row(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    """INSERT INTO schemes(
                         code,name,family,amc,plan,option,category_source)
                       VALUES(?,?,?,?,?,?,?)""",
                    (8123,"Atomic Small Cap Direct Growth","Atomic Small Cap Fund",
                     "Atomic AMC","Direct","Growth","test"),
                )
                c.execute(
                    """CREATE TRIGGER fail_imported_ter
                       BEFORE INSERT ON metrics
                       WHEN NEW.metric='ter'
                       BEGIN
                         SELECT RAISE(ABORT,'synthetic metrics failure');
                       END"""
                )
            client=TestClient(app,raise_server_exceptions=False)
            csv=(
                b"metric,plan,as_of,value\n"
                b"aum,All,2026-09-30,1500\n"
                b"ter,Direct,2026-09-30,0.65\n"
            )
            with patch("tracker.providers.public_url",side_effect=lambda url:url):
                response=client.post(
                    "/api/import",
                    headers={"X-Smallcap-Client":"local"},
                    data={
                        "kind":"metrics",
                        "code":"8123",
                        "source":"https://example.com/metrics.csv",
                    },
                    files={"file":("metrics.csv",csv,"text/csv")},
                )
            self.assertEqual(response.status_code,500)
            self.assertEqual(
                db.one("SELECT COUNT(*) n FROM metrics WHERE family=?",("Atomic Small Cap Fund",))["n"],
                0,
            )
            self.assertEqual(db.one("SELECT COUNT(*) n FROM fetches")["n"],0)


if __name__=="__main__":
    unittest.main()
