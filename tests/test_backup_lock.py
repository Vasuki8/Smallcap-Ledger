"""Backup creation must be serialized to avoid duplicate multi-GB temp archives."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker.app import app, backup, _backup_lock


class BackupLockTests(unittest.TestCase):
    def test_second_backup_request_is_rejected_while_one_is_active(self):
        client=TestClient(app)
        self.assertTrue(_backup_lock.acquire(blocking=False))
        try:
            response=client.post('/api/export/backup',headers={'X-Smallcap-Client':'local'})
            self.assertEqual(response.status_code,409)
            self.assertIn('already being created',response.json()['detail'])
        finally:
            _backup_lock.release()

    def test_backup_setup_failure_releases_lock(self):
        with patch('tracker.app.tempfile.mkdtemp',side_effect=OSError('disk unavailable')):
            with self.assertRaisesRegex(OSError,'disk unavailable'):
                backup()
        self.assertTrue(_backup_lock.acquire(blocking=False))
        _backup_lock.release()


if __name__=='__main__':
    unittest.main()
