import unittest

from tracker.publication_provenance import (
    PublicationBaseMoved,
    assert_publication_base,
    normalize_sha,
)


class PublicationProvenanceTests(unittest.TestCase):
    def test_exact_tested_parent_and_remote_main_are_accepted(self):
        sha = "a" * 40
        assert_publication_base(sha, sha, sha)

    def test_remote_main_movement_is_rejected(self):
        with self.assertRaisesRegex(PublicationBaseMoved, "main moved"):
            assert_publication_base("a" * 40, "a" * 40, "b" * 40)

    def test_generated_commit_with_wrong_parent_is_rejected(self):
        with self.assertRaisesRegex(PublicationBaseMoved, "does not match tested revision"):
            assert_publication_base("a" * 40, "b" * 40, "a" * 40)

    def test_invalid_sha_is_rejected(self):
        for value in ("", "main", "abc123", "g" * 40):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_sha(value)

    def test_sha_normalization_is_case_insensitive(self):
        self.assertEqual(normalize_sha("A" * 40), "a" * 40)


if __name__ == "__main__":
    unittest.main()
