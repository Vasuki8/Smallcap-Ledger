"""One-time Canara Robeco TER/BER recovery; nightly AMC expense collection remains active."""
from pathlib import Path
import sys
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import db, amc_expenses

UPGRADE_KEY = "source_upgrade_canara-expense-v1"
FAMILY = amc_expenses.CANARA_FAMILY


def run():
    db.init()
    if db.setting(UPGRADE_KEY, False):
        print("Canara expense recovery already applied; nightly collection remains active.")
        return True

    result = amc_expenses.canara()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    rows = db.rows(
        """SELECT plan,metric,as_of,value,source
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
        success = len(days) == 1 and all(source.startswith(amc_expenses.CANARA_API) for source in sources)

    if not success:
        raise RuntimeError("Canara expense recovery did not produce a recent exact four-metric plan pair")

    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (UPGRADE_KEY, "true"))
    print(result)
    return True


if __name__ == "__main__":
    run()
