"""One-time ICICI Prudential / Invesco India AMC communication recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures

UPGRADE_KEY="source_upgrade_icici_invesco_communications_2026_09_v1"

ICICI_FAMILY="ICICI Prudential Small Cap Fund"
ICICI_OUTLOOK=("https://www.icicipruamc.com/blob/sebi-repo/Advertisements/2026/August/"
               "Filing%20date%2012-08-2026/Release%20date%2011-08-2026/Advertisements/"
               "Annexure%206%20-%20Mailer%20on%20Monthly%20Market%20Outlook.html")
INVESCO_FAMILY="Invesco India Small Cap Fund"
INVESCO_OUTLOOK=("https://www.invescomutualfund.com/docs/default-source/presentations-pdf/"
                 "market-outlook---apr2026.pdf?sfvrsn=31679dc2_0")

SOURCES=(
    ("ICICI",ICICI_OUTLOOK),
    ("Invesco",INVESCO_OUTLOOK),
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
        print("ICICI/Invesco communication source recovery already applied.")
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

    icici=_doc(ICICI_FAMILY,ICICI_OUTLOOK)
    invesco=_doc(INVESCO_FAMILY,INVESCO_OUTLOOK)
    icici_body=_body(icici)
    invesco_body=_body(invesco)

    success=bool(
        not failures
        and icici and icici["kind"]=="market view"
        and icici["published_at"]=="2026-08-11"
        and icici["versions"]>=1
        and b"Equity Market Outlook" in icici_body
        and b"Fixed Income Outlook" in icici_body
        and b"ICICI Prudential" in icici_body
        and invesco and invesco["kind"]=="market view"
        and invesco["published_at"] is None
        and invesco["versions"]>=1
        and invesco_body.startswith(b"%PDF")
    )
    detail=(
        f"ICICI={icici}; ICICI outlook identity="
        f"{bool(b'Equity Market Outlook' in icici_body and b'Fixed Income Outlook' in icici_body)}; "
        f"Invesco={invesco}; Invesco PDF={invesco_body.startswith(b'%PDF')}; "
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
        print("::warning::ICICI/Invesco communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
