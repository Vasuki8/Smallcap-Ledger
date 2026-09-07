from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("SMALLCAP_DATA_DIR", ROOT / "data")).resolve()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATA / "ledger.sqlite3", timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def init(recover=False):
    with connect() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript('''
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS schemes(
          code INTEGER PRIMARY KEY, name TEXT NOT NULL, family TEXT NOT NULL,
          amc TEXT NOT NULL, plan TEXT NOT NULL, option TEXT NOT NULL,
          category TEXT NOT NULL DEFAULT 'small-cap', isin TEXT, reinvestment_isin TEXT,
          category_source TEXT NOT NULL, last_seen TEXT, history_checked TEXT,
          history_status TEXT, metadata_json TEXT NOT NULL DEFAULT '{}');
        CREATE INDEX IF NOT EXISTS idx_schemes_family ON schemes(family);
        CREATE TABLE IF NOT EXISTS nav(
          code INTEGER NOT NULL REFERENCES schemes(code), date TEXT NOT NULL,
          value REAL NOT NULL CHECK(value>0), source TEXT NOT NULL,
          observed_at TEXT NOT NULL, PRIMARY KEY(code,date));
        CREATE TABLE IF NOT EXISTS nav_observations(
          code INTEGER NOT NULL, date TEXT NOT NULL, value REAL NOT NULL,
          source TEXT NOT NULL, observed_at TEXT NOT NULL,
          UNIQUE(code,date,value,source));
        CREATE TABLE IF NOT EXISTS archives(
          hash TEXT PRIMARY KEY, path TEXT NOT NULL, bytes INTEGER NOT NULL,
          media_type TEXT, first_seen TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fetches(
          id INTEGER PRIMARY KEY, url TEXT NOT NULL, fetched_at TEXT NOT NULL,
          status TEXT NOT NULL, hash TEXT, detail TEXT);
        CREATE INDEX IF NOT EXISTS idx_fetches_url_time ON fetches(url,fetched_at);
        CREATE TABLE IF NOT EXISTS benchmark(
          name TEXT NOT NULL, date TEXT NOT NULL, value REAL NOT NULL CHECK(value>0),
          source TEXT NOT NULL, observed_at TEXT NOT NULL,
          PRIMARY KEY(name,date));
        CREATE TABLE IF NOT EXISTS benchmark_observations(
          name TEXT NOT NULL,date TEXT NOT NULL,value REAL NOT NULL,source TEXT NOT NULL,
          observed_at TEXT NOT NULL,UNIQUE(name,date,value,source));
        CREATE TABLE IF NOT EXISTS metrics(
          id INTEGER PRIMARY KEY, family TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'All',
          metric TEXT NOT NULL, as_of TEXT NOT NULL, value TEXT NOT NULL, unit TEXT,
          source TEXT NOT NULL, hash TEXT NOT NULL DEFAULT '', observed_at TEXT NOT NULL,
          UNIQUE(family,plan,metric,as_of,value,source));
        CREATE INDEX IF NOT EXISTS idx_metrics_family_metric_date ON metrics(family,metric,as_of);
        CREATE TABLE IF NOT EXISTS portfolios(
          id INTEGER PRIMARY KEY, family TEXT NOT NULL, as_of TEXT NOT NULL,
          complete INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL, hash TEXT NOT NULL,
          observed_at TEXT NOT NULL, UNIQUE(family,as_of,hash));
        CREATE INDEX IF NOT EXISTS idx_portfolios_family_date ON portfolios(family,as_of);
        CREATE TABLE IF NOT EXISTS holdings(
          id INTEGER PRIMARY KEY, snapshot_id INTEGER NOT NULL REFERENCES portfolios(id),
          isin TEXT, name TEXT NOT NULL, sector TEXT, weight REAL NOT NULL,
          asset_type TEXT NOT NULL DEFAULT 'Equity');
        CREATE INDEX IF NOT EXISTS idx_holdings_snapshot ON holdings(snapshot_id);
        CREATE TABLE IF NOT EXISTS documents(
          id INTEGER PRIMARY KEY, family TEXT NOT NULL, title TEXT NOT NULL,
          kind TEXT NOT NULL, scope TEXT NOT NULL, url TEXT NOT NULL,
          published_at TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
          origin TEXT NOT NULL, UNIQUE(family,url));
        CREATE TABLE IF NOT EXISTS document_versions(
          id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id),
          hash TEXT NOT NULL REFERENCES archives(hash), observed_at TEXT NOT NULL,
          UNIQUE(document_id,hash));
        CREATE INDEX IF NOT EXISTS idx_documents_family_seen ON documents(family,first_seen);
        CREATE TABLE IF NOT EXISTS source_pages(
          id INTEGER PRIMARY KEY, amc_match TEXT NOT NULL, url TEXT NOT NULL,
          label TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'disclosure', enabled INTEGER NOT NULL DEFAULT 1,
          last_checked TEXT, status TEXT NOT NULL DEFAULT 'Pending', detail TEXT,
          UNIQUE(amc_match,url));
        CREATE TABLE IF NOT EXISTS distribution_coverage(
          code INTEGER PRIMARY KEY REFERENCES schemes(code), start TEXT NOT NULL,
          end TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS distributions(
          code INTEGER NOT NULL REFERENCES schemes(code), ex_date TEXT NOT NULL,
          amount REAL NOT NULL CHECK(amount>=0), reinvestment_nav REAL NOT NULL CHECK(reinvestment_nav>0),
          source TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(code,ex_date));
        CREATE TABLE IF NOT EXISTS jobs(
          id INTEGER PRIMARY KEY, kind TEXT NOT NULL, started_at TEXT NOT NULL,
          finished_at TEXT, status TEXT NOT NULL, detail TEXT);
        ''')
        defaults = {"nav_interval_minutes": "60", "disclosure_interval_hours": "12", "auto_update": "true"}
        c.executemany("INSERT OR IGNORE INTO settings VALUES (?,?)", defaults.items())
        c.execute("DELETE FROM document_versions WHERE document_id IN (SELECT id FROM documents WHERE kind='news')")
        c.execute("DELETE FROM documents WHERE kind='news'")
        c.execute("DELETE FROM settings WHERE key='news_interval_hours'")
        if recover:
            c.execute("UPDATE jobs SET status='interrupted',finished_at=?,detail='Application stopped before this update finished; the next run resumes retained history.' WHERE status='running'", (now(),))


def rows(sql, params=()):
    with connect() as c:
        return [dict(x) for x in c.execute(sql, params)]


def one(sql, params=()):
    r = rows(sql, params)
    return r[0] if r else None


def setting(key, default=None):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return json.loads(r["value"]) if r else default


def archive(content: bytes, media_type: str = "application/octet-stream"):
    h = hashlib.sha256(content).hexdigest()
    target = DATA / "archive" / h[:2] / h
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(content)
        tmp.replace(target)
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO archives VALUES(?,?,?,?,?)", (h, str(target.relative_to(DATA)), len(content), media_type, now()))
    return h


def save_nav(code, points, source):
    timestamp = now()
    observations = [(code, date, float(value), source, timestamp) for date, value in points if float(value) > 0]
    with connect() as c:
        c.executemany("INSERT OR IGNORE INTO nav_observations VALUES(?,?,?,?,?)", observations)
        c.executemany('''INSERT INTO nav VALUES(?,?,?,?,?) ON CONFLICT(code,date) DO UPDATE SET
          value=excluded.value,source=excluded.source,observed_at=excluded.observed_at
          WHERE excluded.source LIKE '%amfiindia.com%' OR nav.source NOT LIKE '%amfiindia.com%' ''', observations)


def save_benchmark(name, points, source):
    records = [(name, day, float(value), source, now()) for day, value in points if float(value) > 0]
    with connect() as c:
        c.executemany("INSERT OR IGNORE INTO benchmark_observations VALUES(?,?,?,?,?)", records)
        c.executemany('''INSERT INTO benchmark VALUES(?,?,?,?,?) ON CONFLICT(name,date) DO UPDATE SET
          value=excluded.value,source=excluded.source,observed_at=excluded.observed_at''', records)


def metric(family, plan, name, as_of, value, unit, source, content_hash=""):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO metrics(family,plan,metric,as_of,value,unit,source,hash,observed_at) VALUES(?,?,?,?,?,?,?,?,?)",
                  (family, plan, name, as_of, str(value), unit, source, content_hash, now()))
