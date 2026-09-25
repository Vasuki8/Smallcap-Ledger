"""One-time UTI Small Cap BER recovery; nightly collection remains active."""
from pathlib import Path
import sys
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import amc_expenses, db

UPGRADE_KEY = "source_upgrade_uti-ber-v1"
FAMILY = amc_expenses.UTI_FAMILY
SOURCE_PREFIX = (
    "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/"
)


def run():
    db.init()
    if db.setting(UPGRADE_KEY, False):
        print("UTI BER recovery already applied; nightly collection remains active.")
        return True

    result = amc_expenses.uti()
    fy_start = date(
        amc_expenses._uti_financial_year_start(date.today()), 4, 1
    ).isoformat()
    rows = db.rows(
        """SELECT plan,metric,as_of,value,source,hash
           FROM metrics
           WHERE family=? AND plan IN ('Regular','Direct')
             AND metric IN ('ter','base_expense_ratio')
             AND as_of>=? AND source LIKE ?
           ORDER BY as_of DESC,observed_at DESC""",
        (FAMILY, fy_start, SOURCE_PREFIX + "%daily_ter_ytd_%"),
    )
    latest = {}
    for row in rows:
        latest.setdefault((row["plan"], row["metric"]), row)
    required = {
        ("Regular", "ter"),
        ("Regular", "base_expense_ratio"),
        ("Direct", "ter"),
        ("Direct", "base_expense_ratio"),
    }
    success = required.issubset(latest)
    if success:
        days = {latest[key]["as_of"] for key in required}
        sources = {latest[key]["source"] for key in required}
        hashes = {latest[key]["hash"] for key in required}
        success = (
            len(days) == 1
            and len(sources) == 1
            and next(iter(sources)).startswith(SOURCE_PREFIX)
            and "daily_ter_ytd_" in next(iter(sources)).lower()
            and len(hashes) == 1
            and bool(next(iter(hashes)))
        )
    if not success:
        raise RuntimeError(
            "UTI BER recovery did not produce an exact current-FY four-metric plan pair"
        )

    with db.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings VALUES(?,?)",
            (UPGRADE_KEY, "true"),
        )
    print(result)
    print("UTI_BER_SOURCE", next(iter(sources)))
    print("UTI_BER_HASH", next(iter(hashes)))
    return True


if __name__ == "__main__":
    run()
