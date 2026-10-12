"""Source fetch telemetry must not leave orphan archives or mask root failures."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers


class FetchAuditAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def client(self, response=None, error=None):
        class Client:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def stream(self,*args,**kwargs):
                if error is not None:raise error
                return response
        return Client

    def test_success_audit_failure_rolls_back_new_archive(self):
        class Response:
            is_redirect=False
            headers={"content-type":"application/pdf"}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def raise_for_status(self):return None
            def iter_bytes(self):return iter((b"%PDF-1.7 source bytes",))

        with db.connect() as conn:
            conn.execute("""CREATE TRIGGER fail_ok_fetch BEFORE INSERT ON fetches
                            WHEN NEW.status='ok'
                            BEGIN SELECT RAISE(ABORT,'synthetic fetch audit failure'); END""")

        with patch("tracker.providers.public_url",side_effect=lambda url:url), \
             patch("tracker.providers._pinned_request_target",side_effect=lambda url,attempt=0:(url,{},{})), \
             patch("tracker.providers.httpx.Client",self.client(response=Response())):
            with self.assertRaisesRegex(sqlite3.Error,"synthetic fetch audit failure"):
                providers.fetch("https://example.com/factsheet.pdf")

        self.assertEqual(db.one("SELECT COUNT(*) n FROM archives")["n"],0)
        root=Path(self.tmp.name)/"archive"
        self.assertFalse(root.exists() and any(p.is_file() for p in root.rglob("*")))
        failure=db.one("SELECT status,detail FROM fetches ORDER BY id DESC LIMIT 1")
        self.assertEqual(failure["status"],"error")
        self.assertIn("synthetic fetch audit failure",failure["detail"])

    def test_failure_audit_error_does_not_mask_original_network_exception(self):
        with db.connect() as conn:
            conn.execute("""CREATE TRIGGER fail_error_fetch BEFORE INSERT ON fetches
                            WHEN NEW.status='error'
                            BEGIN SELECT RAISE(ABORT,'synthetic error-log failure'); END""")

        original=providers.httpx.ConnectError("original network failure")
        with patch("tracker.providers.public_url",side_effect=lambda url:url), \
             patch("tracker.providers._pinned_request_target",side_effect=lambda url,attempt=0:(url,{},{})), \
             patch("tracker.providers.httpx.Client",self.client(error=original)):
            with self.assertRaises(providers.httpx.ConnectError) as caught:
                providers.fetch("https://example.com/unreachable.pdf")

        self.assertIs(caught.exception,original)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM fetches")["n"],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM archives")["n"],0)


if __name__=="__main__":
    unittest.main()
