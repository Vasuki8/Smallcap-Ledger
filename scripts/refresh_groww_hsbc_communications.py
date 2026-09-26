"""One-time Groww/HSBC first-party communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import groww_communications as groww
from tracker import hsbc_communications as hsbc

UPGRADE_KEY="source_upgrade_groww_hsbc_communications_2026_09_v1"

GROWW_DAILY="https://cms-resources.growwmf.in/uploads/daily_report_4_c7907e5e42.pdf"
HSBC_CURRENT=("https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/"
              "rbi-monetary-policy-review-august-2026")

SOURCES=(
    ("Groww",groww.LISTING),
    ("HSBC",hsbc.LISTING),
)


def _source(amc,url):
    return db.one("""SELECT * FROM source_pages
                     WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))


def _doc(family,url):
    return db.one("""SELECT d.title,d.kind,d.scope,d.url,d.published_at,d.origin,
                            COUNT(v.id) versions,MAX(v.observed_at) latest_observed_at
                     FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                     WHERE d.family=? AND d.url=? GROUP BY d.id""",(family,url))


def _count(family):
    return db.one("""SELECT COUNT(*) n FROM documents
                     WHERE family=? AND origin='AMC'
                       AND kind IN ('market view','unitholder letter')""",
                  (family,))["n"]


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Groww/HSBC communication source recovery already applied.")
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
            elif "no automatically readable" in msg or "No matching" in msg:status="Limited"
            elif "download/parser gaps" in msg and not msg.endswith("0 download/parser gaps"):
                status="Partial"
            with db.connect() as c:
                c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                          (db.now(),status,msg,row["id"]))
        except Exception as exc:
            failures.append(f"{amc}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}")

    groww_source=_doc(groww.FAMILY,groww.LISTING)
    groww_daily=_doc(groww.FAMILY,GROWW_DAILY)
    hsbc_source=_doc(hsbc.FAMILY,hsbc.LISTING)
    hsbc_current=_doc(hsbc.FAMILY,HSBC_CURRENT)
    groww_count=_count(groww.FAMILY)
    hsbc_count=_count(hsbc.FAMILY)

    success=bool(
        not failures
        and groww_source and groww_source["versions"]>=1
        and groww_daily and groww_daily["kind"]=="market view"
        and groww_daily["published_at"]=="2026-09-21"
        and groww_daily["versions"]>=1
        and groww_count>=3
        and hsbc_source and hsbc_source["versions"]>=1
        and hsbc_current and hsbc_current["kind"]=="market view"
        and hsbc_current["published_at"]=="2026-08-11"
        and hsbc_current["versions"]>=1
        and hsbc_count>=8
    )
    detail=(
        f"Groww communications={groww_count}; daily={groww_daily}; "
        f"HSBC communications={hsbc_count}; current={hsbc_current}; "
        +" | ".join(messages+failures)
    )
    with db.connect() as c:
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    if success:
        print(detail,flush=True)
    else:
        print("::warning::Groww/HSBC communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
