"""Apply an AMC parser upgrade to the restored archive without replacing history.

Known official report URLs provide reproducible starting coverage. The daily
document collector discovers subsequent reports from their registered AMC pages.
"""
from pathlib import Path
import os
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db,providers,disclosures,amc_reports


def run():
    db.init();disclosures.seed_sources()
    from tracker import reviewed_reports
    print(f'{reviewed_reports.apply()} reviewed official figures retained with source notes',flush=True)
    key='amc_upgrade_'+amc_reports.PARSER_VERSION
    if db.setting(key,False):
        print('This AMC parser upgrade has already been applied; nightly discovery remains active.');return
    rows=json.loads((ROOT/'tracker/report_catalog.json').read_text())
    rows=[row for row in rows if amc_reports.parser_upgrade_applies(row['family'])]
    source_rows=json.loads((ROOT/'tracker/sources.json').read_text())
    # Thin split restores omit historical source binaries during normal runs.
    # Parser upgrades materialize only originals that can actually be read by
    # the catalog pass or this parser version's historical reprocessing pass.
    if os.environ.get('SMALLCAP_DATABASE_ONLY_RESTORE')=='1' and os.environ.get('GITHUB_REPOSITORY'):
        amc_reports.init();needed=set()
        for row in rows:
            existing=db.one("SELECT hash FROM fetches WHERE url=? AND status='ok' AND hash IS NOT NULL ORDER BY id DESC LIMIT 1",(row['url'],))
            if existing:needed.add(existing['hash'])
        pending=db.rows('''SELECT DISTINCT d.family,d.url,v.hash FROM documents d
          JOIN document_versions v ON v.document_id=d.id
          LEFT JOIN document_extractions e ON e.family=d.family AND e.hash=v.hash AND e.parser_version=?
          WHERE d.origin='AMC' AND e.hash IS NULL''',(amc_reports.PARSER_VERSION,))
        needed.update(row['hash'] for row in pending
                      if amc_reports.parser_upgrade_applies(row['family'])
                      and amc_reports.should_reprocess_existing(row['family'],row['url'],row['hash']))
        from scripts.github_state import materialize_hashes
        restored=materialize_hashes(needed)
        print(f'Materialized {restored} archived source files needed for parser upgrade',flush=True)
    def collect(row):
        try:
            url=row['url'];family=row['family']
            # Catalog is committed, reviewed configuration; it must still belong
            # to a registered AMC domain before any public request is made.
            amc=disclosures.resolve_registered_amc(row['amc'],source_rows)
            if amc is None:raise ValueError('Catalog AMC does not match registered source configuration: '+row['amc'])
            if not disclosures.official_publication_url(url,amc):raise ValueError('Unregistered AMC document host')
            with db.connect() as c:c.execute('INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)',(amc,url,'Official report archive'))
            existing=db.one('SELECT a.path,f.hash FROM fetches f JOIN archives a ON a.hash=f.hash WHERE f.url=? AND f.status=\'ok\' ORDER BY f.id DESC LIMIT 1',(url,))
            if existing:
                body=(db.DATA/existing['path']).read_bytes();h=existing['hash']
            else:providers.can_crawl(url);body,h,_=providers.fetch(url)
            did=providers.save_document(family,'Official '+providers.classify('',url),url,providers.classify('',url),'Fund');providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'{family}: {count} dated facts/holdings',flush=True)
            return True
        except Exception as e:
            print(f"::warning::{row['family']}: {(str(e) or type(e).__name__).splitlines()[0][:250]}",flush=True);return False
    with ThreadPoolExecutor(max_workers=2) as pool:ok=list(pool.map(collect,rows))
    # Dynamic AMC discovery is part of the immediately following daily
    # metrics collection. Parser upgrades only need to re-extract affected
    # archived/cataloged originals; do not crawl every AMC twice per push.
    checked,gaps=amc_reports.reprocess_archived()
    print(f'{sum(ok)}/{len(rows)} official report sources processed; {checked} existing documents rechecked; {len(gaps)} extraction errors')
    # A failed transfer/extraction is retried on the next build. Old facts remain.
    if all(ok) and not gaps:
        with db.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,'true'))


if __name__=='__main__':run()
