"""Apply an AMC parser upgrade to the restored archive without replacing history.

Known official report URLs provide reproducible starting coverage. The daily
document collector discovers subsequent reports from their registered AMC pages.
"""
from pathlib import Path
import os
import json
import re
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
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v57','amc-reports-2026-09-v58','amc-reports-2026-09-v61','amc-reports-2026-09-v62','amc-reports-2026-09-v63','amc-reports-2026-09-v64','amc-reports-2026-09-v65','amc-reports-2026-09-v66','amc-reports-2026-09-v67','amc-reports-2026-09-v68','amc-reports-2026-09-v69','amc-reports-2026-09-v70','amc-reports-2026-09-v71','amc-reports-2026-09-v72','amc-reports-2026-09-v73','amc-reports-2026-09-v74','amc-reports-2026-09-v75','amc-reports-2026-09-v76'):rows=[]
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v50':
        current_catalog={
            'https://www.abakkusmf.com/uploads/Abakkus_Fund_Spectrum_Sep_2026_0d434fa086.pdf',
            'https://mutualfund.adityabirlacapital.com/-/media/bsl/files/resources/factsheets/2026/absl-factsheet_sep-2026.pdf',
            'https://www.licmf.com/assets/downloads/monthly_fact_sheet/2026-2027/09/lic-mf-factsheet-31st-august-2026.pdf',
        }
        rows=[row for row in rows if row['url'] in current_catalog]
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
            path=urlparse(url).path.lower()
            if path.endswith('.pdf') and not body.startswith(b'%PDF'):
                raise ValueError('Official PDF URL returned non-PDF content; document association was not refreshed')
            if path.endswith(('.xlsx','.xls')) and not body.startswith((b'PK',b'\xd0\xcf')):
                raise ValueError('Official spreadsheet URL returned non-spreadsheet content; document association was not refreshed')
            did=providers.save_document(family,'Official '+providers.classify('',url),url,providers.classify('',url),'Fund');providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'{family}: {count} dated facts/holdings',flush=True)
            return True
        except Exception as e:
            print(f"::warning::{row['family']}: {(str(e) or type(e).__name__).splitlines()[0][:250]}",flush=True);return False
    with ThreadPoolExecutor(max_workers=2) as pool:ok=list(pool.map(collect,rows))
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v49':
        # Refresh the latest complete portfolios from current official sources.
        # Abakkus uses its disclosure-page discovery because the workbook name
        # is publisher-generated; HSBC and PGIM use reviewed August catalog URLs.
        try:
            from tracker import amc_discovery
            attempted=0
            for family,url,title in amc_discovery.discover('Abakkus'):
                attempted+=1
                try:
                    amc_discovery.store_report('Abakkus',family,url,title)
                except Exception as exc:
                    print(f"::warning::Abakkus current portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
                snap=db.one("SELECT as_of,complete FROM portfolios WHERE family=? ORDER BY as_of DESC,id DESC LIMIT 1",
                            ('Abakkus Small Cap Fund',))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:
                    break
            print(f'Abakkus current-source refresh: {attempted} candidate(s) attempted',flush=True)
        except Exception as exc:
            print(f"::warning::Abakkus current-source discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)

        for family in ('Abakkus Small Cap Fund','HSBC Small Cap Fund','Pgim India Small Cap Fund'):
            snap=db.one("SELECT as_of,complete FROM portfolios WHERE family=? ORDER BY as_of DESC,id DESC LIMIT 1",(family,))
            current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
            if current:
                print(f'{family}: current complete portfolio verified at {snap["as_of"]}',flush=True)
            else:
                detail='none' if not snap else f'{snap["as_of"]}, complete={snap["complete"]}'
                print(f'::warning::{family}: current complete portfolio not recovered; latest is {detail}',flush=True)
            ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v50':
        # Supersede v49 and refresh all six stale complete portfolios in one
        # release. Current HSBC/PGIM catalog URLs are processed above; Abakkus,
        # ABSL, Franklin and LIC require official archive-page discovery.
        from tracker import amc_discovery
        discovery_targets=(
            ('Abakkus','Abakkus Small Cap Fund'),
            ('Aditya Birla','Aditya Birla Sun Life Small Cap Fund'),
            ('Franklin','Franklin India Small Cap Fund'),
            ('HSBC','HSBC Small Cap Fund'),
            ('LIC','LIC Mf Small Cap Fund'),
            ('PGIM','Pgim India Small Cap Fund'),
        )
        for amc,family in discovery_targets:
            attempted=0
            try:
                for discovered_family,url,title in amc_discovery.discover(amc):
                    if discovered_family!=family:continue
                    attempted+=1
                    print(f'{family} current candidate #{attempted}: {url} · {title[:140]}',flush=True)
                    try:
                        records=amc_discovery.store_report(amc,family,url,title)
                        print(f'{family} current candidate #{attempted}: {records} dated facts/holdings parsed',flush=True)
                    except Exception as exc:
                        print(f"::warning::{family} current candidate #{attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
                    snap=db.one("SELECT as_of,complete FROM portfolios WHERE family=? ORDER BY as_of DESC,id DESC LIMIT 1",(family,))
                    if snap and snap['as_of']>='2026-08-31' and snap['complete']:break
                    if attempted>=4:break
            except Exception as exc:
                print(f"::warning::{family} current discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)

        required=(
            'Abakkus Small Cap Fund','Aditya Birla Sun Life Small Cap Fund',
            'Franklin India Small Cap Fund','HSBC Small Cap Fund',
            'LIC Mf Small Cap Fund','Pgim India Small Cap Fund',
        )
        for family in required:
            snap=db.one("SELECT as_of,complete FROM portfolios WHERE family=? ORDER BY as_of DESC,id DESC LIMIT 1",(family,))
            current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
            if current:print(f'{family}: current complete portfolio verified at {snap["as_of"]}',flush=True)
            else:
                detail='none' if not snap else f'{snap["as_of"]}, complete={snap["complete"]}'
                print(f'::warning::{family}: current complete portfolio not recovered; latest is {detail}',flush=True)
            ok.append(current)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v51','amc-reports-2026-09-v52'):
        from tracker import amc_discovery
        family='Groww Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('Groww'):
                if discovered_family!=family:continue
                attempted+=1
                try:amc_discovery.store_report('Groww',family,url,title)
                except Exception as exc:
                    print(f"::warning::Groww current monthly portfolio: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['positions']>=20:break
        except Exception as exc:
            print(f"::warning::Groww monthly portfolio discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']>=20)
        if current:
            print(f'Groww current portfolio verified at {snap["as_of"]}: {snap["positions"]} positions, complete={snap["complete"]}',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Groww current portfolio not recovered; latest is {detail}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v44':
        # One-time targeted recovery for TRUSTMF. The normal nightly collector
        # uses the same discovery path; this push replay proves and archives the
        # newly discovered official monthly disclosure without crawling all AMCs.
        try:
            from tracker import amc_discovery
            candidates=[row for row in amc_discovery.discover('TRUST')
                        if 'portfolio' in (row[2]+' '+row[1]).lower()]
            if not candidates:raise ValueError('TRUSTMF API returned no monthly portfolio candidate')
            parsed=0;attempted=0;failures=[]
            for family,url,title in candidates[:2]:
                attempted+=1
                try:
                    parsed+=amc_discovery.store_report('TRUST',family,url,title)
                    if parsed:break
                except Exception as exc:
                    failures.append((str(exc) or type(exc).__name__)[:180])
            if not parsed:
                raise ValueError('TRUSTMF monthly disclosure archived but yielded no supported holdings'
                                 + (': '+'; '.join(failures) if failures else ''))
            print(f'TRUSTMF API recovery: {parsed} dated facts/holdings from {attempted} candidate(s)',flush=True)
            ok.append(True)
        except Exception as exc:
            print(f"::warning::TRUSTMF API recovery: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
            ok.append(False)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v57','amc-reports-2026-09-v58'):
        from tracker import amc_discovery
        family='Aditya Birla Sun Life Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('Aditya Birla'):
                if discovered_family!=family or not re.search(r'\.zip(?:[?#]|$)',url,re.I):continue
                attempted+=1
                try:
                    records=amc_discovery.store_report('Aditya Birla',family,url,title)
                    print(f'ABSL current monthly portfolio: {records} dated facts/holdings parsed from {url}',flush=True)
                except Exception as exc:
                    print(f"::warning::ABSL current monthly portfolio: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:break
        except Exception as exc:
            print(f"::warning::ABSL monthly portfolio discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:220]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:
            print(f'ABSL current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::ABSL current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v73':
        from tracker import amc_discovery
        family='Pgim India Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('PGIM'):
                if discovered_family!=family:continue
                attempted+=1
                try:
                    records=amc_discovery.store_report('PGIM',family,url,title)
                    print(f'PGIM v73 monthly portfolio: {records} dated facts/holdings parsed from {url}',flush=True)
                except Exception as exc:
                    print(f"::warning::PGIM v73 portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:break
        except Exception as exc:
            print(f"::warning::PGIM v73 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'PGIM current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::PGIM current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v76':
        from tracker import amc_discovery
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin,urlparse
        family='Abakkus Small Cap Fund';attempted=0
        page='https://www.abakkusmf.com/statutory-disclosures.html'
        try:
            providers.can_crawl(page)
            raw,_,mime=providers.fetch(page,max_bytes=10*1024*1024)
            print(f'ABAKKUS_V74_PAGE bytes={len(raw)} mime={mime}',flush=True)
            soup=BeautifulSoup(raw,'html.parser')
            for index,select in enumerate(soup.find_all('select')):
                meta={k:(' '.join(v) if isinstance(v,list) else str(v)) for k,v in select.attrs.items()}
                opts=[]
                for option in select.find_all('option')[:40]:
                    opts.append({'value':option.get('value'),'text':option.get_text(' ',strip=True)})
                if any(re.search(r'portfolio|month|year|disclosure',str(x),re.I) for x in [meta,opts]):
                    print('ABAKKUS_V74_SELECT '+json.dumps({'index':index,'attrs':meta,'options':opts},ensure_ascii=False)[:10000],flush=True)
            txt=raw.decode('utf-8','ignore')
            found=set()
            for m in re.finditer(r"(?:https?://[^\\\"'<>\\s]+|/[^\\\"'<>\\s]+)\\.(?:xlsx?|pdf)(?:\\?[^\\\"'<>\\s]*)?",txt,re.I):
                url=urljoin(page,m.group(0).replace('&amp;','&'))
                ctx=re.sub(r'\s+',' ',txt[max(0,m.start()-260):m.end()+260]).strip()
                if url in found:continue
                found.add(url)
                if re.search(r'portfolio|monthly|aug|31|small.?cap',ctx+' '+url,re.I):
                    print('ABAKKUS_V74_EMBED '+url+' :: '+ctx[:1200],flush=True)
            for tag in soup.find_all('script'):
                src=tag.get('src')
                if src:
                    url=urljoin(page,src)
                    if urlparse(url).netloc.endswith('abakkusmf.com'):
                        print('ABAKKUS_V74_SCRIPT '+url,flush=True)
            for discovered_family,url,title in amc_discovery.discover('Abakkus'):
                if discovered_family!=family:continue
                attempted+=1
                print(f'ABAKKUS_V74_CANDIDATE {attempted} {url} :: {title}',flush=True)
                try:
                    providers.can_crawl(url)
                    body,h,cmime=providers.fetch(url,max_bytes=70*1024*1024)
                    print(f'ABAKKUS_V74_FETCH {attempted} bytes={len(body)} mime={cmime} sig={body[:16].hex()}',flush=True)
                    count=amc_reports.extract(body,family,url,h)
                    print(f'ABAKKUS_V74_PARSED {attempted} count={count}',flush=True)
                except Exception as exc:
                    print(f"::warning::Abakkus v74 candidate {attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap:
                    print(f'ABAKKUS_V74_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:break
        except Exception as exc:
            print(f"::warning::Abakkus v74 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'Abakkus current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Abakkus current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    # Dynamic AMC discovery is part of the immediately following daily
    # metrics collection. Parser upgrades only need to re-extract affected
    # archived/cataloged originals; do not crawl every AMC twice per push.
    checked,gaps=amc_reports.reprocess_archived()
    print(f'{sum(ok)}/{len(rows)} official report sources processed; {checked} existing documents rechecked; {len(gaps)} extraction errors')
    # Most parser upgrades retry failed transfers on the next push. Union v45
    # is a completed transport audit: all reviewed official routes were tried,
    # while the normal nightly discovery path continues retrying the live source.
    transport_audit_complete=(amc_reports.PARSER_VERSION=='amc-reports-2026-09-v45' and not gaps)
    if (all(ok) or transport_audit_complete) and not gaps:
        with db.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,'true'))


if __name__=='__main__':run()
