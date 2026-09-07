"""Run independent public-source updates, keeping previous data on source failures."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['SMALLCAP_NO_SCHEDULER']='1'
from tracker import db,disclosures
from tracker.sync import Updater


def run():
    db.init(recover=True);disclosures.seed_sources();u=Updater()
    # Discover new scheme identities before fetching the corresponding figures.
    u.run('nav')
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(u.run,['metrics','benchmark','documents']))
    jobs=db.rows('SELECT * FROM jobs ORDER BY id DESC LIMIT 4')
    print(json.dumps(jobs,indent=2))
    for job in jobs:
        if job['status'] in ('error','partial'):
            detail=(job['detail'] or '').splitlines()[0].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
            print('::warning title='+job['kind']+' coverage::'+detail)
    if not db.one('SELECT code FROM nav LIMIT 1'):raise RuntimeError('No NAV data is available to publish')
    # A failed source must not erase existing history or imply a fresh report.
    # Individual source errors and the last reporting dates are exported to UI.


if __name__=='__main__':run()
