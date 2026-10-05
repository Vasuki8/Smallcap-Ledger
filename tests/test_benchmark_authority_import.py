"""Benchmark canonical authority must come from ingestion provenance, not a claimed URL."""
import csv
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db
from tracker.app import app


class BenchmarkAuthorityImportTests(unittest.TestCase):
    def test_import_claiming_official_url_cannot_replace_authoritative_value(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            name='Nifty Smallcap 250 TRI';day='2026-09-30'
            source='https://www.niftyindices.com/reports/historical-data'
            db.save_benchmark(name,[(day,12345.0)],source,authoritative=True)
            payload=f'date,value\n{day},99999\n'.encode()
            client=TestClient(app)
            with patch('tracker.providers.public_url',side_effect=lambda url:url):
                response=client.post(
                    '/api/import',
                    headers={'X-Smallcap-Client':'local'},
                    data={'kind':'benchmark','source':source,'benchmark':name},
                    files={'file':('benchmark.csv',payload,'text/csv')},
                )
            self.assertEqual(response.status_code,200,response.text)
            canonical=db.one(
                'SELECT value,source,authority FROM benchmark WHERE name=? AND date=?',
                (name,day))
            self.assertEqual(canonical,{'value':12345.0,'source':source,'authority':1})
            imported=db.one(
                'SELECT authority FROM benchmark_observations WHERE name=? AND date=? AND value=?',
                (name,day,99999.0))
            self.assertEqual(imported['authority'],0)

    def test_series_provenance_distinguishes_verified_user_and_mixed_history(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            verified='Verified TRI'
            db.save_benchmark(verified,[('2026-09-01',100),('2026-09-02',101)],
                              'https://index.example/tri',authoritative=True)
            self.assertEqual(db.benchmark_info(verified)['provenance_status'],'verified_collector')

            manual='Manual TRI'
            db.save_benchmark(manual,[('2026-09-01',200)],'https://example.com/manual.csv')
            self.assertEqual(db.benchmark_info(manual)['provenance_status'],'user_supplied')

            mixed='Mixed TRI'
            db.save_benchmark(mixed,[('2026-09-01',300)],'https://example.com/manual.csv')
            db.save_benchmark(mixed,[('2026-09-02',301)],'https://index.example/tri',authoritative=True)
            info=db.benchmark_info(mixed)
            self.assertEqual(info['provenance_status'],'mixed')
            self.assertEqual((info['authoritative_points'],info['points']),(1,2))

    def test_static_export_and_ui_surface_benchmark_provenance(self):
        root=Path(__file__).resolve().parents[1]
        export=(root/'scripts'/'export_site.py').read_text(encoding='utf-8')
        ui=(root/'dist'/'app.js').read_text(encoding='utf-8')
        self.assertIn("db.benchmark_info(row['name'])",export)
        self.assertIn('Verified collector',ui)
        self.assertIn('User-supplied',ui)
        self.assertIn('provenance_status',ui)

    def test_legacy_nifty_rows_are_promoted_only_for_completed_collector_years(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            Path(tmp).mkdir(parents=True,exist_ok=True)
            con=sqlite3.connect(Path(tmp)/'ledger.sqlite3')
            con.executescript('''
              CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
              CREATE TABLE benchmark(
                name TEXT NOT NULL,date TEXT NOT NULL,value REAL NOT NULL,
                source TEXT NOT NULL,observed_at TEXT NOT NULL,
                PRIMARY KEY(name,date)) WITHOUT ROWID;
              CREATE TABLE benchmark_observations(
                name TEXT NOT NULL,date TEXT NOT NULL,value REAL NOT NULL,source TEXT NOT NULL,
                observed_at TEXT NOT NULL,PRIMARY KEY(name,date,value,source)) WITHOUT ROWID;
            ''')
            source='https://www.niftyindices.com/reports/historical-data'
            con.execute("INSERT INTO settings VALUES('nifty_year_2025','true')")
            con.execute("INSERT INTO benchmark VALUES(?,?,?,?,?)",
                        ('Nifty Smallcap 250 TRI','2025-06-30',100,source,'2025-07-01T00:00:00+00:00'))
            con.execute("INSERT INTO benchmark VALUES(?,?,?,?,?)",
                        ('Nifty Smallcap 250 TRI','2024-06-30',90,source,'2024-07-01T00:00:00+00:00'))
            con.executemany("INSERT INTO benchmark_observations VALUES(?,?,?,?,?)",[
                ('Nifty Smallcap 250 TRI','2025-06-30',100,source,'2025-07-01T00:00:00+00:00'),
                ('Nifty Smallcap 250 TRI','2024-06-30',90,source,'2024-07-01T00:00:00+00:00'),
            ])
            con.commit();con.close()
            db.init()
            rows=db.rows("SELECT date,authority FROM benchmark ORDER BY date")
            self.assertEqual(rows,[{'date':'2024-06-30','authority':0},{'date':'2025-06-30','authority':1}])
            obs=db.rows("SELECT date,authority FROM benchmark_observations ORDER BY date")
            self.assertEqual(obs,[{'date':'2024-06-30','authority':0},{'date':'2025-06-30','authority':1}])


if __name__=='__main__':
    unittest.main()
