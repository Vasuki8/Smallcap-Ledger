"""Import provenance URL boundary regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db
from tracker.app import app


class ImportSourceURLBoundaryTests(unittest.TestCase):
    def client(self,tmp):
        db.init()
        with db.connect() as c:
            c.execute(
                'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                (881,'URL Small Cap Direct Growth','URL Small Cap Fund','URL AMC','Direct','Growth','test'))
        return TestClient(app)

    def valid_metric_file(self):
        return {'file':('metrics.csv',b'metric,plan,as_of,value\naum,All,2026-09-30,1000\n','text/csv')}

    def test_private_network_source_url_is_rejected_without_archive(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            client=self.client(tmp)
            response=client.post(
                '/api/import',
                headers={'X-Smallcap-Client':'local'},
                data={'kind':'metrics','code':'881','source':'http://127.0.0.1/private.csv'},
                files=self.valid_metric_file(),
            )
            self.assertEqual(response.status_code,400)
            self.assertIn('public source URL',response.json()['detail'])
            self.assertEqual(db.one('SELECT COUNT(*) n FROM archives')['n'],0)

    def test_credential_bearing_source_url_is_rejected_without_archive(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            client=self.client(tmp)
            response=client.post(
                '/api/import',
                headers={'X-Smallcap-Client':'local'},
                data={'kind':'metrics','code':'881','source':'https://user:secret@example.com/source.csv'},
                files=self.valid_metric_file(),
            )
            self.assertEqual(response.status_code,400)
            self.assertIn('public source URL',response.json()['detail'])
            self.assertEqual(db.one('SELECT COUNT(*) n FROM archives')['n'],0)


if __name__=='__main__':
    unittest.main()
