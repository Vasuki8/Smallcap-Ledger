"""Benchmark canonical-source precedence regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db


class BenchmarkPrecedenceTests(unittest.TestCase):
    def isolated(self):
        return tempfile.TemporaryDirectory()

    def test_manual_import_cannot_replace_official_index_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-30'
            official='https://www.niftyindices.com/reports/historical-data'
            manual='https://example.com/imported-index.csv'
            db.save_benchmark(name,[(day,12345.0)],official,authoritative=True)
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
            db.save_benchmark(name,[(day,222.0)],official,authoritative=True)
            canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],222.0)
            self.assertEqual(canonical['source'],official)

    def test_manual_import_cannot_gain_authority_by_claiming_official_url(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-27'
            official='https://www.niftyindices.com/reports/historical-data'
            db.save_benchmark(name,[(day,500.0)],official,authoritative=True)
            db.save_benchmark(name,[(day,999.0)],official)
            canonical=db.one("SELECT value,source,authority FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(canonical['value'],500.0)
            self.assertEqual(canonical['source'],official)
            self.assertEqual(canonical['authority'],1)
            observations=db.rows(
                "SELECT value,source,authority FROM benchmark_observations WHERE name=? AND date=? ORDER BY value",
                (name,day))
            self.assertEqual([(x['value'],x['authority']) for x in observations],[(500.0,1),(999.0,0)])

    def test_authoritative_collection_can_replace_same_url_manual_value(self):
        with self.isolated() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-26'
            source='https://www.niftyindices.com/reports/historical-data'
            db.save_benchmark(name,[(day,111.0)],source)
            before=db.one("SELECT value,authority FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(before,{'value':111.0,'authority':0})
            db.save_benchmark(name,[(day,222.0)],source,authoritative=True)
            after=db.one("SELECT value,authority FROM benchmark WHERE name=? AND date=?",(name,day))
            self.assertEqual(after,{'value':222.0,'authority':1})

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
