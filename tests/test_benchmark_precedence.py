"""Benchmark canonical-source precedence regressions."""
import os
import tempfile
import unittest
from pathlib import Path

_temp=tempfile.TemporaryDirectory()
os.environ['SMALLCAP_DATA_DIR']=_temp.name
os.environ['SMALLCAP_NO_SCHEDULER']='1'

from tracker import db

db.DATA=Path(_temp.name)


class BenchmarkPrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()

    def setUp(self):
        with db.connect() as c:
            c.execute("DELETE FROM benchmark")
            c.execute("DELETE FROM benchmark_observations")

    def test_manual_import_cannot_replace_official_index_value(self):
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
        name='Nifty Smallcap 250 TRI';day='2026-09-29'
        manual='https://example.com/imported-index.csv'
        official='https://www.niftyindices.com/reports/historical-data'
        db.save_benchmark(name,[(day,111.0)],manual)
        db.save_benchmark(name,[(day,222.0)],official)
        canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
        self.assertEqual(canonical['value'],222.0)
        self.assertEqual(canonical['source'],official)

    def test_same_manual_source_can_correct_its_own_value(self):
        name='BSE 250 SmallCap TRI';day='2026-09-28'
        source='https://example.com/bse-tri.csv'
        db.save_benchmark(name,[(day,300.0)],source)
        db.save_benchmark(name,[(day,301.5)],source)
        canonical=db.one("SELECT value,source FROM benchmark WHERE name=? AND date=?",(name,day))
        self.assertEqual(canonical['value'],301.5)
        self.assertEqual(canonical['source'],source)


if __name__=='__main__':
    unittest.main()
