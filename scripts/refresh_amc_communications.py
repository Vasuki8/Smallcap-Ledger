"""One-time retained-evidence repair for ITI and Mahindra AMC communications.

This upgrade does not fetch new data. It promotes only exact first-party,
already-versioned monthly outlook/update pages whose retained title and URL
unambiguously establish an AMC communication.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,disclosures,providers

UPGRADE_KEY="source_upgrade_amc_communications_2026_09_v1"

TARGETS=(
    ("Iti Small Cap Fund","ITI","Equity Market Update",
     "https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html"),
    ("Iti Small Cap Fund","ITI","Debt Market Update",
     "https://www.itiamc.com/digitalfactsheet/July2026/debt-update.html"),
    ("Iti Small Cap Fund","ITI","Market Outlook",
     "https://www.itiamc.com/digitalfactsheet/July2026/CEO.html"),
    ("Mahindra Manulife Small Cap Fund","Mahindra","Market Outlook",
     "https://www.mahindramanulife.com/digital-factsheet/july-2026/Outlook.html"),
)


def _validated_document(family,amc,label,url):
    source=db.one("""SELECT amc_match,label,url FROM source_pages
                     WHERE lower(amc_match)=lower(?) AND url=? AND label=?""",
                  (amc,url,label))
    if not source:
        raise ValueError(f"Registered communication source missing: {family} · {url}")
    if not disclosures.official_publication_url(url,amc):
        raise ValueError(f"Unregistered communication host: {family} · {url}")
    kind=disclosures.dated_communication_source_kind(label,url)
    if kind!="market view" or providers.classify(label,url)!="market view":
        raise ValueError(f"Communication identity not explicit: {family} · {url}")
    row=db.one("""SELECT d.id,d.kind,d.scope,d.origin,d.published_at,
                         COUNT(v.id) versions
                  FROM documents d
                  LEFT JOIN document_versions v ON v.document_id=d.id
                  WHERE d.family=? AND d.url=? AND d.title=?
                  GROUP BY d.id""",(family,url,label))
    if not row or row["origin"]!="AMC" or not row["versions"]:
        raise ValueError(f"Retained AMC document evidence missing: {family} · {url}")
    if row["published_at"] is not None:
        # This repair must never manufacture or modify dates. An independently
        # retained source date is fine and remains untouched.
        pass
    return row,kind


def run():
    db.init()
    if db.setting(UPGRADE_KEY,False):
        print("AMC communication evidence repair already applied.")
        return True
    started=db.now();failures=[];promoted=[]
    for family,amc,label,url in TARGETS:
        try:
            row,kind=_validated_document(family,amc,label,url)
            with db.connect() as c:
                c.execute("""UPDATE documents SET kind=?,scope='AMC'
                             WHERE id=? AND origin='AMC'
                               AND kind IN ('source page','factsheet','disclosure','market view')""",
                          (kind,row["id"]))
            promoted.append((family,url))
        except Exception as exc:
            failures.append((str(exc) or type(exc).__name__).splitlines()[0][:300])

    iti=db.one("""SELECT COUNT(*) n FROM documents
                  WHERE family='Iti Small Cap Fund' AND origin='AMC'
                    AND kind='market view'
                    AND url IN (?,?,?)""",
               tuple(x[3] for x in TARGETS[:3]))
    mahindra=db.one("""SELECT COUNT(*) n FROM documents
                       WHERE family='Mahindra Manulife Small Cap Fund'
                         AND origin='AMC' AND kind='market view' AND url=?""",
                    (TARGETS[3][3],))
    kotak=db.one("""SELECT COUNT(*) n FROM documents
                    WHERE family='Kotak Small Cap Fund' AND origin='AMC'
                      AND kind IN ('market view','unitholder letter')
                      AND url LIKE 'https://www.mahindramanulife.com/%'""")
    success=bool(len(promoted)==4 and iti["n"]==3 and mahindra["n"]==1
                 and kotak["n"]==0 and not failures)
    detail=(f"AMC communications: promoted={len(promoted)}; "
            f"ITI={iti['n']}; Mahindra={mahindra['n']}; "
            f"Kotak-Mahindra cross-associations={kotak['n']}; "
            +"; ".join(failures))
    with db.connect() as c:
        c.execute("INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                  ("amc-communications",started,db.now(),"ok" if success else "partial",detail))
        if success:
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(UPGRADE_KEY,"true"))
    if success:
        print(detail,flush=True)
    else:
        print("::warning::AMC communication evidence repair incomplete; "+detail,flush=True)
    return success


if __name__=="__main__":
    raise SystemExit(0 if run() else 1)
