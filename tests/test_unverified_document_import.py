"""Unverified document uploads must not promote source bytes into structured fund data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db
from tracker.app import app


class UnverifiedDocumentImportTests(unittest.TestCase):
    def test_document_upload_is_archived_but_never_auto_parsed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (99001,'Upload Small Cap Direct Growth','Upload Small Cap Fund','Upload AMC','Direct','Growth','test'))
            client=TestClient(app)
            with patch('tracker.app.providers.public_url',side_effect=lambda url:url), \
                 patch('tracker.app.disclosures.summary_xml') as xml, \
                 patch('tracker.app.disclosures.spreadsheet') as sheet, \
                 patch('tracker.app.disclosures.factsheet_pdf') as pdf:
                response=client.post(
                    '/api/import',
                    headers={'X-Smallcap-Client':'local'},
                    data={
                        'kind':'document','code':'99001','source':'https://example.com/factsheet.xlsx',
                        'title':'Owner supplied factsheet','document_kind':'factsheet','scope':'Fund',
                    },
                    files={'file':('factsheet.xlsx',b'PK-not-a-real-workbook','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
                )
            self.assertEqual(response.status_code,200,response.text)
            self.assertIn('not promoted automatically',response.json()['note'])
            xml.assert_not_called();sheet.assert_not_called();pdf.assert_not_called()
            self.assertEqual(db.one("SELECT COUNT(*) n FROM documents WHERE family='Upload Small Cap Fund'")['n'],1)
            self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions')['n'],1)
            self.assertEqual(db.one("SELECT COUNT(*) n FROM metrics WHERE family='Upload Small Cap Fund'")['n'],0)
            self.assertEqual(db.one("SELECT COUNT(*) n FROM portfolios WHERE family='Upload Small Cap Fund'")['n'],0)

    def test_ui_explains_document_uploads_are_not_structured_imports(self):
        source=(Path(__file__).resolve().parents[1]/'dist'/'app.js').read_text(encoding='utf-8')
        self.assertIn('user-supplied, unverified evidence',source)
        self.assertIn('not promoted automatically into structured figures or holdings',source)


if __name__=='__main__':
    unittest.main()
