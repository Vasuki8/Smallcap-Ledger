"""Retry exact retained AMC communication URLs that have no archived original.

This is deliberately narrower than discovery: only existing AMC-origin market-view
or unitholder-letter records for reviewed repairable families are eligible.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys
from urllib.parse import quote,unquote,urlparse,urlunparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers
from tracker.disclosures import official_publication_url

FAMILIES=(
    ("LIC Mf Small Cap Fund","LIC"),
    ("Nippon India Small Cap Fund","Nippon"),
    ("Samco Small Cap Fund","Samco"),
)
PER_FAMILY_LIMIT=40
REPORT=ROOT/"deployment"/"communication-archive-repair.json"


def missing(family):
    return db.rows(
        """SELECT d.id,d.family,d.title,d.kind,d.url,d.published_at,d.last_seen
           FROM documents d
           WHERE d.family=? AND d.origin='AMC'
             AND d.kind IN ('market view','unitholder letter')
             AND NOT EXISTS (
               SELECT 1 FROM document_versions v WHERE v.document_id=d.id
             )
           ORDER BY COALESCE(d.published_at,d.last_seen,'') DESC,d.id DESC
           LIMIT ?""",
        (family,PER_FAMILY_LIMIT),
    )


def canonical_fetch_url(url):
    """Encode unsafe path characters for the request without changing document identity."""
    parsed=urlparse(url)
    path=quote(unquote(parsed.path),safe="/._-()")
    return urlunparse((parsed.scheme,parsed.netloc,path,parsed.params,parsed.query,parsed.fragment))


def _looks_valid(url,body,media_type):
    if not body:return False
    path=urlparse(url).path.lower()
    typ=str(media_type or "").lower()
    stripped=body.lstrip()
    if path.endswith(".pdf") or "pdf" in typ:
        return stripped.startswith(b"%PDF")
    if path.endswith((".pptx",".xlsx",".docx")):
        return body.startswith(b"PK")
    if path.endswith((".ppt",".xls",".doc")):
        return body.startswith(bytes.fromhex("D0CF11E0"))
    if path.endswith((".html",".htm")) or "html" in typ:
        low=stripped[:2048].lower()
        return low.startswith(b"<!doctype") or b"<html" in low or b"<body" in low
    if stripped.startswith(b"%PDF") or body.startswith(b"PK") or body.startswith(bytes.fromhex("D0CF11E0")):
        return True
    low=stripped[:2048].lower()
    return ("html" in typ and b"<" in low) or b"<html" in low


def repair(fetch_fn=providers.fetch,can_crawl_fn=providers.can_crawl):
    db.init()
    report={"families":{},"repaired":0,"failed":0,"skipped":0}
    for family,amc in FAMILIES:
        before=missing(family)
        repaired=[];failed=[];skipped=[]
        for row in before:
            url=row["url"]
            if not official_publication_url(url,amc):
                skipped.append({"url":url,"reason":"not a reviewed first-party AMC URL"})
                continue
            try:
                request_url=canonical_fetch_url(url)
                can_crawl_fn(request_url)
                body,_,typ=fetch_fn(request_url,archive=False,max_bytes=20*1024*1024)
                if not _looks_valid(url,body,typ):
                    raise ValueError("response did not validate as an expected document/page")
                h=db.archive(body,typ)
                with db.connect() as conn:
                    conn.execute(
                        "INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",
                        (request_url,db.now(),"ok",h),
                    )
                providers.doc_version(row["id"],h)
                repaired.append({"url":url,"request_url":request_url,"hash":h})
            except Exception as exc:
                failed.append({
                    "url":url,
                    "error":(str(exc) or type(exc).__name__).splitlines()[0][:300],
                })
        remaining=len(missing(family))
        report["families"][family]={
            "before":len(before),
            "repaired":len(repaired),
            "failed":len(failed),
            "skipped":len(skipped),
            "remaining":remaining,
            "repaired_rows":repaired,
            "failed_rows":failed,
            "skipped_rows":skipped,
        }
        report["repaired"]+=len(repaired)
        report["failed"]+=len(failed)
        report["skipped"]+=len(skipped)

    detail="; ".join(
        f"{family}: before={x['before']} repaired={x['repaired']} remaining={x['remaining']}"
        for family,x in report["families"].items()
    )
    with db.connect() as c:
        c.execute(
            "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
            (
                "amc-communication-archive-repair",
                db.now(),db.now(),
                "ok" if report["failed"]==0 and report["skipped"]==0 else "partial",
                detail,
            ),
        )
    print(detail,flush=True)
    return report


def write_report(report,path=REPORT):
    payload=dict(report)
    payload["prepared_at"]=db.now()
    payload["mode"]="exact_retained_urls_best_effort"
    payload["scope"]=[family for family,_ in FAMILIES]
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path


def main():
    result=repair()
    path=write_report(result)
    print("Wrote",path,flush=True)
    # This repair is best-effort: one stale/blocked historical URL must not stop
    # publication, and successful repairs remain retained.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
