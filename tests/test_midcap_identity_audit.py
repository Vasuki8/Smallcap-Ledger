"""Mid Cap staged identity-audit regressions."""
import unittest

from scripts.audit_midcap_identity import audit


def preview(rows):
    return {"source_sha256":"abc","rows":rows}


def row(code,name="Nippon India Growth Mid Cap Fund",amc="Nippon India Mutual Fund",
        plan="Direct Plan",option="Growth Option"):
    return {
        "code":code,"category":"mid-cap","amc":amc,"name":name,
        "plan_raw":plan,"option_raw":option,"isin":"INF000000001",
        "reinvestment_isin":None,"date":"2026-09-25","nav_raw":"10.0",
        "source_label":"Open Ended Schemes(Equity Scheme - Mid Cap Fund)","source_line":100,
    }


class MidCapIdentityAuditTests(unittest.TestCase):
    def test_official_family_name_preserves_legitimate_growth_word(self):
        result=audit(preview([row(1)]),[])
        self.assertEqual(result["proposals"][0]["family"],"Nippon India Growth Mid Cap Fund")
        self.assertTrue(result["mid_cap_import_ready"])
        self.assertEqual(result["production_writes"],0)

    def test_existing_scheme_code_collision_blocks_import(self):
        result=audit(preview([row(1)]),[
            {"code":1,"family":"Existing Small Cap Fund","amc":"Example AMC","category":"small-cap"}
        ])
        self.assertFalse(result["mid_cap_import_ready"])
        self.assertEqual(result["code_collisions"][0]["code"],1)

    def test_cross_category_family_collision_blocks_import(self):
        candidate=row(2,name="Shared Fund",amc="Example AMC")
        result=audit(preview([candidate]),[
            {"code":1,"family":"Shared Fund","amc":"Example AMC","category":"small-cap"}
        ])
        self.assertFalse(result["mid_cap_import_ready"])
        self.assertTrue(result["family_collisions"])

    def test_unresolved_missing_plan_option_blocks_import(self):
        candidate=row(3,name="Motilal Oswal Midcap Fund",amc="Motilal Oswal Mutual Fund",plan="",option="")
        def fake_fetch(url,**kwargs):
            import json
            return json.dumps({"meta":{
                "scheme_code":3,"scheme_name":"Motilal Oswal Midcap Fund",
                "scheme_category":"Equity Scheme - Mid Cap Fund","scheme_type":"Open Ended Schemes",
            }}).encode(),None,"application/json"
        result=audit(preview([candidate]),[],fetch_fn=fake_fetch)
        self.assertFalse(result["mid_cap_import_ready"])
        self.assertEqual(result["unresolved_plan_option"][0]["code"],3)

    def test_exact_code_metadata_can_resolve_missing_plan_option(self):
        candidate=row(4,name="Example Mid Cap Fund",amc="Example AMC",plan="",option="")
        def fake_fetch(url,**kwargs):
            import json
            return json.dumps({"meta":{
                "scheme_code":4,"scheme_name":"Example Mid Cap Fund - Direct Plan - Growth",
                "scheme_category":"Equity Scheme - Mid Cap Fund","scheme_type":"Open Ended Schemes",
            }}).encode(),None,"application/json"
        result=audit(preview([candidate]),[],fetch_fn=fake_fetch)
        self.assertTrue(result["mid_cap_import_ready"])
        self.assertEqual(result["proposals"][0]["plan"],"Direct")
        self.assertEqual(result["proposals"][0]["option"],"Growth")


if __name__=="__main__":
    unittest.main()
