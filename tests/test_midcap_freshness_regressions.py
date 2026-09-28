"""Source freshness, not summary generation, determines staged readiness."""
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from tracker.midcap_portfolio_readiness import reconcile

FAMILY = "Example Mid Cap Fund"
AMC = "Example Mutual Fund"
NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)

def evidence(day="2026-08-31", **changes):
    row = dict(family=FAMILY, amc=AMC, status="recovered", as_of=day,
               positions_observed=10, complete=False, source="https://example.com/portfolio.xlsx",
               source_sha256="a" * 64, workbook_sha256="b" * 64,
               observed_at="2026-09-27T12:00:00+00:00", sheet="MIDCAP",
               scope="structured_monthly_portfolio")
    return dict(row, **changes)

def batch(*rows):
    return dict(staged_category="mid-cap", built_at="2026-09-27T12:01:00+00:00",
                portfolio_expected_as_of="2026-08-31", results=list(rows), errors=[])

class FreshnessBugReproductions(unittest.TestCase):
    def test_older_complete_never_displaces_newer_partial(self):
        result = reconcile({FAMILY: AMC}, batch(evidence("2026-07-31", complete=True)), batch(evidence()), now=NOW)
        self.assertEqual(result["families_detail"][0]["as_of"], "2026-08-31")

    def test_stale_source_does_not_count_as_current(self):
        result = reconcile({FAMILY: AMC}, batch(evidence("2020-07-31", complete=True)), now=NOW)
        self.assertEqual(result["current_portfolio_evidence"], 0)
        self.assertEqual(result["current_complete_portfolios"], 0)

    def test_source_provenance_survives_reconciliation(self):
        row = evidence()
        result = reconcile({FAMILY: AMC}, batch(row), now=NOW)
        for key in ("source_sha256", "workbook_sha256", "observed_at", "sheet"):
            self.assertEqual(result["families_detail"][0].get(key), row[key])

class FreshnessBoundaryTests(unittest.TestCase):
    def report(self, row=None, **kwargs):
        return reconcile({FAMILY: AMC}, batch(row or evidence()), now=kwargs.pop("now", NOW), **kwargs)

    def test_same_date_completeness_remains_a_tie_breaker(self):
        r = reconcile({FAMILY: AMC}, batch(evidence(complete=True, positions_observed=5)),
                      batch(evidence(positions_observed=20)), now=NOW)
        self.assertTrue(r["families_detail"][0]["complete"])
        self.assertEqual(r["current_complete_portfolios"], 1)

    def test_stale_valid_row_is_preserved_with_reason(self):
        r = self.report(evidence("2026-07-31", complete=True))
        self.assertEqual(r["families_detail"][0]["as_of"], "2026-07-31")
        self.assertEqual(r["families_detail"][0]["freshness_status"], "stale")
        self.assertEqual(r["current_portfolio_evidence"], 0)

    def test_malformed_future_and_intramonth_dates_are_rejected(self):
        for day in (None, "", "20260831", "2026-02-30", "2026-09-30", "2026-08-15"):
            with self.subTest(day=day):
                r = self.report(evidence(day))
                self.assertEqual(r["current_portfolio_evidence"], 0)
                self.assertTrue(r["excluded_evidence"])
                self.assertFalse(r["inputs_healthy"])

    def test_wrong_identity_unsuccessful_and_invalid_count_are_rejected(self):
        for changes in ({"family":"Other Mid Cap Fund"}, {"amc":"Other AMC"}, {"status":"failed"},
                        {"positions_observed":0}, {"positions_observed":True}, {"positions_observed":1.5},
                        {"positions_observed":"10"}, {"complete":"true"}, {"source_sha256":None},
                        {"observed_at":"2026-09-29T12:00:00Z"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.report(evidence(**changes))["current_portfolio_evidence"], 0)

    def test_existing_ten_day_grace_is_unchanged(self):
        for day, expected, count in ((10,"2026-08-31",1), (11,"2026-09-30",0)):
            r = self.report(now=datetime(2026,10,day,tzinfo=timezone.utc))
            self.assertEqual(r["portfolio_expected_as_of"], expected)
            self.assertEqual(r["current_portfolio_evidence"], count)

    def test_newer_closed_month_is_current_during_grace(self):
        now = datetime(2026,10,5,tzinfo=timezone.utc)
        row = evidence("2026-09-30", observed_at="2026-10-02T00:00:00Z")
        b = batch(row); b["built_at"] = "2026-10-03T00:00:00Z"
        r = reconcile({FAMILY:AMC}, b, now=now)
        self.assertEqual(r["portfolio_expected_as_of"], "2026-08-31")
        self.assertEqual(r["current_portfolio_evidence"], 1)

    def test_year_rollover_and_leap_year(self):
        for now, expected in ((datetime(2027,1,10,tzinfo=timezone.utc),"2026-11-30"),
                              (datetime(2027,1,11,tzinfo=timezone.utc),"2026-12-31"),
                              (datetime(2028,3,11,tzinfo=timezone.utc),"2028-02-29")):
            row = evidence(expected, observed_at=now.isoformat()); b = batch(row); b["built_at"] = now.isoformat()
            r = reconcile({FAMILY:AMC}, b, now=now)
            self.assertEqual(r["portfolio_expected_as_of"], expected)
            self.assertEqual(r["current_portfolio_evidence"], 1)

    def test_current_run_failure_cannot_reuse_retained_batch(self):
        r = self.report(input_reports=[{"ok":False,"error":"not_generated_this_run"}])
        self.assertEqual(r["current_portfolio_evidence"], 0)
        self.assertFalse(r["inputs_healthy"])
        self.assertEqual(r["excluded_evidence"][0]["evidence"]["results"][0]["as_of"], "2026-08-31")

    def test_shape_errors_are_diagnostic_not_silent_success(self):
        for b in (None, [], {}, {"results":None}, {"results":[] ,"staged_category":"small-cap"}):
            with self.subTest(b=b):
                r = reconcile({FAMILY:AMC}, b, now=NOW)
                self.assertFalse(r["inputs_healthy"])
                self.assertEqual(r["current_portfolio_evidence"], 0)

    def test_inputs_and_original_source_observation_are_not_mutated(self):
        b = batch(evidence()); before = deepcopy(b)
        r = reconcile({FAMILY:AMC}, b, now=NOW)
        self.assertEqual(b, before)
        self.assertNotEqual(r["built_at"], r["families_detail"][0]["observed_at"])
        self.assertEqual(r["families_detail"][0]["observed_at"], b["results"][0]["observed_at"])
        self.assertFalse(r["public_export_enabled"])
        self.assertEqual(r["production_writes"],0)

    def test_empty_universe_is_not_a_zero_target_success(self):
        with self.assertRaises(ValueError):
            reconcile({}, batch(), now=NOW)

if __name__ == "__main__":
    unittest.main()
