"""One-time Bajaj/Bandhan AMC communication-source recovery.

Uses exact first-party routes established by live production probes. The gate
requires archived communication evidence for Bajaj's current Equity Outlook and
Bandhan's current equity/debt Market Outlook posts before marking completion.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures

UPGRADE_KEY="source_upgrade_bajaj_bandhan_communications_2026_09_v1"

BAJAJ_OUTLOOK="https://cobranding.bajajamc.com/marketing/Cobrandingmarketingmaterial?LId=51"
BAJAJ_VIEWER="https://cobranding.bajajamc.com/Home/dynamicvideoslide/469/6jfeX8S/454"
BANDHAN_LANDING="https://bandhanmutual.com/downloads/market-outlook"
BANDHAN_EQUITY="https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-equity-september-2026/"
BANDHAN_DEBT="https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-debt-september-2026/"

SOURCES=(
    ("Bajaj",BAJAJ_OUTLOOK),
    ("Bandhan",BANDHAN_LANDING),
    ("Bandhan",BANDHAN_EQUITY),
    ("Bandhan",BANDHAN_DEBT),
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


def _communication_count(family):
    return db.one("""SELECT COUNT(*) n FROM documents
                     WHERE family=? AND origin='AMC'
                       AND kind IN ('market view','unitholder letter')""",
                  (family,))["n"]


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Bajaj/Bandhan communication source recovery already applied.")
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
            elif "download/parser gaps" in msg and not msg.endswith("; 0 download/parser gaps"):
                status="Partial"
            with db.connect() as c:
                c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                          (db.now(),status,msg,row["id"]))
        except Exception as exc:
            failures.append(
                f"{amc}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}")

    bajaj=_doc("Bajaj Finserv Small Cap Fund",BAJAJ_VIEWER)
    bandhan_equity=_doc("Bandhan Small Cap Fund",BANDHAN_EQUITY)
    bandhan_debt=_doc("Bandhan Small Cap Fund",BANDHAN_DEBT)
    bajaj_source=_doc("Bajaj Finserv Small Cap Fund",BAJAJ_OUTLOOK)
    bandhan_landing=_doc("Bandhan Small Cap Fund",BANDHAN_LANDING)

    success=bool(
        not failures
        and bajaj and bajaj["kind"]=="market view"
        and bajaj["published_at"]=="2026-05-21" and bajaj["versions"]>=1
        and bandhan_equity and bandhan_equity["kind"]=="market view"
        and bandhan_equity["published_at"]=="2026-09-11"
        and bandhan_equity["versions"]>=1
        and bandhan_debt and bandhan_debt["kind"]=="market view"
        and bandhan_debt["published_at"]=="2026-09-11"
        and bandhan_debt["versions"]>=1
        and bajaj_source and bajaj_source["versions"]>=1
        and bandhan_landing and bandhan_landing["versions"]>=1
        and _communication_count("Bajaj Finserv Small Cap Fund")>=1
        and _communication_count("Bandhan Small Cap Fund")>=2
    )
    detail=(
        f"Bajaj communications={_communication_count('Bajaj Finserv Small Cap Fund')}; "
        f"equity_outlook={bajaj}; "
        f"Bandhan communications={_communication_count('Bandhan Small Cap Fund')}; "
        f"equity={bandhan_equity}; debt={bandhan_debt}; "
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
        print("::warning::Bajaj/Bandhan communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
