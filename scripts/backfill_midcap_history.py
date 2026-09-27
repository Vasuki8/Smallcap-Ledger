"""Backfill historical NAV into the isolated Mid Cap staging store."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers

MFAPI=providers.MFAPI


def due_for_history(row, *, now=None, refresh_days=30):
    """Refresh new/error rows immediately and healthy rows at a bounded cadence."""
    status=str(row.get("history_status") or "")
    checked=row.get("history_checked")
    if not checked or status.startswith("Error:"):
        return True
    now=now or datetime.now(timezone.utc)
    try:
        observed=datetime.fromisoformat(str(checked))
    except ValueError:
        return True
    if observed.tzinfo is None:
        observed=observed.replace(tzinfo=timezone.utc)
    return now-observed>=timedelta(days=refresh_days)


def fetch_history(row, fetch_fn=providers.fetch):
    code=int(row["code"])
    url=f"{MFAPI}/{code}"
    body,_,_=fetch_fn(url,archive=False,max_bytes=12*1024*1024)
    payload=json.loads(body.decode("utf-8","replace"))
    meta=payload.get("meta") or {}
    if int(meta.get("scheme_code") or 0)!=code:
        raise ValueError(f"Provider returned a different scheme code for {code}")
    category=str(meta.get("scheme_category") or "")
    if "mid cap" not in category.lower():
        raise ValueError(f"Provider category is not Mid Cap for {code}")
    points={}
    for item in payload.get("data") or []:
        day=providers.iso(item["date"])
        value=providers.number(item["nav"])
        if value>0 and day<=date.today().isoformat():
            points[day]=value
    if not points:
        raise ValueError(f"No historical NAV returned for {code}")
    return url,hashlib.sha256(body).hexdigest(),sorted(points.items()),meta


def backfill(*, fetch_fn=providers.fetch, now=None, refresh_days=30):
    db.init()
    candidates=db.rows("""SELECT code,family,history_checked,history_status
      FROM category_staged_schemes WHERE category='mid-cap' ORDER BY code""")
    selected=[row for row in candidates if due_for_history(row,now=now,refresh_days=refresh_days)]
    succeeded=0;failed=[];inserted=0;observed=db.now()
    for row in selected:
        code=int(row["code"])
        try:
            url,source_hash,points,meta=fetch_history(row,fetch_fn=fetch_fn)
            with db.connect() as conn:
                before=conn.execute(
                    "SELECT COUNT(*) FROM category_staged_nav WHERE code=?",(code,)).fetchone()[0]
                # Preserve an already-staged AMFI observation for the same date. Historical
                # provider data fills missing dates only; it never overwrites AMFI evidence.
                conn.executemany("""INSERT OR IGNORE INTO category_staged_nav(
                    code,date,value,source_url,source_sha256,observed_at)
                    VALUES(?,?,?,?,?,?)""",
                    [(code,day,value,url,source_hash,observed) for day,value in points])
                after=conn.execute(
                    "SELECT COUNT(*) FROM category_staged_nav WHERE code=?",(code,)).fetchone()[0]
                metadata=json.loads(conn.execute(
                    "SELECT metadata_json FROM category_staged_schemes WHERE code=?",(code,)
                ).fetchone()[0] or "{}")
                metadata["history_meta"]={
                    "scheme_name":meta.get("scheme_name"),
                    "scheme_category":meta.get("scheme_category"),
                    "scheme_type":meta.get("scheme_type"),
                }
                conn.execute("""UPDATE category_staged_schemes
                  SET history_checked=?,history_status=?,history_source=?,metadata_json=?
                  WHERE code=?""",
                  (observed,f"{len(points)} NAV observations",url,
                   json.dumps(metadata,separators=(",",":")),code))
                inserted+=after-before
            succeeded+=1
        except Exception as exc:
            failed.append({"code":code,"error":(str(exc) or type(exc).__name__)[:250]})
            with db.connect() as conn:
                conn.execute("""UPDATE category_staged_schemes
                  SET history_checked=?,history_status=? WHERE code=?""",
                  (observed,"Error: "+(str(exc) or type(exc).__name__)[:200],code))
    summary=db.one("""SELECT COUNT(*) observations,COUNT(DISTINCT code) scheme_codes,
      MIN(date) first_date,MAX(date) last_date FROM category_staged_nav""")
    return {
        "staged_category":"mid-cap",
        "scheme_codes":len(candidates),
        "selected_for_history":len(selected),
        "history_succeeded":succeeded,
        "history_failed":len(failed),
        "new_nav_rows":inserted,
        "nav_observations":summary["observations"] if summary else 0,
        "nav_scheme_codes":summary["scheme_codes"] if summary else 0,
        "nav_first_date":summary["first_date"] if summary else None,
        "nav_last_date":summary["last_date"] if summary else None,
        "failures":failed,
        "live_writes":0,
        "public_export_enabled":False,
        "observed_at":observed,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--refresh-days",type=int,default=30)
    args=parser.parse_args(argv)
    result=backfill(refresh_days=args.refresh_days)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result["history_failed"]==0 else 1


if __name__=="__main__":
    raise SystemExit(main())
