"""One-time Axis Small Cap monthly portfolio recovery; nightly discovery remains active."""
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import amc_discovery, db, disclosures
from tracker.axis_portfolios import FAMILY, PARSER_VERSION
from tracker.coverage import expected_portfolio_as_of

UPGRADE_KEY = "source_upgrade_" + PARSER_VERSION


def run():
    db.init()
    disclosures.seed_sources()
    if db.setting(UPGRADE_KEY, False):
        print("Axis monthly portfolio recovery already applied; nightly discovery remains active.")
        return True

    started = db.now()
    attempted = 0
    failures = []
    try:
        for family, url, title in amc_discovery.discover("Axis"):
            if family != FAMILY:
                raise ValueError("Unexpected family in Axis discovery")
            attempted += 1
            try:
                count = amc_discovery.store_report("Axis", family, url, title)
                print(f"Axis monthly portfolio: {count} dated facts/holdings; {url}", flush=True)
            except Exception as exc:
                failures.append((str(exc) or type(exc).__name__).splitlines()[0][:240])
    except Exception as exc:
        failures.append((str(exc) or type(exc).__name__).splitlines()[0][:240])

    expected = expected_portfolio_as_of()
    latest = db.one(
        """SELECT p.as_of,p.complete,p.source,p.hash,COUNT(h.id) positions,
                  SUM(h.weight) weight
           FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
           WHERE p.family=? AND p.complete=1 AND p.as_of>=?
           GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",
        (FAMILY, expected),
    )
    valid_source = False
    if latest:
        parsed = urlparse(latest["source"])
        valid_source = bool(
            parsed.scheme == "https"
            and (parsed.hostname or "").lower() in ("www.axismf.com", "axismf.com")
            and "monthly_portfolio_axis_small_cap_fund_" in parsed.path.lower()
            and parsed.path.lower().endswith(".xlsx")
        )
    success = bool(
        attempted
        and latest
        and latest["complete"]
        and latest["positions"] >= 130
        # Individual published percentages are rounded to two decimals; the
        # parsed workbook separately reconciles exact market values and the
        # published 100% grand total before marking the snapshot complete.
        and abs(float(latest["weight"] or 0) - 100) <= 0.05
        and valid_source
        and latest["hash"]
        and not failures
    )
    detail = (
        f"Axis: {attempted} monthly report(s); expected>={expected}; "
        f"complete={latest}; " + "; ".join(failures)
    )
    with db.connect() as c:
        c.execute(
            "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
            ("amc-reports", started, db.now(), "ok" if success else "partial", detail),
        )
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (UPGRADE_KEY, "true"))

    if success:
        print(detail, flush=True)
    else:
        print("::warning::Axis monthly portfolio recovery incomplete; prior data retained. " + detail,
              flush=True)
    return success


if __name__ == "__main__":
    run()
