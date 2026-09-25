"""One-time Groww Small Cap Current BER recovery; nightly collection remains active."""
from pathlib import Path
import sys
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import amc_expenses, db

UPGRADE_KEY = "source_upgrade_groww-ber-v1"
FAMILY = amc_expenses.GROWW_FAMILY


def run():
    db.init()
    if db.setting(UPGRADE_KEY, False):
        print("Groww BER recovery already applied; nightly collection remains active.")
        return True

    result = amc_expenses.groww()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    rows = db.rows(
        """SELECT plan,metric,as_of,value,source,hash
           FROM metrics
           WHERE family=? AND plan IN ('Regular','Direct')
             AND metric='base_expense_ratio'
             AND as_of>=?
           ORDER BY as_of DESC""",
        (FAMILY, cutoff),
    )
    latest = {}
    for row in rows:
        latest.setdefault(row["plan"], row)
    required = {"Regular", "Direct"}
    success = required.issubset(latest)
    if success:
        days = {latest[plan]["as_of"] for plan in required}
        sources = {latest[plan]["source"] for plan in required}
        hashes = {latest[plan]["hash"] for plan in required}
        success = (
            len(days) == 1
            and len(sources) == 1
            and next(iter(sources)).startswith(
                "https://assets-netstorage.growwmf.in/compliance_docs/Downloads/"
                "Expense%20Ratio/Notice%20-%20Change%20in%20TER/"
            )
            and len(hashes) == 1
            and bool(next(iter(hashes)))
        )
    if not success:
        raise RuntimeError(
            "Groww BER recovery did not produce a recent exact two-plan Current BER observation"
        )

    with db.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings VALUES(?,?)",
            (UPGRADE_KEY, "true"),
        )
    print(result)
    print("GROWW_BER_SOURCE", next(iter(sources)))
    print("GROWW_BER_HASH", next(iter(hashes)))
    return True


if __name__ == "__main__":
    run()
