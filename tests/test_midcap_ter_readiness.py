"""Tests for staged Mid Cap TER readiness reconciliation."""
import unittest
from tracker.midcap_ter_readiness import reconcile

class MidCapTerReadinessTests(unittest.TestCase):
    def test_first_party_fills_only_amfi_gap(self):
        source={"families":[
            {"family":"A","amc":"AMC A","direct_ter_available":True,
             "ter":{"direct":{"value":0.5},"regular":{"value":1.5},"as_of":"2026-09-24","source":"amfi"}},
            {"family":"B","amc":"AMC B","direct_ter_available":False,"ter":None},
        ]}
        first={"results":[
            {"family":"A","status":"recovered","direct_ter":9.9,"regular_ter":9.9,"as_of":"2026-09-27","source":"fp"},
            {"family":"B","status":"recovered","direct_ter":0.8,"regular_ter":1.8,"as_of":"2026-09-27","source":"fp","identity":{"scheme_name":"B"}},
        ]}
        result=reconcile(source,first)
        by={r["family"]:r for r in result["families"]}
        self.assertEqual(by["A"]["evidence_channel"],"amfi")
        self.assertEqual(by["A"]["direct_ter"],0.5)
        self.assertEqual(by["B"]["evidence_channel"],"first_party_amc")
        self.assertEqual(result["counts"]["direct_ter"],2)
        self.assertEqual(result["counts"]["remaining"],0)
        self.assertEqual(result["production_writes"],0)
        self.assertFalse(result["public_export_enabled"])

if __name__=="__main__":
    unittest.main()
