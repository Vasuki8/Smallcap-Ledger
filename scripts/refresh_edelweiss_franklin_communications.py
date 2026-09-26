"""One-time Edelweiss/Franklin AMC communication-source recovery.

Edelweiss uses first-party Fund & Market Insights pages with archived originals.
Franklin's public Latest Commentaries UI is a JS shell in the production runner;
the public frontend's same-domain article API is therefore the authoritative
automated source for titles, dates and first-party article URLs. Widen binaries
remain link-only because their robots policy disallows automatic access.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import franklin_communications as franklin

UPGRADE_KEY="source_upgrade_edelweiss_franklin_communications_2026_09_v2"

EDELWEISS_INSIGHTS="https://www.edelweissmf.com/investor-insights/fund-market"
EDELWEISS_CURVE="https://www.edelweissmf.com/investor-insights/fund-market/curve"
EDELWEISS_FACTOR="https://www.edelweissmf.com/investor-insights/fund-market/factor-investing-2026-outlook"
EDELWEISS_FACTOR_PDF="https://www.edelweissmf.com/Files/Insigths/viewpoint/EMF_Factor_Investing_Outlook_2026_01012026_060107_PM.pdf"

FRANKLIN_LATEST=franklin.LISTING
FRANKLIN_API=franklin.ENDPOINT
FRANKLIN_MONTHLY="https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries/article/monthly-equity-outlook"
LEGACY_WIDEN="https://franklintempletonprod.widen.net/s/rrxmvxwmh9/ft-monthly-equity-market-outlook"

SOURCES=(
    # The dynamic Edelweiss insight pages remain registered for scheduled
    # retries, but the one-time release gate uses the exact first-party PDF
    # because those HTML routes currently return 403 in the production runner.
    ("Edelweiss",EDELWEISS_FACTOR_PDF),
    ("Franklin",FRANKLIN_LATEST),
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
        print("Edelweiss/Franklin communication source recovery already applied.")
        return True

    # A robots-blocked Widen viewer was briefly registered during investigation.
    # Preserve the row for audit, but stop scheduled retries; the Franklin API
    # now supplies the authoritative metadata and official article links.
    with db.connect() as c:
        c.execute("""UPDATE source_pages
                     SET enabled=0,status='Excluded',
                         detail='Superseded by Franklin first-party article API; Widen robots policy disallows automatic binary retrieval'
                     WHERE lower(amc_match)='franklin' AND url=?""",
                  (LEGACY_WIDEN,))

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

    factor_pdf=_doc("Edelweiss Small Cap Fund",EDELWEISS_FACTOR_PDF)

    franklin_api=_doc("Franklin India Small Cap Fund",FRANKLIN_API)
    franklin_monthly=_doc("Franklin India Small Cap Fund",FRANKLIN_MONTHLY)
    franklin_count=_count("Franklin India Small Cap Fund")
    franklin_unarchived=db.one("""SELECT COUNT(*) n FROM documents d
      LEFT JOIN document_versions v ON v.document_id=d.id
      WHERE d.family='Franklin India Small Cap Fund' AND d.origin='AMC'
        AND d.kind='market view' AND v.id IS NULL""")["n"]

    success=bool(
        not failures
        and factor_pdf and factor_pdf["kind"]=="market view" and factor_pdf["versions"]>=1
        and franklin_api and franklin_api["kind"]=="source page" and franklin_api["versions"]>=1
        and franklin_monthly and franklin_monthly["kind"]=="market view"
        and franklin_monthly["published_at"]=="2026-08-06"
        and franklin_monthly["versions"]==0
        and _count("Edelweiss Small Cap Fund")>=1
        and franklin_count>=6
        and franklin_unarchived==franklin_count
    )
    detail=(
        f"Edelweiss communications={_count('Edelweiss Small Cap Fund')}; "
        f"exact_factor_pdf={factor_pdf}; "
        f"Franklin communications={franklin_count}; API={franklin_api}; "
        f"monthly_equity={franklin_monthly}; "
        f"Franklin link-only originals={franklin_unarchived}; "
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
