"""Isolated Mid Cap staging-store tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from scripts.stage_midcap_import import stage


def fixture():
    preview={
        "source_sha256":"abc","prepared_at":"2026-09-27T00:00:00+00:00",
        "rows":[{
            "code":200001,"category":"mid-cap","amc":"Example AMC",
            "name":"Example Growth Mid Cap Fund","plan_raw":"Direct Plan","option_raw":"Growth",
            "nav_raw":"12.5000","date":"2026-09-25","source_line":123,
            "source_label":"Open Ended Schemes(Equity Scheme - Mid Cap Fund)",
            "isin":"INF000000001","reinvestment_isin":None,
        }],
    }
    audit={
        "mid_cap_import_ready":True,"production_writes":0,"source_preview_sha256":"abc",
        "proposals":[{
            "code":200001,"category":"mid-cap","family":"Example Growth Mid Cap Fund",
            "amc":"Example AMC","plan":"Direct","option":"Growth","isin":"INF000000001",
            "reinvestment_isin":None,"nav_date":"2026-09-25","nav_raw":"12.5000",
            "source_line":123,"source_label":"Open Ended Schemes(Equity Scheme - Mid Cap Fund)",
        }],
    }
    return audit,preview


class MidCapStagingStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as conn:
            conn.execute("""INSERT INTO schemes(code,name,family,amc,plan,option,category,category_source)
                VALUES(1,'Existing Small Cap','Existing Small Cap','Existing AMC','Direct','Growth','small-cap','fixture')""")
            conn.execute("""INSERT INTO nav(code,date,value,source,observed_at)
                VALUES(1,'2026-09-25',10,'fixture','2026-09-27T00:00:00+00:00')""")

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def test_stage_writes_only_isolated_tables(self):
        audit,preview=fixture();result=stage(audit,preview)
        self.assertEqual(result["staged_schemes"],1)
        self.assertEqual(result["live_scheme_rows"],1)
        self.assertFalse(result["public_export_enabled"])
        self.assertEqual(db.one("SELECT COUNT(*) n FROM schemes")["n"],1)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM nav")["n"],1)
        staged=db.one("SELECT * FROM category_staged_schemes WHERE code=200001")
        self.assertEqual(staged["name"],"Example Growth Mid Cap Fund")
        self.assertEqual(staged["family"],"Example Growth Mid Cap Fund")
        self.assertEqual(staged["category"],"mid-cap")
        nav=db.one("SELECT * FROM category_staged_nav WHERE code=200001")
        self.assertEqual(nav["date"],"2026-09-25")
        self.assertEqual(nav["value"],12.5)

    def test_stage_requires_ready_matching_audit(self):
        audit,preview=fixture();audit["mid_cap_import_ready"]=False
        with self.assertRaisesRegex(ValueError,"not import-ready"):stage(audit,preview)
        audit,preview=fixture();audit["source_preview_sha256"]="other"
        with self.assertRaisesRegex(ValueError,"hash mismatch"):stage(audit,preview)

    def test_live_code_collision_is_rejected(self):
        audit,preview=fixture()
        audit["proposals"][0]["code"]=1;preview["rows"][0]["code"]=1
        with self.assertRaisesRegex(ValueError,"collide"):stage(audit,preview)

    def test_repeated_stage_updates_without_duplication(self):
        audit,preview=fixture();stage(audit,preview)
        preview["rows"][0]["nav_raw"]="13.0000"
        stage(audit,preview)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM category_staged_schemes")["n"],1)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM category_staged_nav")["n"],1)
        self.assertEqual(db.one("SELECT value FROM category_staged_nav WHERE code=200001")["value"],13.0)


if __name__=="__main__":
    unittest.main()
