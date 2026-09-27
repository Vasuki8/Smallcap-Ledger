"""Mid Cap isolated historical-NAV staging tests."""
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from tracker import db
from scripts.backfill_midcap_history import backfill,due_for_history


class MidCapHistoryStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as conn:
            conn.execute("""INSERT INTO schemes(
              code,name,family,amc,plan,option,category,category_source)
              VALUES(1,'Live Small Cap','Live Small Cap','Live AMC','Direct','Growth','small-cap','fixture')""")
            conn.execute("""INSERT INTO nav(code,date,value,source,observed_at)
              VALUES(1,'2026-09-25',10,'fixture','2026-09-27T00:00:00+00:00')""")
            conn.execute("""INSERT INTO category_staged_schemes(
              code,category,name,family,amc,plan,option,source_sha256,first_seen,last_seen,metadata_json)
              VALUES(200001,'mid-cap','Example Mid Cap','Example Mid Cap','Example AMC',
              'Direct','Growth','amfi','2026-09-27T00:00:00+00:00','2026-09-27T00:00:00+00:00','{}')""")
            conn.execute("""INSERT INTO category_staged_nav(
              code,date,value,source_url,source_sha256,observed_at)
              VALUES(200001,'2026-09-25',12.5,'https://www.amfiindia.com/spages/NAVAll.txt',
              'amfi','2026-09-27T00:00:00+00:00')""")

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def fake_fetch(self,url,**kwargs):
        payload={"meta":{
            "scheme_code":200001,"scheme_name":"Example Mid Cap Fund - Direct Plan - Growth",
            "scheme_category":"Equity Scheme - Mid Cap Fund","scheme_type":"Open Ended Schemes",
        },"data":[
            {"date":"25-09-2026","nav":"99.0"},
            {"date":"24-09-2026","nav":"12.4"},
            {"date":"23-09-2026","nav":"12.3"},
        ]}
        return json.dumps(payload).encode(),None,"application/json"

    def test_backfill_adds_history_without_touching_live_tables_or_amfi_date(self):
        result=backfill(fetch_fn=self.fake_fetch)
        self.assertEqual(result["history_succeeded"],1)
        self.assertEqual(result["history_failed"],0)
        self.assertEqual(result["live_writes"],0)
        self.assertFalse(result["public_export_enabled"])
        self.assertEqual(db.one("SELECT COUNT(*) n FROM schemes")["n"],1)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM nav")["n"],1)
        rows=db.rows("SELECT date,value,source_url FROM category_staged_nav WHERE code=200001 ORDER BY date")
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[-1]["value"],12.5)
        self.assertIn("amfiindia.com",rows[-1]["source_url"])
        self.assertEqual(db.one("SELECT history_status FROM category_staged_schemes WHERE code=200001")["history_status"],
                         "3 NAV observations")

    def test_wrong_category_fails_closed_and_preserves_current_stage(self):
        def wrong(url,**kwargs):
            payload={"meta":{"scheme_code":200001,"scheme_category":"Equity Scheme - Small Cap Fund"},"data":[
                {"date":"24-09-2026","nav":"12.4"}]}
            return json.dumps(payload).encode(),None,"application/json"
        result=backfill(fetch_fn=wrong)
        self.assertEqual(result["history_failed"],1)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM category_staged_nav")["n"],1)
        self.assertTrue(db.one("SELECT history_status FROM category_staged_schemes WHERE code=200001")["history_status"].startswith("Error:"))

    def test_healthy_history_uses_bounded_refresh_cadence(self):
        row={"history_checked":"2026-09-20T00:00:00+00:00","history_status":"100 NAV observations"}
        now=datetime(2026,9,27,tzinfo=timezone.utc)
        self.assertFalse(due_for_history(row,now=now,refresh_days=30))
        row["history_status"]="Error: transient"
        self.assertTrue(due_for_history(row,now=now,refresh_days=30))


if __name__=="__main__":
    unittest.main()
