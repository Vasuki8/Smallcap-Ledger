"""One-time Abakkus/Axis AMC communication-source recovery.

Registers and exercises two dedicated first-party market-outlook catalogs plus
one exact current communication anchor for each AMC. The gate succeeds only
when both dynamic catalog paths produce retained communication evidence.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures

UPGRADE_KEY="source_upgrade_abakkus_axis_communications_2026_09_v1"

ABAKKUS_TAG="https://insights.abakkusinvest.com/tag/market-outlook/"
ABAKKUS_AUG="https://insights.abakkusinvest.com/market-outlook-august-2026/"
AXIS_TAG="https://www.axismf.com/mutual-fund-knowledge-centre/articles?tag=Market-Outlook"
AXIS_OUTLOOK="https://www.axismf.com/cms/sites/default/files/pdf-factsheets/Axis%20MF_%20Annual%20Equity%20Outlook%202026.pdf"

SOURCES=(
    ("Abakkus",ABAKKUS_TAG),
    ("Abakkus",ABAKKUS_AUG),
    ("Axis",AXIS_TAG),
    ("Axis",AXIS_OUTLOOK),
)


def _source(amc,url):
    return db.one("""SELECT * FROM source_pages
                     WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))


def _doc(family,url):
    return db.one("""SELECT d.title,d.kind,d.scope,d.url,d.published_at,d.origin,
                            COUNT(v.id) versions,MAX(v.observed_at) latest_observed_at
                     FROM documents d
                     LEFT JOIN document_versions v ON v.document_id=d.id
                     WHERE d.family=? AND d.url=?
                     GROUP BY d.id""",(family,url))


def _count(family,where="",params=()):
    return db.one(f"""SELECT COUNT(*) n FROM documents d
                      WHERE d.family=? AND d.origin='AMC'
                        AND d.kind IN ('market view','unitholder letter')
                        {where}""",(family,*params))["n"]


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Abakkus/Axis communication source recovery already applied.")
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
            elif not msg.endswith("; 0 download/parser gaps") and "download/parser gaps" in msg:status="Partial"
            with db.connect() as c:
                c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                          (db.now(),status,msg,row["id"]))
        except Exception as exc:
            failures.append(f"{amc}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}")

    abakkus=_doc("Abakkus Small Cap Fund",ABAKKUS_AUG)
    axis=_doc("Axis Small Cap Fund",AXIS_OUTLOOK)
    abakkus_children=_count(
        "Abakkus Small Cap Fund",
        "AND d.url LIKE 'https://insights.abakkusinvest.com/market-outlook-%'")
    axis_children=_count(
        "Axis Small Cap Fund",
        "AND d.url LIKE 'https://www.axismf.com/mutual-fund-knowledge-centre/articles/%'")
    abakkus_tag=_doc("Abakkus Small Cap Fund",ABAKKUS_TAG)
    axis_tag=_doc("Axis Small Cap Fund",AXIS_TAG)

    success=bool(
        not failures
        and abakkus and abakkus["kind"]=="market view" and abakkus["versions"]>=1
        and abakkus["published_at"]=="2026-08-11"
        and axis and axis["kind"]=="market view" and axis["versions"]>=1
        and abakkus_children>=1 and axis_children>=1
        and abakkus_tag and abakkus_tag["versions"]>=1
        and axis_tag and axis_tag["versions"]>=1
    )
    detail=(
        f"Abakkus market views={abakkus_children}; August={abakkus}; "
        f"Axis market-outlook articles={axis_children}; annual outlook={axis}; "
        + " | ".join(messages+failures)
    )
    with db.connect() as c:
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    if success:
        print(detail,flush=True)
    else:
        print("::warning::Abakkus/Axis communication source recovery incomplete; "+detail,flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
