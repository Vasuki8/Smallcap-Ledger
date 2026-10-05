"""Custom source pages must not expand the reviewed AMC publication trust boundary."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures


class CustomSourceTrustBoundaryTests(unittest.TestCase):
    def test_owner_added_source_does_not_make_domain_official(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    "INSERT INTO source_pages(amc_match,url,label) VALUES(?,?,?)",
                    ('HDFC','https://third-party.example/hdfc','Owner-added page'))
            self.assertFalse(disclosures.official_publication_url(
                'https://third-party.example/hdfc/factsheet.pdf','HDFC'))
            self.assertTrue(disclosures.official_publication_url(
                'https://files.hdfcfund.com/factsheet.pdf','HDFC'))


if __name__=='__main__':
    unittest.main()
