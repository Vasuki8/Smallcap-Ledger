"""Launch decisions must use current rows and verified upstream inputs."""
import unittest
from datetime import datetime, timezone
from tracker.midcap_launch_readiness import evaluate, REQUIRED_INPUTS
from tracker.midcap_portfolio_readiness import reconcile

NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)

class MidCapLaunchReadinessTests(unittest.TestCase):
    def fixtures(self, bench=12, portfolio=9, ter=31):
        staged = {f"Fund {i}": f"AMC {i}" for i in range(34)}
        source = {"counts":{"families":34,"aum":34,"scheme_codes":135}, "source_errors":[],
                  "families":[{"family":f,"amc":a} for f,a in staged.items()]}
        rows = [dict(family=f"Fund {i}",amc=f"AMC {i}",status="recovered",as_of="2026-08-31",
                     positions_observed=10, complete=(i==0), scope="structured_monthly_portfolio",
                     source="https://example.com/portfolio.xlsx",source_sha256="a"*64,
                     observed_at="2026-09-27T12:00:00Z") for i in range(portfolio)]
        port = reconcile(staged, {"results":rows,"errors":[],"staged_category":"mid-cap",
                                 "built_at":"2026-09-27T12:01:00Z"}, now=NOW)
        return source, {"counts":{"families":34,"direct_ter":ter}}, {"families":34,"benchmark_identity":bench}, port, {"scheme_codes":135,"nav_scheme_codes":135,"history_failed":0}
    def check(self, values=None, **kwargs):
        kwargs.setdefault("input_health", [{"name":name,"ok":True} for name in REQUIRED_INPUTS])
        kwargs.setdefault("now", NOW)
        return evaluate(*(values or self.fixtures()), **kwargs)
    def test_current_state_is_not_data_ready(self):
        r = self.check()
        self.assertFalse(r["data_ready"])
        self.assertFalse(r["launch_ready"])
        self.assertEqual(r["required"], {"aum":34,"direct_ter":31,"benchmark_identity":31,"current_portfolio_evidence":28})
        self.assertEqual(r["remaining_to_data_gate"]["benchmark_identity"], 19)
        self.assertEqual(r["remaining_to_data_gate"]["current_portfolio_evidence"], 19)
    def test_retained_aum_presence_does_not_clear_live_source_failure(self):
        values=list(self.fixtures(bench=34,portfolio=34))
        values[0]["source_errors"]=[{"source":"AMFI daily AUM","error":"502 Bad Gateway"}]
        values[0]["aum_evidence"]={"mode":"retained_last_verified","current_fetch_ok":False}
        result=self.check(values,public_surface_ready=True)
        self.assertEqual(result["actual"]["aum"],34)
        self.assertTrue(result["gates"]["aum"])
        self.assertFalse(result["gates"]["source_fetch_health"])
        self.assertFalse(result["data_ready"])
        self.assertFalse(result["launch_ready"])
        self.assertIn("source_fetch_health",result["blockers"])

    def test_data_ready_still_requires_public_surface_dry_run(self):
        values=self.fixtures(bench=31,portfolio=28)
        r=self.check(values)
        self.assertTrue(r["data_ready"])
        self.assertFalse(r["launch_ready"])
        self.assertTrue(self.check(values,public_surface_ready=True)["launch_ready"])
        self.assertFalse(r["public_export_enabled"])
    def test_nav_history_is_hard_gate(self):
        values=self.fixtures(bench=34,portfolio=34); values[-1]["history_failed"]=1
        self.assertFalse(self.check(values,public_surface_ready=True)["data_ready"])
    def test_no_input_proof_cannot_make_counts_green(self):
        self.assertFalse(self.check(self.fixtures(bench=34,portfolio=34),input_health=None)["data_ready"])
    def test_missing_or_failed_upstream_proof_blocks_launch(self):
        proof=[{"name":name,"ok":True} for name in REQUIRED_INPUTS]
        for candidate in (proof[:-1], [dict(x,ok=False) if i==0 else x for i,x in enumerate(proof)]):
            self.assertFalse(self.check(self.fixtures(bench=34,portfolio=34),input_health=candidate)["data_ready"])
    def test_falsely_green_portfolio_summary_is_recomputed(self):
        values=self.fixtures(bench=34,portfolio=9)
        values[3]["current_portfolio_evidence"]=34
        r=self.check(values,public_surface_ready=True)
        self.assertEqual(r["actual"]["current_portfolio_evidence"],9)
        self.assertFalse(r["data_ready"])
    def test_month_rollover_does_not_trust_retained_current_flags(self):
        r=self.check(self.fixtures(bench=34,portfolio=34),now=datetime(2026,10,11,tzinfo=timezone.utc))
        self.assertEqual(r["actual"]["current_portfolio_evidence"],0)
        self.assertFalse(r["data_ready"])
    def test_invalid_missing_or_mismatched_portfolio_report_is_blocked(self):
        for port in ({}, {"current_portfolio_evidence":34}, None, []):
            values=list(self.fixtures(bench=34,portfolio=34)); values[3]=port
            self.assertFalse(self.check(values)["data_ready"])
    def test_reconciler_input_failure_propagates_to_launch(self):
        values=self.fixtures(bench=34,portfolio=34); values[3]["inputs_healthy"]=False
        self.assertFalse(self.check(values)["data_ready"])
    def test_duplicate_or_wrong_family_is_not_coverage(self):
        values=self.fixtures(bench=34,portfolio=34)
        values[3]["families_detail"][1]=values[3]["families_detail"][0].copy()
        self.assertFalse(self.check(values)["data_ready"])
    def test_counts_above_universe_and_boolean_counts_are_rejected(self):
        for value in (35, True, "34", -1, None):
            values=self.fixtures(bench=34,portfolio=34); values[1]["counts"]["direct_ter"]=value
            self.assertFalse(self.check(values)["data_ready"])

if __name__ == "__main__": unittest.main()
