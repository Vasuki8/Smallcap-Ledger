"""One-time ICICI Prudential Small Cap complete-portfolio recovery.

The live AMC downloads API exposes exact month-end ZIP identities. Recovery
keeps the current and immediately previous complete snapshots and then leaves
nightly discovery responsible for subsequent months.
"""
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import amc_discovery, db, disclosures
from tracker.icici_portfolios import FAMILY, PARSER_VERSION, closed_month_ends

UPGRADE_KEY = "source_upgrade_" + PARSER_VERSION


def _snapshot(day):
    return db.one(
        """SELECT p.as_of,p.complete,p.source,p.hash,COUNT(h.id) positions,
                  SUM(h.weight) weight
           FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
           WHERE p.family=? AND p.as_of=?
           GROUP BY p.id ORDER BY p.complete DESC,p.id DESC LIMIT 1""",
        (FAMILY, day),
    )


def _valid(row):
    if not row or not row["complete"] or not row["hash"] or row["positions"] < 80:
        return False
    if abs(float(row["weight"] or 0) - 100) > 0.05:
        return False
    parsed = urlparse(row["source"])
    return bool(
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() in ("www.icicipruamc.com", "icicipruamc.com")
        and parsed.path.startswith("/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/")
        and parsed.path.lower().endswith(".zip")
    )


def run():
    db.init()
    disclosures.seed_sources()
    if db.setting(UPGRADE_KEY, False):
        print("ICICI monthly portfolio recovery already applied; nightly discovery remains active.")
        return True

    started = db.now()
    attempted = 0
    failures = []
    try:
        for family, url, title in amc_discovery.discover("ICICI"):
            if family != FAMILY:
                raise ValueError("Unexpected family in ICICI discovery")
            attempted += 1
            try:
                count = amc_discovery.store_report("ICICI", family, url, title)
                print(f"ICICI monthly portfolio: {count} dated facts/holdings; {url}", flush=True)
            except Exception as exc:
                failures.append((str(exc) or type(exc).__name__).splitlines()[0][:260])
    except Exception as exc:
        failures.append((str(exc) or type(exc).__name__).splitlines()[0][:260])

    expected = [day.isoformat() for day in closed_month_ends(count=2)]
    snapshots = [_snapshot(day) for day in expected]
    success = bool(
        attempted == 2
        and all(_valid(row) for row in snapshots)
        and not failures
    )
    detail = (
        f"ICICI: {attempted} monthly ZIP(s); expected={expected}; "
        f"snapshots={snapshots}; " + "; ".join(failures)
    )
    with db.connect() as connection:
        connection.execute(
            "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
            ("amc-reports", started, db.now(), "ok" if success else "partial", detail),
        )
        if success:
            connection.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)", (UPGRADE_KEY, "true")
            )
    if success:
        print(detail, flush=True)
    else:
        print("::warning::ICICI monthly portfolio recovery incomplete; prior data retained. " + detail,
              flush=True)
    return success


if __name__ == "__main__":
    run()
