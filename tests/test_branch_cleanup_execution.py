import unittest

from scripts.delete_audited_branches import plan_cleanup


class BranchCleanupExecutionTests(unittest.TestCase):
    def audit(self):
        return {
            "high_confidence_candidates": [
                {"branch": "merged/a", "tip_sha": "a" * 40},
                {"branch": "merged/b", "tip_sha": "b" * 40},
                {"branch": "merged/c", "tip_sha": "c" * 40},
                {"branch": "merged/d", "tip_sha": "d" * 40},
            ]
        }

    def test_only_exact_current_tip_matches_are_eligible(self):
        plan = plan_cleanup(
            self.audit(),
            {
                "merged/a": "a" * 40,
                "merged/b": "9" * 40,
                "merged/d": "d" * 40,
            },
            {"merged/d"},
            expected_count=4,
        )
        self.assertEqual(plan["delete"], [{"branch": "merged/a", "tip_sha": "a" * 40}])
        self.assertEqual(plan["missing"], ["merged/c"])
        self.assertEqual(plan["open_pr"], ["merged/d"])
        self.assertEqual(plan["moved"], [{
            "branch": "merged/b",
            "audited_sha": "b" * 40,
            "current_sha": "9" * 40,
        }])

    def test_main_is_never_eligible(self):
        audit = {"high_confidence_candidates": [{"branch": "main", "tip_sha": "a" * 40}]}
        with self.assertRaisesRegex(ValueError, "main can never"):
            plan_cleanup(audit, {"main": "a" * 40}, set(), expected_count=1)

    def test_expected_candidate_count_is_required(self):
        with self.assertRaisesRegex(ValueError, "Expected 299"):
            plan_cleanup(self.audit(), {}, set(), expected_count=299)

    def test_duplicate_branch_is_rejected(self):
        audit = {
            "high_confidence_candidates": [
                {"branch": "merged/a", "tip_sha": "a" * 40},
                {"branch": "merged/a", "tip_sha": "a" * 40},
            ]
        }
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            plan_cleanup(audit, {"merged/a": "a" * 40}, set(), expected_count=2)


if __name__ == "__main__":
    unittest.main()
