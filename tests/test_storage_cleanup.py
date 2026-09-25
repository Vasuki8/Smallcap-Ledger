from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from scripts import compact_database as storage


class StorageCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_data = db.DATA
        db.DATA = Path(self.tmp.name)
        db.init()
        # Explicitly build the old layout even after fresh databases use the
        # compact format. There are no time-series rows at this point.
        with db.connect() as c:
            for name, body in storage.BODIES.items():
                c.execute(f'DROP TABLE {name}')
                if name.endswith('_observations'):
                    body = body.replace('PRIMARY KEY', 'UNIQUE')
                c.execute(f'CREATE TABLE {name} ({body})')
            c.execute('''INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                         VALUES(1,'Small Cap Direct Growth','Small Cap','Example AMC','Direct','Growth','official')''')
        db.save_nav(1, [('2026-09-01', 10.0), ('2026-09-02', 10.5)], 'https://www.amfiindia.com/nav')
        db.save_nav(1, [('2026-09-01', 11.0)], 'https://www.amfiindia.com/nav')
        db.save_benchmark('TRI', [('2026-09-01', 1000)], 'https://example.test/official')
        db.save_benchmark('TRI', [('2026-09-01', 1001)], 'https://example.test/official')
        h = db.archive(b'original AMC evidence', 'text/plain')
        db.metric('Small Cap', 'All', 'aum', '2026-08-31', 123, 'crore', 'official', h)

    def tearDown(self):
        db.DATA = self.previous_data
        self.tmp.cleanup()

    def fingerprints(self):
        with db.connect() as c:
            return storage.table_fingerprints(c)

    def planned(self):
        with db.connect() as c:
            return storage.schema_plan(c)

    def test_dry_run_does_not_change_records_or_schema(self):
        before = self.fingerprints()
        report = storage.compact_database()
        self.assertFalse(report['applied'])
        self.assertEqual(report['tables_changed'], [])
        self.assertEqual(len(report['tables_planned']), 4)
        self.assertEqual(self.fingerprints(), before)
        self.assertEqual(len(self.planned()), 4)

    def test_every_table_row_and_original_remains_unchanged(self):
        before = self.fingerprints()
        originals = {p.relative_to(db.DATA): p.read_bytes() for p in (db.DATA / 'archive').rglob('*') if p.is_file()}
        report = storage.compact_database(True)
        self.assertEqual(report['rows_deleted'], 0)
        self.assertTrue(report['all_logical_rows_unchanged'])
        self.assertEqual(report['preserved_tables'], before)
        self.assertEqual(self.fingerprints(), before)
        self.assertEqual(self.planned(), [])
        self.assertEqual(report['integrity'], 'ok')
        for path, content in originals.items():
            self.assertEqual((db.DATA / path).read_bytes(), content)

    def test_rerun_is_idempotent(self):
        storage.compact_database(True)
        before = self.fingerprints()
        report = storage.compact_database(True)
        self.assertEqual(report['tables_changed'], [])
        self.assertEqual(report['bytes_saved'], 0)
        self.assertEqual(self.fingerprints(), before)

    def test_nav_and_benchmark_correction_history_survives(self):
        storage.compact_database(True)
        self.assertEqual([r['value'] for r in db.rows('SELECT value FROM nav_observations WHERE date=? ORDER BY value', ('2026-09-01',))], [10, 11])
        self.assertEqual([r['value'] for r in db.rows('SELECT value FROM benchmark_observations ORDER BY value')], [1000, 1001])
        self.assertEqual(db.one('SELECT value FROM nav WHERE date=?', ('2026-09-01',))['value'], 11)

    def test_new_upserts_and_duplicate_observations_still_work(self):
        storage.compact_database(True)
        for _ in range(2):
            db.save_nav(1, [('2026-09-01', 12)], 'https://www.amfiindia.com/nav')
            db.save_benchmark('TRI', [('2026-09-01', 1002)], 'https://example.test/official')
        self.assertEqual(db.one('SELECT value FROM nav WHERE date=?', ('2026-09-01',))['value'], 12)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM nav_observations WHERE date=?', ('2026-09-01',))['n'], 3)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM benchmark_observations')['n'], 3)

    def test_positive_value_constraint_remains(self):
        storage.compact_database(True)
        with self.assertRaises(sqlite3.IntegrityError):
            with db.connect() as c:
                c.execute("INSERT INTO nav VALUES(1,'2026-09-03',0,'official','now')")

    def test_foreign_key_constraint_remains(self):
        storage.compact_database(True)
        with self.assertRaises(sqlite3.IntegrityError):
            with db.connect() as c:
                c.execute("INSERT INTO nav VALUES(999,'2026-09-03',12,'official','now')")

    def test_late_fingerprint_failure_rolls_back_all_tables(self):
        before = self.fingerprints()
        with patch.object(storage, 'table_fingerprints', side_effect=[before, {}]):
            with self.assertRaisesRegex(ValueError, 'Logical database content changed'):
                storage.compact_database(True)
        self.assertEqual(self.fingerprints(), before)
        self.assertEqual(len(self.planned()), 4)
        self.assertEqual(db.rows("SELECT name FROM sqlite_master WHERE name LIKE '_storage_v1_%'"), [])

    def test_unknown_schema_is_rejected_without_changes(self):
        with db.connect() as c:
            c.execute('ALTER TABLE nav ADD COLUMN future_feature TEXT')
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, 'Unexpected schema'):
            storage.compact_database(True)
        self.assertEqual(self.fingerprints(), before)

    def test_custom_index_is_not_silently_removed(self):
        with db.connect() as c:
            c.execute('CREATE INDEX custom_nav_source ON nav(source)')
        with self.assertRaisesRegex(ValueError, 'Custom indexes/triggers'):
            storage.compact_database(True)
        self.assertIsNotNone(db.one("SELECT name FROM sqlite_master WHERE name='custom_nav_source'"))

    def test_custom_trigger_is_not_silently_removed(self):
        with db.connect() as c:
            c.execute('CREATE TRIGGER custom_nav AFTER INSERT ON nav BEGIN SELECT 1; END')
        with self.assertRaisesRegex(ValueError, 'Custom indexes/triggers'):
            storage.compact_database(True)
        self.assertIsNotNone(db.one("SELECT name FROM sqlite_master WHERE name='custom_nav'"))

    def test_incoming_foreign_key_is_rejected(self):
        with db.connect() as c:
            c.execute('CREATE TABLE future_reference(code INTEGER,date TEXT,FOREIGN KEY(code,date) REFERENCES nav(code,date))')
        with self.assertRaisesRegex(ValueError, 'Incoming foreign key'):
            storage.compact_database(True)

    def test_dependent_view_is_rejected(self):
        with db.connect() as c:
            c.execute('CREATE VIEW future_view AS SELECT * FROM nav')
        with self.assertRaisesRegex(ValueError, 'Dependent view'):
            storage.compact_database(True)

    def test_existing_foreign_key_violation_is_rejected(self):
        with sqlite3.connect(db.DATA / 'ledger.sqlite3') as c:
            c.execute("INSERT INTO nav VALUES(999,'2026-09-03',12,'official','now')")
        with self.assertRaisesRegex(ValueError, 'foreign-key violations before'):
            storage.compact_database(True)
        self.assertEqual(len(self.planned()), 4)


if __name__ == '__main__':
    unittest.main()
