"""Read-only retained-evidence probe for ITI and Mahindra AMC communications."""
from pathlib import Path
import json
import sys
from urllib.parse import unquote

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db, providers
from tracker.publications import exclusion_reason

TARGETS={
    "Iti Small Cap Fund":("ITI",[
        "https://www.itiamc.com/digitalfactsheet/July2026/CEO.html",
        "https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html",
        "https://www.itiamc.com/digitalfactsheet/July2026/debt-update.html",
    ]),
    "Mahindra Manulife Small Cap Fund":("Mahindra",[
        "https://www.mahindramanulife.com/digital-factsheet/july-2026/Outlook.html",
    ]),
}

def latest_version(family,url):
    return db.one("""SELECT d.id,d.title,d.kind,d.scope,d.url,d.published_at,d.first_seen,d.last_seen,
                            v.hash,v.observed_at,a.media_type,a.bytes,
                            COALESCE(r.binary_state,'retained') binary_state
                     FROM documents d
                     LEFT JOIN document_versions v ON v.id=(
                       SELECT id FROM document_versions
                       WHERE document_id=d.id ORDER BY observed_at DESC,id DESC LIMIT 1)
                     LEFT JOIN archives a ON a.hash=v.hash
                     LEFT JOIN archive_retention r ON r.hash=v.hash
                     WHERE d.family=? AND d.url=?""",(family,url))

def show_page(family,amc,url):
    row=latest_version(family,url)
    print("COMM_SOURCE",family,json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
    if not row or not row.get("hash"):return
    path=db.archive_binary_path(row["hash"])
    if not path:
        print("COMM_SOURCE_BINARY_UNAVAILABLE",family,url,flush=True);return
    body=path.read_bytes()
    try:
        soup=BeautifulSoup(body,"html.parser")
    except Exception as exc:
        print("COMM_SOURCE_PARSE_ERROR",family,url,type(exc).__name__,str(exc)[:300],flush=True);return
    title=(soup.title.get_text(" ",strip=True) if soup.title else "")
    text=" ".join(soup.stripped_strings)
    print("COMM_SOURCE_PAGE",family,"title="+repr(title[:300]),"text="+repr(text[:1800]),flush=True)
    links=providers.candidate_links(soup,url)
    for target,label in links.items():
        combined=unquote((label or "")+" "+target)
        if not providers.official_publication_url(target,amc):continue
        if exclusion_reason(amc,target,label):continue
        relevant=providers.classify(label,target) in ("market view","unitholder letter")
        keywords=any(k in combined.lower() for k in (
            "outlook","market update","equity update","debt update","newsletter",
            "unitholder","cio","investment view","small cap","factsheet","portfolio"))
        if not relevant and not keywords:continue
        linked=latest_version(family,target)
        print("COMM_LINK",family,json.dumps({
            "label":label,
            "url":target,
            "classifier":providers.classify(label,target),
            "retained_document":linked,
        },ensure_ascii=False,sort_keys=True),flush=True)

def main():
    db.init()
    for family,(amc,urls) in TARGETS.items():
        print("COMM_FAMILY",family,flush=True)
        docs=db.rows("""SELECT d.id,d.title,d.kind,d.scope,d.url,d.published_at,
                               d.first_seen,d.last_seen,COUNT(v.id) versions,
                               MAX(v.observed_at) latest_observed_at
                        FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                        WHERE d.family=?
                        GROUP BY d.id ORDER BY d.id""",(family,))
        for row in docs:
            if row["url"] in urls or row["kind"] in ("market view","unitholder letter"):
                print("COMM_DOC",family,json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
        for url in urls:show_page(family,amc,url)

if __name__=="__main__":
    main()
