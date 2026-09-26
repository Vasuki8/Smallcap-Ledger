"""Reclassify Samco lien request transaction forms that were misread as letters to unitholders."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db

FAMILY="Samco Small Cap Fund"
UPGRADE_KEY="source_upgrade_samco_lien_form_classification_2026_09_v1"


def candidates():
    return db.rows(
        """SELECT id,title,url,kind FROM documents
           WHERE family=? AND origin='AMC' AND kind='unitholder letter'
             AND (
               lower(title) LIKE '%lien%request%letter%unitholder%'
               OR lower(title) LIKE '%lien%request%letter%unit holder%'
               OR lower(url) LIKE '%lienrequestletterfromunitholder%'
               OR lower(url) LIKE '%lienrequestletterfromunitholder%'
             )
           ORDER BY id""",
        (FAMILY,),
    )


def run():
    db.init()
    if db.setting(UPGRADE_KEY,False):
        print("Samco lien-form classification repair already applied.")
        return True

    rows=candidates()
    with db.connect() as c:
        for row in rows:
            c.execute(
                """UPDATE documents SET kind='disclosure',scope='AMC'
                   WHERE id=? AND family=? AND origin='AMC'
                     AND kind='unitholder letter'""",
                (row["id"],FAMILY),
            )
        c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
        c.execute(
            "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
            (
                "amc-communication-classification",
                db.now(),db.now(),"ok",
                f"Samco lien request forms reclassified={len(rows)}",
            ),
        )
    print(f"Samco lien request forms reclassified={len(rows)}",flush=True)
    return True


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
