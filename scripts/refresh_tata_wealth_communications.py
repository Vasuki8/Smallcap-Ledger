"""One-time Tata / The Wealth Company AMC communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import tata_wealth_communications as comm

UPGRADE_KEY="source_upgrade_tata_wealth_communications_2026_09_v1"
SOURCES=(
    ("Tata",comm.TATA_OUTLOOK),
    ("The Wealth",comm.WEALTH_INSIGHTS),
)


def _source(amc,url):
    return db.one("""SELECT * FROM source_pages
                     WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))


def _count(family):
    return db.one("""SELECT COUNT(*) n FROM documents
                     WHERE family=? AND origin='AMC'
                       AND kind IN ('market view','unitholder letter')""",
                  (family,))["n"]


def _archived_count(family):
    return db.one("""SELECT COUNT(DISTINCT d.id) n
                     FROM documents d JOIN document_versions v ON v.document_id=d.id
                     WHERE d.family=? AND d.origin='AMC'
                       AND d.kind IN ('market view','unitholder letter')""",
                  (family,))["n"]


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Tata/Wealth communication source recovery already applied.")
        return True

    started=db.now();failures=[];messages=[]
    for amc,url in SOURCES:
        row=_source(amc,url)
        if not row:
            failures.append(f"Registered source missing: {amc} · {url}")
            continue
        try:
            msg=disclosures.ingest_source(row)
            messages.append(f"{amc}: {msg}")
            status="Checked"
            if msg.startswith("Excluded:"):status="Excluded"
            elif "download/parser gaps" in msg and not msg.endswith("0 download/parser gaps"):
                status="Partial"
            with db.connect() as c:
                c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                          (db.now(),status,msg,row["id"]))
        except Exception as exc:
            failures.append(f"{amc}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}")

    tata=_count(comm.TATA_FAMILY);wealth=_count(comm.WEALTH_FAMILY)
    tata_archived=_archived_count(comm.TATA_FAMILY)
    wealth_archived=_archived_count(comm.WEALTH_FAMILY)
    success=bool(
        not failures
        and tata>=1 and tata_archived>=1
        and wealth>=1 and wealth_archived>=1
    )
    detail=(
        f"Tata communications={tata}, archived={tata_archived}; "
        f"Wealth communications={wealth}, archived={wealth_archived}; "
        +" | ".join(messages+failures)
    )
    with db.connect() as c:
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    if success:print(detail,flush=True)
    else:print("::warning::Tata/Wealth communication source recovery incomplete; "+detail,flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
