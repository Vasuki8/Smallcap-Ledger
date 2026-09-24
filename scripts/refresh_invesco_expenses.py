"""One-time Invesco India Small Cap TER recovery; nightly AMC expense collection remains active."""
from pathlib import Path
import sys
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import amc_expenses, db

UPGRADE_KEY = "source_upgrade_invesco-ter-v1"
FAMILY = amc_expenses.INVESCO_FAMILY


def run():
    db.init()
    if db.setting(UPGRADE_KEY, False):
        print("Invesco Small Cap TER recovery already applied; nightly collection remains active.")
        return True

    result = amc_expenses.invesco()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    rows = db.rows(
        """SELECT plan,metric,as_of,value,source,hash
           FROM metrics
           WHERE family=? AND plan IN ('Regular','Direct')
             AND metric IN ('ter','base_expense_ratio')
             AND as_of>=?
           ORDER BY as_of DESC""",
        (FAMILY, cutoff),
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
            and next(iter(sources)).startswith(amc_expenses.INVESCO_TER_API + "?")
            and len(hashes) == 1
            and bool(next(iter(hashes)))
        )
    if not success:
        raise RuntimeError("Invesco TER recovery did not produce a recent exact four-metric plan pair")

    with db.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings VALUES(?,?)",
            (UPGRADE_KEY, "true"),
        )
    print(result)
    print("INVESCO_TER_SOURCE", next(iter(sources)))
    print("INVESCO_TER_HASH", next(iter(hashes)))
    return True


if __name__ == "__main__":
    run()
