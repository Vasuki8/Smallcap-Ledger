"""One-time UTI Mutual Fund communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import uti_communications as comm

UPGRADE_KEY="source_upgrade_uti_communications_2026_09_v1"


def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("UTI communication recovery already applied.")
        return True

    row=db.one("""SELECT * FROM source_pages
                  WHERE lower(amc_match)=lower(?) AND url=?""",
               ("UTI",comm.LISTING))
    if not row:
        print("::warning::UTI communication source not registered",flush=True)
        return False

    started=db.now();failure=None;msg=""
    try:
        msg=disclosures.ingest_source(row)
    except Exception as exc:
        failure=(str(exc) or type(exc).__name__).splitlines()[0][:300]

    stats=db.one("""SELECT COUNT(*) n,
                           SUM(CASE WHEN v.id IS NOT NULL THEN 1 ELSE 0 END) archived
                    FROM documents d
                    LEFT JOIN (
                      SELECT document_id,MIN(id) id FROM document_versions GROUP BY document_id
                    ) v ON v.document_id=d.id
                    WHERE d.family=? AND d.origin='AMC'
                      AND d.kind IN ('market view','unitholder letter')""",
                 (comm.FAMILY,))
    count=int(stats["n"] or 0);archived=int(stats["archived"] or 0)
    source_doc=db.one("""SELECT COUNT(v.id) versions FROM documents d
                         LEFT JOIN document_versions v ON v.document_id=d.id
                         WHERE d.family=? AND d.url=? GROUP BY d.id""",
                      (comm.FAMILY,comm.LISTING))
    success=bool(
        not failure and source_doc and source_doc["versions"]>=1
        and count>=1 and archived>=1
    )
    detail=(
        f"UTI communications={count}, archived={archived}, "
        f"source_versions={source_doc['versions'] if source_doc else 0}; "
        f"{msg or failure}"
    )
    with db.connect() as c:
        c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                  (db.now(),"Checked" if success else "Partial",msg or failure,row["id"]))
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    if success:print(detail,flush=True)
    else:print("::warning::UTI communication recovery incomplete; "+detail,flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
