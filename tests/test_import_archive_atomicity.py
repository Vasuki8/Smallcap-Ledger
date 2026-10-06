"""Rejected CSV imports must not retain archive evidence or partial structured rows."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db
from tracker.app import app


class ImportArchiveAtomicityTests(unittest.TestCase):
    def test_rejected_cross_scheme_document_leaves_no_archive_or_document_row(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (771,'Axis Small Cap Direct Growth','Axis Small Cap Fund','Axis Mutual Fund','Direct','Growth','test'))
            client=TestClient(app)
            before_archives=db.one('SELECT COUNT(*) n FROM archives')['n']
            before_documents=db.one('SELECT COUNT(*) n FROM documents')['n']
            wrong_url=(
                'https://www.axismf.com/mutual-fund-knowledge-centre/articles/'
                'everything-you-need-to-know-about-axis-greater-china-fund-of-fund'
            )
            response=client.post(
                '/api/import',
                headers={'X-Smallcap-Client':'local'},
                data={
                    'kind':'document','code':'771','source':wrong_url,
                    'title':'Axis Greater China Equity Fund of Fund: Making Sense...',
                    'document_kind':'market view','scope':'AMC',
                },
                files={'file':('axis-greater-china.pdf',b'%PDF-1.7 unrelated scheme','application/pdf')},
            )
            self.assertEqual(response.status_code,400)
            self.assertIn('Greater China',response.text)
            self.assertEqual(db.one('SELECT COUNT(*) n FROM documents')['n'],before_documents)
            self.assertEqual(db.one('SELECT COUNT(*) n FROM archives')['n'],before_archives)
            self.assertFalse((Path(tmp)/'archive').exists() and any((Path(tmp)/'archive').rglob('*')))

    def test_rejected_metrics_import_leaves_no_archive_or_metric_rows(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (772,'Atomic Small Cap Direct Growth','Atomic Small Cap Fund','Atomic AMC','Direct','Growth','test'))
            client=TestClient(app)
            before_archives=db.one('SELECT COUNT(*) n FROM archives')['n']
            before_metrics=db.one('SELECT COUNT(*) n FROM metrics')['n']
            payload=(
                b'metric,plan,as_of,value\n'
                b'aum,All,2026-09-30,150\n'
                b'ter,Direct,2026-09-30,650\n'
            )
            response=client.post(
                '/api/import',
                headers={'X-Smallcap-Client':'local'},
                data={'kind':'metrics','code':'772','source':'https://example.com/rejected.csv'},
                files={'file':('rejected.csv',payload,'text/csv')},
            )
            self.assertEqual(response.status_code,400)
            self.assertEqual(db.one('SELECT COUNT(*) n FROM metrics')['n'],before_metrics)
            self.assertEqual(db.one('SELECT COUNT(*) n FROM archives')['n'],before_archives)
            self.assertFalse((Path(tmp)/'archive').exists() and any((Path(tmp)/'archive').rglob('*')))


if __name__=='__main__':
    unittest.main()
