"""Tests for combined Mid Cap benchmark readiness."""
import unittest

from tracker.midcap_benchmark_readiness import reconcile


class MidCapBenchmarkReadinessTests(unittest.TestCase):
    def test_batches_merge_without_overwriting_first_evidence(self):
        staged={"A":"AMC A","B":"AMC B","C":"AMC C"}
        b1={"results":[{"family":"A","primary_benchmark":"Nifty Midcap 150","reported_benchmarks":["Nifty Midcap 150"],"source":"a1"}],"errors":[]}
        b2={"results":[{"family":"A","primary_benchmark":"Other","source":"a2"},{"family":"B","primary_benchmark":"BSE 150 Mid Cap TRI","reported_benchmarks":["BSE 150 Mid Cap TRI"],"source":"b"}],"errors":[]}
        r=reconcile(staged,b1,b2)
        by={x["family"]:x for x in r["families_detail"]}
        self.assertEqual(by["A"]["benchmark_identity"],"Nifty Midcap 150")
        self.assertEqual(by["B"]["benchmark_identity"],"BSE 150 Mid Cap TRI")
        self.assertIsNone(by["C"]["benchmark_identity"])
        self.assertEqual(r["benchmark_identity"],2)
        self.assertEqual(r["remaining"],1)
        self.assertEqual(r["production_writes"],0)
        self.assertFalse(r["public_export_enabled"])

if __name__=="__main__":unittest.main()
