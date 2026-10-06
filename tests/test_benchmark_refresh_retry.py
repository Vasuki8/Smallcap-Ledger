"""Nifty TRI benchmark refresh retries only transient transport failures."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers


class BenchmarkRefreshRetryTests(unittest.TestCase):
    def test_transient_transport_timeout_is_retried_once(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            body=json.dumps([{
                "Index Name":"NIFTY SMALLCAP 250",
                "Date":"05-Oct-2026",
                "TotalReturnsIndex":"12345.67",
            }]).encode()
            with patch("tracker.providers.india_today",return_value=date(2026,10,6)), \
                 patch("tracker.providers.db.setting",return_value=True), \
                 patch("tracker.providers.fetch",side_effect=[
                     providers.httpx.ReadTimeout("read timed out"),
                     (body,None,"application/json"),
                 ]) as fetch:
                result=providers.fetch_benchmark()
            self.assertEqual(fetch.call_count,2)
            self.assertIn("1 benchmark observations updated",result)
            row=db.one("SELECT date,value FROM benchmark WHERE name=?",(providers.BENCHMARK,))
            self.assertEqual(row["date"],"2026-10-05")
            self.assertAlmostEqual(row["value"],12345.67)

    def test_non_transport_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            with patch("tracker.providers.india_today",return_value=date(2026,10,6)), \
                 patch("tracker.providers.db.setting",return_value=True), \
                 patch("tracker.providers.fetch",side_effect=ValueError("bad response")) as fetch:
                with self.assertRaisesRegex(ValueError,"bad response"):
                    providers.fetch_benchmark()
            self.assertEqual(fetch.call_count,1)


if __name__=="__main__":
    unittest.main()
