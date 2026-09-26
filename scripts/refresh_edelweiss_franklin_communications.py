"""One-time Edelweiss/Franklin AMC communication-source recovery.

Edelweiss uses first-party Fund & Market Insights pages. Franklin's public
Latest Commentaries page is a JS shell on the production runner, so current
evidence is anchored to the exact Franklin Widen-hosted Monthly Equity Outlook
viewer and its underlying PDF while the listing page remains registered.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures

UPGRADE_KEY="source_upgrade_edelweiss_franklin_communications_2026_09_v1"

EDELWEISS_INSIGHTS="https://www.edelweissmf.com/investor-insights/fund-market"
EDELWEISS_CURVE="https://www.edelweissmf.com/investor-insights/fund-market/curve"
EDELWEISS_FACTOR="https://www.edelweissmf.com/investor-insights/fund-market/factor-investing-2026-outlook"
EDELWEISS_FACTOR_PDF="https://www.edelweissmf.com/Files/Insigths/viewpoint/EMF_Factor_Investing_Outlook_2026_01012026_060107_PM.pdf"

FRANKLIN_LATEST="https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries"
FRANKLIN_OUTLOOK="https://franklintempletonprod.widen.net/s/rrxmvxwmh9/ft-monthly-equity-market-outlook"

SOURCES=(
    ("Edelweiss",EDELWEISS_INSIGHTS),
    ("Edelweiss",EDELWEISS_CURVE),
    ("Edelweiss",EDELWEISS_FACTOR),
    ("Franklin",FRANKLIN_LATEST),
    ("Franklin",FRANKLIN_OUTLOOK),
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


def _franklin_pdf():
    return db.one("""SELECT d.title,d.kind,d.scope,d.url,d.published_at,d.origin,
                            COUNT(v.id) versions,MAX(v.observed_at) latest_observed_at
                     FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                     WHERE d.family='Franklin India Small Cap Fund'
                       AND d.origin='AMC' AND d.kind='market view'
                       AND d.url LIKE 'https://franklintempletonprod.widen.net/content/%/original/ft-monthly-equity-market-outlook.pdf%'
                     GROUP BY d.id ORDER BY d.id DESC LIMIT 1""")


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Edelweiss/Franklin communication source recovery already applied.")
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
            failures.append(f"{amc}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}")

    factor=_doc("Edelweiss Small Cap Fund",EDELWEISS_FACTOR)
    factor_pdf=_doc("Edelweiss Small Cap Fund",EDELWEISS_FACTOR_PDF)
    curve=_doc("Edelweiss Small Cap Fund",EDELWEISS_CURVE)
    insights=_doc("Edelweiss Small Cap Fund",EDELWEISS_INSIGHTS)
    franklin_listing=_doc("Franklin India Small Cap Fund",FRANKLIN_LATEST)
    franklin_viewer=_doc("Franklin India Small Cap Fund",FRANKLIN_OUTLOOK)
    franklin_pdf=_franklin_pdf()

    success=bool(
        not failures
        and factor and factor["kind"]=="market view" and factor["versions"]>=1
        and factor_pdf and factor_pdf["kind"]=="market view" and factor_pdf["versions"]>=1
        and curve and curve["kind"]=="market view" and curve["versions"]>=1
        and insights and insights["versions"]>=1
        and franklin_listing and franklin_listing["versions"]>=1
        and franklin_viewer and franklin_viewer["kind"]=="market view"
        and franklin_viewer["versions"]>=1
        and franklin_pdf and franklin_pdf["versions"]>=1
        and _count("Edelweiss Small Cap Fund")>=3
        and _count("Franklin India Small Cap Fund")>=2
    )
    detail=(
        f"Edelweiss communications={_count('Edelweiss Small Cap Fund')}; "
        f"factor={factor}; factor_pdf={factor_pdf}; curve={curve}; "
        f"Franklin communications={_count('Franklin India Small Cap Fund')}; "
        f"viewer={franklin_viewer}; pdf={franklin_pdf}; "
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
        print("::warning::Edelweiss/Franklin communication source recovery incomplete; "+detail,flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
