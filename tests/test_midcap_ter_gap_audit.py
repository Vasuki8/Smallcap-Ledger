"""Regression tests for Mid Cap TER gap classification."""
import unittest

from tracker.midcap_ter_gap_audit import classify


class MidCapTerGapClassificationTests(unittest.TestCase):
    def test_zero_rows_across_exact_amc_category_is_classified(self):
        source={
            "built_at":"2026-09-27T00:00:00+00:00",
            "source_errors":[],
            "families":[{
                "family":"Example Mid Cap Fund","amc":"Example AMC",
                "direct_ter_available":False,
            }],
            "source_checks":[
                {"kind":"ter_mid_cap_contract_summary","category_id":"17",
                 "category_label":"Equity Scheme - Mid Cap Fund"},
                {"kind":"ter_mid_cap_by_amc","amc":"Example AMC","month":"09-2026",
                 "pages_checked":[{"rows":0,"mid_cap_rows":0}],"matched_families":[]},
                {"kind":"ter_mid_cap_by_amc","amc":"Example AMC","month":"08-2026",
                 "pages_checked":[{"rows":0,"mid_cap_rows":0}],"matched_families":[]},
                {"kind":"ter_mid_cap_by_amc","amc":"Example AMC","month":"07-2026",
                 "pages_checked":[{"rows":0,"mid_cap_rows":0}],"matched_families":[]},
            ],
        }
        result=classify(source)
        self.assertEqual(result["gap_families"],1)
        row=result["families"][0]
        self.assertEqual(row["classification"],"amfi_exact_amc_category_no_rows")
        self.assertEqual(row["next_action"],"seek_exact_first_party_amc_ter")
        self.assertEqual(row["months_checked"],["09-2026","08-2026","07-2026"])
        self.assertEqual(result["official_ter_category_selector"]["category_id"],"17")
        self.assertEqual(result["production_writes"],0)
        self.assertFalse(result["public_export_enabled"])

    def test_existing_direct_ter_is_not_a_gap(self):
        source={
            "families":[{
                "family":"Covered Mid Cap Fund","amc":"Example AMC",
                "direct_ter_available":True,
            }],
            "source_checks":[],
            "source_errors":[],
        }
        result=classify(source)
        self.assertEqual(result["gap_families"],0)
        self.assertEqual(result["families"],[])

    def test_midcap_rows_without_exact_family_are_identity_review(self):
        source={
            "source_errors":[],
            "families":[{
                "family":"Renamed Mid Cap Fund","amc":"Example AMC",
                "direct_ter_available":False,
            }],
            "source_checks":[{
                "kind":"ter_mid_cap_by_amc","amc":"Example AMC","month":"09-2026",
                "pages_checked":[{"rows":3,"mid_cap_rows":3}],"matched_families":[],
            }],
        }
        result=classify(source)
        self.assertEqual(result["families"][0]["classification"],
                         "amfi_midcap_rows_identity_unmatched")


if __name__=="__main__":
    unittest.main()
