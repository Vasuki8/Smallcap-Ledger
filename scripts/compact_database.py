"""Remove redundant SQLite indexing without removing any logical database rows.

Default is a read-only plan. --apply requires all-table content equality, database
integrity and foreign-key checks. The production publisher retains its previous
checkpoint as the rollback copy. No source archive or release asset is deleted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker import db

BODIES = {
    'nav': '''code INTEGER NOT NULL REFERENCES schemes(code), date TEXT NOT NULL,
        value REAL NOT NULL CHECK(value>0), source TEXT NOT NULL,
        observed_at TEXT NOT NULL, PRIMARY KEY(code,date)''',
    'nav_observations': '''code INTEGER NOT NULL, date TEXT NOT NULL, value REAL NOT NULL,
        source TEXT NOT NULL, observed_at TEXT NOT NULL,
        PRIMARY KEY(code,date,value,source)''',
    'benchmark': '''name TEXT NOT NULL, date TEXT NOT NULL,
        value REAL NOT NULL CHECK(value>0), source TEXT NOT NULL,
        observed_at TEXT NOT NULL, PRIMARY KEY(name,date)''',
    'benchmark_observations': '''name TEXT NOT NULL,date TEXT NOT NULL,value REAL NOT NULL,
        source TEXT NOT NULL, observed_at TEXT NOT NULL,
        PRIMARY KEY(name,date,value,source)''',
}


def canonical(sql):
    return re.sub(r'[\s"`\[\];]', '', sql).lower().replace('ifnotexists', '')


def table_fingerprints(connection):
    """Fingerprint all logical columns, including correction history and dates."""
    result = {}
    names = [r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for name in names:
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in connection.execute(f'PRAGMA table_info({quoted})')]
        order = ','.join('"' + x.replace('"', '""') + '"' for x in columns)
        digest = hashlib.sha256()
        count = 0
        for row in connection.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
            digest.update((repr(tuple(row)) + '\n').encode('utf-8'))
            count += 1
        result[name] = {'rows': count, 'sha256': digest.hexdigest()}
    return result


def schema_plan(connection):
    changes = []
    for name, body in BODIES.items():
        row = connection.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?',
                                 ('table', name)).fetchone()
        if not row:
            raise ValueError('Missing time-series table: ' + name)
        desired = f'CREATE TABLE {name} ({body}) WITHOUT ROWID'
        legacy_body = body.replace('PRIMARY KEY', 'UNIQUE') if name.endswith('_observations') else body
        legacy = f'CREATE TABLE {name} ({legacy_body})'
        if canonical(row[0]) == canonical(desired):
            continue
        if canonical(row[0]) != canonical(legacy):
            raise ValueError('Unexpected schema; refusing to rewrite ' + name)
        if connection.execute('SELECT 1 FROM sqlite_master WHERE tbl_name=? AND type IN (?,?) AND sql IS NOT NULL',
                              (name, 'index', 'trigger')).fetchone():
            raise ValueError('Custom indexes/triggers need explicit migration: ' + name)
        for other, in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            quoted = '"' + other.replace('"', '""') + '"'
            if any(r[2] == name for r in connection.execute(f'PRAGMA foreign_key_list({quoted})')):
                raise ValueError('Incoming foreign key needs explicit migration: ' + name)
        for view, sql in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='view'"):
            if re.search(r'\b' + re.escape(name) + r'\b', sql or '', re.I):
                raise ValueError('Dependent view needs explicit migration: ' + view)
        changes.append(name)
    return changes


def compact_database(apply=False):
    path = db.DATA / 'ledger.sqlite3'
    if not path.is_file():
        raise ValueError('Restore or initialise a database before running compaction')
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        changes = schema_plan(c)
        before_bytes = c.execute('PRAGMA page_count').fetchone()[0] * c.execute('PRAGMA page_size').fetchone()[0]
        report = {'operation': 'lossless-time-series-layout-v1', 'applied': apply,
                  'tables_changed': changes if apply else [], 'tables_planned': changes,
                  'before_bytes': before_bytes, 'after_bytes': before_bytes,
                  'bytes_saved': 0, 'rows_deleted': 0}
        if not apply:
            return report
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database failed integrity check before maintenance')
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Database has foreign-key violations before maintenance')
        before = table_fingerprints(c)
        for name in changes:
            temporary = '_storage_v1_' + name
            c.execute(f'CREATE TABLE {temporary} ({BODIES[name]}) WITHOUT ROWID')
            c.execute(f'INSERT INTO {temporary} SELECT * FROM {name}')
            old_count = c.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            if c.execute(f'SELECT COUNT(*) FROM {temporary}').fetchone()[0] != old_count:
                raise ValueError('Row count changed while copying ' + name)
            c.execute(f'DROP TABLE {name}')
            c.execute(f'ALTER TABLE {temporary} RENAME TO {name}')
        after = table_fingerprints(c)
        if before != after:
            raise ValueError('Logical database content changed; rolling back compaction')
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Foreign-key validation failed; rolling back compaction')
        report['preserved_tables'] = after
        report['all_logical_rows_unchanged'] = True
    # Physical space reclamation occurs only after the verified transaction.
    with db.connect() as c:
        if changes or c.execute('PRAGMA freelist_count').fetchone()[0]:
            c.execute('VACUUM')
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database failed integrity check after compaction')
        report['after_bytes'] = c.execute('PRAGMA page_count').fetchone()[0] * c.execute('PRAGMA page_size').fetchone()[0]
        report['bytes_saved'] = before_bytes - report['after_bytes']
        report['integrity'] = 'ok'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = compact_database(args.apply)
    if args.report and (not args.report.exists() or result['tables_changed']):
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
