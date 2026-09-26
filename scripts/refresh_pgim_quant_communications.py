"""One-time PGIM India / quant Mutual AMC communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import pgim_communications as pgim
from tracker import quant_communications as quant

UPGRADE_KEY="source_upgrade_pgim_quant_communications_2026_09_v1"

PGIM_ANCHOR=("https://www.pgimindia.com/mutual-funds/domestic-insights/"
             "CEO-Letters/article/Money-for-a-Life-in-Motion")
QUANT_ANCHOR=("https://www.quantmutual.com/Admin/Pdf/"
              "Predictive%20Analytics_June%202023_Volume%203_Issue%202.pdf")

SOURCES=(
    ("PGIM",pgim.LISTING),
    ("quant Mutual",quant.LISTING),
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


def _count(family):
    return db.one("""SELECT COUNT(*) n FROM documents
                     WHERE family=? AND origin='AMC'
                       AND kind IN ('market view','unitholder letter')""",
                  (family,))["n"]


def _body(row):
    if not row or not row.get("hash"):return b""
    path=db.archive_binary_path(row["hash"])
    return path.read_bytes() if path else b""


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("PGIM/quant communication source recovery already applied.")
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

    pgim_source=_doc(pgim.FAMILY,pgim.LISTING)
    pgim_anchor=_doc(pgim.FAMILY,PGIM_ANCHOR)
    quant_source=_doc(quant.FAMILY,quant.LISTING)
    quant_anchor=_doc(quant.FAMILY,QUANT_ANCHOR)
    quant_body=_body(quant_anchor)
    pgim_count=_count(pgim.FAMILY);quant_count=_count(quant.FAMILY)

    success=bool(
        not failures
        and pgim_source and pgim_source["versions"]>=1
        and pgim_anchor and pgim_anchor["kind"]=="market view"
        and pgim_anchor["versions"]>=1
        and pgim_count>=3
        and quant_source and quant_source["versions"]>=1
        and quant_anchor and quant_anchor["kind"]=="market view"
        and quant_anchor["published_at"] is None
        and quant_anchor["versions"]>=1
        and quant_body.startswith(b"%PDF")
        and quant_count>=7
    )
    detail=(
        f"PGIM communications={pgim_count}; anchor={pgim_anchor}; "
        f"quant communications={quant_count}; anchor={quant_anchor}; "
        f"quant anchor PDF={quant_body.startswith(b'%PDF')}; "
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
        print("::warning::PGIM/quant communication source recovery incomplete; "+detail,
              flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
