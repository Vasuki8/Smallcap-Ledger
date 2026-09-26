"""One-time SBI / Sundaram AMC communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures

UPGRADE_KEY="source_upgrade_sbi_sundaram_communications_2026_09_v2"

SBI_FAMILY="SBI Small Cap Fund"
SBI_OUTLOOK="https://www.sbimf.com/learn-about-mutual-funds/2026-outlook"

SUNDARAM_FAMILY="Sundaram Small Cap Fund"
SUNDARAM_OUTLOOK="https://blog.sundarammutual.com/Documents/outlook-june-2026.pdf"

SOURCES=(
    ("SBI",SBI_OUTLOOK),
    ("Sundaram",SUNDARAM_OUTLOOK),
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
        print("SBI/Sundaram communication source recovery already applied.")
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

    sbi=_doc(SBI_FAMILY,SBI_OUTLOOK)
    sundaram=_doc(SUNDARAM_FAMILY,SUNDARAM_OUTLOOK)
    sbi_body=_body(sbi);sundaram_body=_body(sundaram)

    sbi_identity=all(marker in sbi_body for marker in (
        b"Executive Summary",b"Equity Outlook",b"Fixed Income Outlook",
        b"Rajeev Radhakrishnan",
    ))
    success=bool(
        not failures
        and sbi and sbi["kind"]=="market view"
        and sbi["published_at"]=="2026-01-08"
        and sbi["versions"]>=1
        and sbi_identity
        and sundaram and sundaram["kind"]=="market view"
        and sundaram["published_at"] is None
        and sundaram["versions"]>=1
        and sundaram_body.startswith(b"%PDF")
        and len(sundaram_body)>100000
    )
    detail=(
        f"SBI={sbi}; SBI identity={sbi_identity}; "
        f"Sundaram={sundaram}; Sundaram PDF="
        f"{sundaram_body.startswith(b'%PDF')} bytes={len(sundaram_body)}; "
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
        print("::warning::SBI/Sundaram communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
