"""Tests for the staged Mid Cap launch-readiness policy."""
import unittest
from tracker.midcap_launch_readiness import evaluate


class MidCapLaunchReadinessTests(unittest.TestCase):
    def fixtures(self,bench=12,portfolio=9,ter=31):
        source={"counts":{"families":34,"aum":34},"source_errors":[]}
        ter_r={"counts":{"direct_ter":ter}}
        bench_r={"benchmark_identity":bench}
        port_r={"current_portfolio_evidence":portfolio,"current_complete_portfolios":1}
        history={"scheme_codes":135,"nav_scheme_codes":135,"history_failed":0}
        return source,ter_r,bench_r,port_r,history

    def test_current_state_is_not_data_ready(self):
        r=evaluate(*self.fixtures(),public_surface_ready=False)
        self.assertFalse(r["data_ready"])
        self.assertFalse(r["launch_ready"])
        self.assertEqual(r["required"]["direct_ter"],31)
        self.assertEqual(r["required"]["benchmark_identity"],31)
        self.assertEqual(r["required"]["current_portfolio_evidence"],28)
        self.assertEqual(r["remaining_to_data_gate"]["benchmark_identity"],19)
        self.assertEqual(r["remaining_to_data_gate"]["current_portfolio_evidence"],19)

    def test_data_ready_still_requires_public_surface_dry_run(self):
        r=evaluate(*self.fixtures(bench=31,portfolio=28),public_surface_ready=False)
        self.assertTrue(r["data_ready"])
        self.assertFalse(r["launch_ready"])
        self.assertEqual(r["recommended_action"],"prepare_category_aware_public_surface_dry_run")
        r=evaluate(*self.fixtures(bench=31,portfolio=28),public_surface_ready=True)
        self.assertTrue(r["launch_ready"])

    def test_nav_history_is_hard_gate(self):
        source,ter,bench,port,history=self.fixtures(bench=34,portfolio=34)
        history["history_failed"]=1
        r=evaluate(source,ter,bench,port,history,public_surface_ready=True)
        self.assertFalse(r["data_ready"])
        self.assertIn("scheme_nav_identity",r["blockers"])


if __name__=="__main__":
    unittest.main()
