"""Document crawl preflight failures must rotate instead of starving later links."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures


class DocumentAttemptRotationTests(unittest.TestCase):
    def test_preflight_failure_moves_target_behind_never_attempted_candidate(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            blocked="https://example.com/blocked.pdf"
            unseen="https://example.com/unseen.pdf"
            disclosures._record_preflight_failure(
                blocked,ValueError("robots policy disallows automatic access"))
            last={
                row["url"]:row["last"]
                for row in db.rows(
                    "SELECT url,MAX(fetched_at) last FROM fetches GROUP BY url")
            }
            ordered=sorted([blocked,unseen],key=lambda url:last.get(url,""))
            self.assertEqual(ordered,[unseen,blocked])
            row=db.one(
                "SELECT status,detail FROM fetches WHERE url=? ORDER BY id DESC LIMIT 1",
                (blocked,))
            self.assertEqual(row["status"],"error")
            self.assertIn("Preflight:",row["detail"])
            self.assertIn("robots policy",row["detail"])

    def test_both_bounded_document_loops_record_preflight_failures(self):
        source=(Path(__file__).resolve().parents[1]/"tracker"/"disclosures.py").read_text(
            encoding="utf-8")
        self.assertEqual(
            source.count("_record_preflight_failure(target,exc);errors+=1"),
            2,
        )


if __name__=="__main__":
    unittest.main()
