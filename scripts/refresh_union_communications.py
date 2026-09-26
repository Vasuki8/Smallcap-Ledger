"""One-time Union Mutual Fund communication-source recovery."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures
from tracker import union_communications as comm

UPGRADE_KEY="source_upgrade_union_communications_2026_09_v1"

def run():
    db.init();disclosures.seed_sources()
    if db.setting(UPGRADE_KEY,False):
        print("Union communication recovery already applied.")
        return True
    row=db.one("""SELECT * FROM source_pages WHERE lower(amc_match)=lower(?) AND url=?""",
               ("Union",comm.LISTING))
    if not row:
        print("::warning::Union communication source not registered",flush=True);return False
    started=db.now()
    try:
        msg=disclosures.ingest_source(row);failure=None
    except Exception as exc:
        msg="";failure=(str(exc) or type(exc).__name__).splitlines()[0][:300]
    count=db.one("""SELECT COUNT(*) n FROM documents WHERE family=? AND origin='AMC'
                    AND kind IN ('market view','unitholder letter')""",(comm.FAMILY,))["n"]
    archived=db.one("""SELECT COUNT(DISTINCT d.id) n FROM documents d
                       JOIN document_versions v ON v.document_id=d.id
                       WHERE d.family=? AND d.origin='AMC'
                         AND d.kind IN ('market view','unitholder letter')""",(comm.FAMILY,))["n"]
    success=bool(not failure and count>=1 and archived>=1)
    detail=f"Union communications={count}, archived={archived}; {msg or failure}"
    with db.connect() as c:
        c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",
                  (db.now(),"Checked" if success else "Partial",msg or failure,row["id"]))
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    print(detail,flush=True)
    return success

if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
