"""Benchmark canonical-source precedence regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db
from tracker.app import app


class BenchmarkPrecedenceTests(unittest.TestCase):
    def isolated(self):
        return tempfile.TemporaryDirectory()

    def test_manual_import_cannot_replace_official_index_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-30'
            official='https://www.niftyindices.com/reports/historical-data'
            manual='https://example.com/imported-index.csv'
            db.save_benchmark(name,[(day,12345.0)],official)
            db.save_benchmark(name,[(day,99999.0)],manual)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],12345.0)
            self.assertEqual(canonical['source'],official)
            observations=db.rows("SELECT value,source FROM benchmark_observations WHERE name=? AND date=?",(name,day))
            self.assertEqual({(row['value'],row['source']) for row in observations},
                             {(12345.0,official),(99999.0,manual)})

    def test_official_provider_can_replace_manual_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-29'
            manual='https://example.com/imported-index.csv'
            official='https://www.niftyindices.com/reports/historical-data'
            db.save_benchmark(name,[(day,111.0)],manual)
            db.save_benchmark(name,[(day,222.0)],official)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],222.0)
            self.assertEqual(canonical['source'],official)

    def test_non_authoritative_observation_can_fill_a_missing_date(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='BSE 250 SmallCap TRI';day='2026-09-27'
            source='https://www.bseindices.com/indices/IndexArchiveData.html'
            db.save_benchmark(name,[(day,456.0)],source,authoritative=False)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],456.0)
            self.assertEqual(canonical['source'],source)

    def test_import_claiming_official_url_cannot_replace_existing_canonical_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)), \
             patch('tracker.app.providers.public_url',side_effect=lambda url:url):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-30'
            official='https://www.niftyindices.com/reports/historical-data'
            db.save_benchmark(name,[(day,12345.0)],official)
            client=TestClient(app)
            response=client.post(
                '/api/import',
                headers={'X-Smallcap-Client':'local'},
                data={'kind':'benchmark','source':official,'benchmark':name},
                files={'file':('fake.csv',f'date,value\n{day},99999\n'.encode(),'text/csv')},
            )
            self.assertEqual(response.status_code,200,response.text)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],12345.0)
            self.assertEqual(canonical['source'],official)
            observations=db.rows("SELECT value,source FROM benchmark_observations WHERE name=? AND date=?",(name,day))
            self.assertIn((99999.0,official),{(row['value'],row['source']) for row in observations})

    def test_same_manual_source_can_correct_its_own_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='BSE 250 SmallCap TRI';day='2026-09-28'
            source='https://example.com/bse-tri.csv'
            db.save_benchmark(name,[(day,300.0)],source)
            db.save_benchmark(name,[(day,301.5)],source)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],301.5)
            self.assertEqual(canonical['source'],source)


if __name__=='__main__':
    unittest.main()
