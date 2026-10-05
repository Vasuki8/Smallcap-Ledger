"""Public/private document provenance boundary regressions."""
from pathlib import Path
import unittest

from scripts import export_site


ROOT=Path(__file__).resolve().parents[1]


class UserImportPublicationBoundaryTests(unittest.TestCase):
    def test_public_export_keeps_only_verified_amc_documents(self):
        rows=[
            {'id':1,'origin':'AMC','kind':'factsheet'},
            {'id':2,'origin':'User import · unverified source','kind':'factsheet'},
            {'id':3,'origin':'Third party','kind':'market view'},
        ]
        self.assertEqual(export_site.public_documents(rows),[rows[0]])

    def test_imported_documents_are_labeled_unverified_locally(self):
        app=(ROOT/'tracker'/'app.py').read_text(encoding='utf-8')
        research=(ROOT/'dist'/'research.js').read_text(encoding='utf-8')
        validator=(ROOT/'scripts'/'validate_site.py').read_text(encoding='utf-8')
        self.assertIn("origin='User import · unverified source'",app)
        self.assertIn('User-supplied · unverified',research)
        self.assertIn("d['origin']=='AMC'",validator)
        self.assertNotIn("d['origin'].startswith('User import')",validator)


if __name__=='__main__':
    unittest.main()
