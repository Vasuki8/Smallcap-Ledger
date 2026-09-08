from __future__ import annotations
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone,timedelta
from . import db,providers,disclosures,amfi_metrics,amc_metrics

class Updater:
    def __init__(self):
        self.lock=threading.Lock();self.running={};self.stop=threading.Event()

    def status(self):
        with self.lock: return {k:dict(v) for k,v in self.running.items()}

    def progress(self,kind,detail):
        with self.lock:
            if kind in self.running: self.running[kind]["detail"]=detail

    def launch(self,kind):
        if kind not in ("nav","benchmark","documents","metrics"): raise ValueError("Unknown update type")
        with self.lock:
            if kind in self.running: return False
            self.running[kind]={"detail":"Starting update","started_at":db.now()}
        threading.Thread(target=self.run,args=(kind,),daemon=True,name='update-'+kind).start()
        return True

    def run(self,kind):
        errors=[];detail=""
        with db.connect() as c:
            jid=c.execute("INSERT INTO jobs(kind,started_at,status) VALUES(?,?,'running')",(kind,db.now())).lastrowid
        try:
            if kind=="nav":
                self.progress(kind,"Checking the official AMFI small-cap category")
                detail=providers.latest_nav()
                # Backfill all available dates once daily, including dates missed while the computer was off.
                cutoff=datetime.now(timezone.utc).date().isoformat()
                schemes=db.rows("SELECT code,family FROM schemes WHERE history_checked IS NULL OR history_status LIKE 'Error:%' OR substr(history_checked,1,10)<? ORDER BY CASE option WHEN 'Growth' THEN 0 ELSE 1 END,code",(cutoff,))
                with ThreadPoolExecutor(max_workers=3) as pool:
                    futures={pool.submit(providers.backfill,x['code']):x for x in schemes}
                    for i,f in enumerate(as_completed(futures),1):
                        self.progress(kind,f"Historical NAV {i}/{len(schemes)} · {futures[f]['family']}")
                        try: f.result()
                        except Exception as e: errors.append(f"{futures[f]['code']}: {str(e)[:160]}")
                detail+=f"; {len(schemes)-len(errors)}/{len(schemes)} histories updated"
            elif kind=="benchmark":
                detail=providers.fetch_benchmark(lambda msg:self.progress(kind,msg))
            elif kind=="metrics":
                results=[]
                for operation in (amfi_metrics.fees,amc_metrics.update):
                    try:results.append(operation(lambda msg:self.progress(kind,msg)))
                    except Exception as e:errors.append(str(e)[:250])
                detail='; '.join(results)
            else:
                from .amc_reports import reprocess_archived
                self.progress(kind,'Updating parsers for previously archived official reports')
                _,parse_gaps=reprocess_archived();errors.extend(parse_gaps)
                sources=db.rows("SELECT * FROM source_pages WHERE enabled=1 ORDER BY COALESCE(last_checked,''),id")
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures={pool.submit(disclosures.ingest_source,x):x for x in sources}
                    for i,f in enumerate(as_completed(futures),1):
                        s=futures[f];self.progress(kind,f"Fund disclosures {i}/{len(sources)} · {s['amc_match']}")
                        try:
                            msg=f.result();status="Checked"
                            if msg.startswith('Excluded:'):status='Excluded'
                            elif 'no automatically readable' in msg or 'No matching' in msg:status='Limited'
                            elif not msg.endswith('; 0 download/parser gaps'):status='Partial';errors.append(s['amc_match']+': '+msg)
                        except Exception as e: status="Gap";msg=str(e)[:350];errors.append(s['amc_match']+": "+msg)
                        with db.connect() as c: c.execute("UPDATE source_pages SET last_checked=?,status=?,detail=? WHERE id=?",(db.now(),status,msg,s['id']))
                detail=f"{len(sources)} source pages checked; {len(errors)} unavailable sources"
            status="partial" if errors else "ok"
        except Exception as e:
            status="error";detail=str(e)[:500]
        finally:
            with db.connect() as c:
                c.execute("UPDATE jobs SET finished_at=?,status=?,detail=? WHERE id=?",(db.now(),status,detail+("\n"+"\n".join(errors) if errors else ""),jid))
            with self.lock: self.running.pop(kind,None)

    def schedule(self):
        while not self.stop.is_set():
            if db.setting("auto_update",True):
                intervals={"nav":db.setting("nav_interval_minutes",60)*60,"benchmark":6*3600,"metrics":12*3600,
                           "documents":db.setting("disclosure_interval_hours",12)*3600}
                has_funds=bool(db.one("SELECT code FROM schemes LIMIT 1"))
                for kind,seconds in intervals.items():
                    if kind in ('documents','metrics') and not has_funds: continue
                    previous=db.one("SELECT finished_at,status FROM jobs WHERE kind=? AND finished_at IS NOT NULL ORDER BY id DESC LIMIT 1",(kind,))
                    # Failed sources retry with bounded backoff, retaining all previous observations.
                    due=not previous or previous['status']=='interrupted' or (datetime.now(timezone.utc)-datetime.fromisoformat(previous['finished_at'])).total_seconds()> (min(seconds,1800) if previous['status']=='error' else seconds)
                    if due:self.launch(kind)
            self.stop.wait(15)

    def start(self):
        threading.Thread(target=self.schedule,daemon=True,name="schedule").start()

updater=Updater()

if __name__=="__main__":
    import argparse,time
    parser=argparse.ArgumentParser();parser.add_argument("kinds",nargs="*",default=["nav","benchmark","documents","metrics"])
    args=parser.parse_args();db.init();disclosures.seed_sources()
    for kind in args.kinds:
        updater.launch(kind)
    while updater.status():
        print(json.dumps(updater.status()),flush=True)
        updater.stop.wait(10)
    print(json.dumps(db.rows("SELECT kind,status,substr(detail,1,300) detail FROM jobs ORDER BY id DESC LIMIT 4")),flush=True)
