"""One-time Kotak / Mirae Asset AMC communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import kotak_communications as kotak

UPGRADE_KEY="source_upgrade_kotak_mirae_communications_2026_09_v1"

KOTAK_FAMILY="Kotak Small Cap Fund"
KOTAK_LISTING=kotak.LISTING
KOTAK_CURRENT=("https://www.kotakmf.com/kotakmf/reportupload/download/"
               "Monthly/6125/2026/8")

MIRAE_FAMILY="Mirae Asset Small Cap Fund"
MIRAE_OUTLOOK=("https://www.miraeassetmf.co.in/docs/default-source/"
               "marketing-insights/annual-outlook-2025.pdf")

SOURCES=(
    ("Kotak",KOTAK_LISTING),
    ("Mirae",MIRAE_OUTLOOK),
)


def _source(amc,url):
    return db.one("""SELECT * FROM source_pages
                     WHERE lower(amc_match)=lower(?) AND url=?""",(amc,url))


def _doc(family,url):
    return db.one("""SELECT d.title,d.kind,d.scope,d.url,d.published_at,d.origin,
                            COUNT(v.id) versions,
                            (SELECT hash FROM document_versions
                             WHERE document_id=d.id ORDER BY observed_at DESC,id DESC LIMIT 1) hash
                     FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                     WHERE d.family=? AND d.url=? GROUP BY d.id""",(family,url))


def _body(row):
    if not row or not row.get("hash"):return b""
    path=db.archive_binary_path(row["hash"])
    return path.read_bytes() if path else b""


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Kotak/Mirae communication source recovery already applied.")
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

    kotak_source=_doc(KOTAK_FAMILY,KOTAK_LISTING)
    kotak_doc=_doc(KOTAK_FAMILY,KOTAK_CURRENT)
    mirae_doc=_doc(MIRAE_FAMILY,MIRAE_OUTLOOK)
    mirae_body=_body(mirae_doc)

    success=bool(
        not failures
        and kotak_source and kotak_source["versions"]>=1
        and kotak_doc and kotak_doc["kind"]=="market view"
        and kotak_doc["published_at"]=="2026-09-09"
        and kotak_doc["versions"]==0
        and mirae_doc and mirae_doc["kind"]=="market view"
        and mirae_doc["published_at"] is None
        and mirae_doc["versions"]>=1
        and mirae_body.startswith(b"%PDF")
    )
    detail=(
        f"Kotak source={kotak_source}; Kotak={kotak_doc}; Kotak original link-only={bool(kotak_doc and kotak_doc['versions']==0)}; "
        f"Mirae={mirae_doc}; Mirae PDF={mirae_body.startswith(b'%PDF')}; "
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
        print("::warning::Kotak/Mirae communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
