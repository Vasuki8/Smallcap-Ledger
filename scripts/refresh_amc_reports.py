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
from urllib.parse import urlparse,urljoin

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
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v57','amc-reports-2026-09-v58','amc-reports-2026-09-v61','amc-reports-2026-09-v62','amc-reports-2026-09-v63','amc-reports-2026-09-v64','amc-reports-2026-09-v65','amc-reports-2026-09-v66','amc-reports-2026-09-v67','amc-reports-2026-09-v68','amc-reports-2026-09-v69','amc-reports-2026-09-v70','amc-reports-2026-09-v71','amc-reports-2026-09-v72','amc-reports-2026-09-v73','amc-reports-2026-09-v74','amc-reports-2026-09-v75','amc-reports-2026-09-v76','amc-reports-2026-09-v77','amc-reports-2026-09-v78','amc-reports-2026-09-v79','amc-reports-2026-09-v80','amc-reports-2026-09-v81','amc-reports-2026-09-v82','amc-reports-2026-09-v83','amc-reports-2026-09-v84','amc-reports-2026-09-v85','amc-reports-2026-09-v86','amc-reports-2026-09-v87','amc-reports-2026-09-v88','amc-reports-2026-09-v89','amc-reports-2026-09-v90','amc-reports-2026-09-v91','amc-reports-2026-09-v92','amc-reports-2026-09-v93','amc-reports-2026-09-v94','amc-reports-2026-09-v95','amc-reports-2026-09-v96','amc-reports-2026-09-v97','amc-reports-2026-09-v98','amc-reports-2026-09-v99','amc-reports-2026-09-v100','amc-reports-2026-09-v101','amc-reports-2026-09-v102','amc-reports-2026-09-v103','amc-reports-2026-09-v105','amc-reports-2026-09-v106','amc-reports-2026-09-v107','amc-reports-2026-09-v108','amc-reports-2026-09-v109','amc-reports-2026-09-v110','amc-reports-2026-09-v111','amc-reports-2026-09-v112','amc-reports-2026-09-v113','amc-reports-2026-09-v114','amc-reports-2026-09-v115','amc-reports-2026-09-v116','amc-reports-2026-09-v117','amc-reports-2026-09-v118','amc-reports-2026-09-v119','amc-reports-2026-09-v120','amc-reports-2026-09-v121','amc-reports-2026-09-v122','amc-reports-2026-09-v123','amc-reports-2026-09-v124','amc-reports-2026-09-v125','amc-reports-2026-09-v126','amc-reports-2026-09-v127'):rows=[]
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
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v78':
        from tracker import amc_discovery
        family='Abakkus Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('Abakkus'):
                if discovered_family!=family:continue
                attempted+=1
                try:
                    records=amc_discovery.store_report('Abakkus',family,url,title)
                    print(f'Abakkus current monthly portfolio: {records} dated facts/holdings parsed from {url}',flush=True)
                except Exception as exc:
                    print(f"::warning::Abakkus current monthly portfolio: {(str(exc) or type(exc).__name__).splitlines()[0][:240]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:break
                if attempted>=3:break
        except Exception as exc:
            print(f"::warning::Abakkus v78 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:260]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'Abakkus current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Abakkus current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v79':
        from tracker import amc_discovery
        from bs4 import BeautifulSoup

        family='Franklin India Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('Franklin'):
                if discovered_family!=family:continue
                attempted+=1
                print(f'FRANKLIN_V79_CANDIDATE {attempted} {url} :: {title}',flush=True)
                try:
                    providers.can_crawl(url)
                    body,h,mime=providers.fetch(url,max_bytes=70*1024*1024)
                    print(f'FRANKLIN_V79_FETCH {attempted} bytes={len(body)} mime={mime} sig={body[:16].hex()}',flush=True)
                    count=amc_reports.extract(body,family,url,h)
                    print(f'FRANKLIN_V79_PARSED {attempted} count={count}',flush=True)
                except Exception as exc:
                    print(f"::warning::Franklin v79 candidate {attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        except Exception as exc:
            print(f"::warning::Franklin v79 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)

        for page in (
            'https://www.franklintempletonindia.com/fund-details/fund-overview/4373/franklin-india-small-cap-fund-erstwhile-franklin-india-smaller-companies-fund',
            'https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html',
        ):
            try:
                providers.can_crawl(page)
                raw,_,mime=providers.fetch(page,max_bytes=12*1024*1024)
                txt=raw.decode('utf-8','ignore')
                print(f'FRANKLIN_V79_PAGE {page} bytes={len(raw)} mime={mime}',flush=True)
                soup=BeautifulSoup(raw,'html.parser')
                links=providers.candidate_links(soup,page)
                for u,title in list(links.items()):
                    joined=(u+' '+str(title))
                    if re.search(r'portfolio|monthly|holding|xlsx?|xls|download|factsheet|as.on',joined,re.I):
                        print('FRANKLIN_V79_LINK '+u+' :: '+str(title)[:500],flush=True)
                flat=re.sub(r'\\s+',' ',soup.get_text(' ',strip=True))
                for pat in (r'As on[^<]{0,80}',r'Company Name[^<]{0,120}',r'Portfolio[^<]{0,160}',r'August[^<]{0,100}',r'July[^<]{0,100}'):
                    for hit in re.findall(pat,flat,re.I)[:12]:
                        print('FRANKLIN_V79_TEXT '+str(hit)[:700],flush=True)
                for tag in soup.find_all('script'):
                    src=tag.get('src')
                    body=(tag.string or tag.get_text('',strip=False) or '')
                    if src and urlparse(urljoin(page,src)).netloc.endswith('franklintempletonindia.com'):
                        print('FRANKLIN_V79_SCRIPT '+urljoin(page,src),flush=True)
                    elif body and re.search(r'portfolio|holding|download|factsheet|fund-overview|api',body,re.I):
                        snippet=re.sub(r'\\s+',' ',body).strip()
                        print('FRANKLIN_V79_INLINE '+snippet[:3000],flush=True)
            except Exception as exc:
                print(f"::warning::Franklin v79 page audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)

        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'Franklin current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Franklin current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v80':
        family='Franklin India Small Cap Fund'
        url='https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html'
        try:
            providers.can_crawl(url)
            body,h,_=providers.fetch(url,max_bytes=12*1024*1024)
            did=providers.save_document(family,'Franklin India Small Cap Fund current digital factsheet',url,'factsheet','Fund',origin='AMC')
            providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'Franklin v80 current HTML: {count} dated facts/holdings',flush=True)
        except Exception as exc:
            print(f"::warning::Franklin v80 current HTML: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'Franklin current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Franklin current complete portfolio not recovered; latest is {detail}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v81':
        from bs4 import BeautifulSoup
        family='Franklin India Small Cap Fund'
        url='https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html'
        try:
            providers.can_crawl(url)
            body,_,_=providers.fetch(url,max_bytes=12*1024*1024)
            soup=BeautifulSoup(body,'html.parser')
            matched=0
            for ti,table in enumerate(soup.select('table')):
                tx=re.sub(r'\\s+',' ',table.get_text(' ',strip=True))
                if not (re.search(r'Company Name',tx,re.I) and re.search(r'Market Value',tx,re.I) and re.search(r'% of',tx,re.I)):
                    continue
                matched+=1
                print(f'FRANKLIN_V81_TABLE index={ti} rows={len(table.select("tr"))} text={tx[:500]}',flush=True)
                for ri,row in enumerate(table.select('tr')):
                    cells=[c.get_text(' ',strip=True) for c in row.find_all(['td','th'],recursive=False)]
                    joined=' | '.join(cells)
                    if (ri<5 or len(cells)!=4 or re.search(r'Total|Company Name|Margin|cash|DTB|SOVEREIGN',joined,re.I)):
                        print('FRANKLIN_V81_ROW '+json.dumps({'table':ti,'row':ri,'len':len(cells),'cells':cells},ensure_ascii=False)[:3000],flush=True)
            print(f'FRANKLIN_V81_MATCHED {matched}',flush=True)
        except Exception as exc:
            print(f"::warning::Franklin v81 diagnostic: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v82':
        family='Franklin India Small Cap Fund'
        url='https://www.franklintempletonindia.com/static/factsheet/Innerpage/Franklin-India-Smaller-Companies-Fund.html'
        try:
            providers.can_crawl(url)
            body,h,_=providers.fetch(url,max_bytes=12*1024*1024)
            did=providers.save_document(family,'Franklin India Small Cap Fund current digital factsheet',url,'factsheet','Fund',origin='AMC')
            providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'Franklin v82 current HTML: {count} dated facts/holdings',flush=True)
        except Exception as exc:
            print(f"::warning::Franklin v82 current HTML: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
        if current:print(f'Franklin current complete portfolio verified at {snap["as_of"]}: {snap["positions"]} positions',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Franklin current complete portfolio not recovered; latest is {detail}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v83':
        from bs4 import BeautifulSoup

        family='Bajaj Finserv Small Cap Fund'
        pages=(
            'https://www.bajajamc.com/mutual-funds/equity-funds/bajaj-finserv-small-cap-fund',
            'https://www.bajajamc.com/downloads?factsheet',
            'https://www.bajajamc.com/downloads',
        )
        for page in pages:
            try:
                providers.can_crawl(page)
                raw,_,mime=providers.fetch(page,max_bytes=12*1024*1024)
                print(f'BAJAJ_V83_PAGE {page} bytes={len(raw)} mime={mime}',flush=True)
                soup=BeautifulSoup(raw,'html.parser')
                links=providers.candidate_links(soup,page)
                for url,title in links.items():
                    joined=(url+' '+str(title))
                    if re.search(r'small\s*cap|factsheet|portfolio|monthly|2026|pdf|xlsx?',joined,re.I):
                        print('BAJAJ_V83_LINK '+url+' :: '+str(title)[:700],flush=True)
                for tag in soup.find_all('script'):
                    src=tag.get('src')
                    body=(tag.string or tag.get_text('',strip=False) or '')
                    if src:
                        u=urljoin(page,src)
                        if 'bajajamc.com' in u:print('BAJAJ_V83_SCRIPT '+u,flush=True)
                    elif body and re.search(r'factsheet|portfolio|download|small.?cap|api',body,re.I):
                        snippet=re.sub(r'\s+',' ',body).strip()
                        print('BAJAJ_V83_INLINE '+snippet[:3500],flush=True)
            except Exception as exc:
                print(f"::warning::Bajaj v83 page {page}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        # Audit only the same first-party media naming family already retained;
        # do not store guessed URLs unless they return a genuine PDF.
        for month in ('September','Sep'):
            url=f'https://media.bajajamc.com/wp-content/uploads/2026/02/Bajaj-Finserv-Small-Cap-Fund_{month}-2026.pdf'
            try:
                providers.can_crawl(url)
                body,h,mime=providers.fetch(url,max_bytes=40*1024*1024)
                print(f'BAJAJ_V83_MEDIA {url} bytes={len(body)} mime={mime} sig={body[:16].hex()}',flush=True)
                if body.startswith(b'%PDF'):
                    count=amc_reports.extract(body,family,url,h)
                    print(f'BAJAJ_V83_MEDIA_PARSED {count}',flush=True)
            except Exception as exc:
                print(f"::warning::Bajaj v83 media {month}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
        print(f'BAJAJ_V83_SNAPSHOT {detail}',flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v84','amc-reports-2026-09-v85','amc-reports-2026-09-v86','amc-reports-2026-09-v88'):
        from tracker import amc_discovery
        family='DSP Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('DSP'):
                if discovered_family!=family:continue
                attempted+=1
                try:
                    records=amc_discovery.store_report('DSP',family,url,title)
                    print(f'DSP current month-end portfolio: {records} dated facts/holdings parsed from {url}',flush=True)
                except Exception as exc:
                    print(f"::warning::DSP current month-end portfolio: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['positions']>=20:break
        except Exception as exc:
            print(f"::warning::DSP month-end discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']>=20)
        if current:print(f'DSP current portfolio verified at {snap["as_of"]}: {snap["positions"]} positions, complete={snap["complete"]}',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::DSP current portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v87':
        from tracker import amc_discovery
        family='DSP Small Cap Fund'
        try:
            import io,zipfile,openpyxl,xlrd
            from pathlib import PurePosixPath
            from tracker.portfolio_parser import parse_sheet
            candidate=next((row for row in amc_discovery.discover('DSP') if row[0]==family),None)
            if candidate is None:raise ValueError('No DSP month-end ZIP candidate discovered')
            _,url,title=candidate
            providers.can_crawl(url)
            body,h,_=providers.fetch(url,max_bytes=80*1024*1024)
            print(f'DSP_V87_SOURCE {url} :: {title}',flush=True)
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                for entry in z.infolist():
                    suffix=PurePosixPath(entry.filename).suffix.lower()
                    if suffix not in ('.xls','.xlsx'):continue
                    raw=z.read(entry)
                    if suffix=='.xlsx':
                        book=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
                        sheets=[]
                        for sh in book.worksheets:
                            cells=list(sh.iter_rows())
                            sheets.append((sh.title,[[x.value for x in row] for row in cells],
                                           [[x.number_format or '' for x in row] for row in cells]))
                        book.close()
                    else:
                        book=xlrd.open_workbook(file_contents=raw,formatting_info=True)
                        sheets=[(sh.name,[sh.row_values(i) for i in range(sh.nrows)],
                                 [[book.format_map[book.xf_list[sh.cell_xf_index(i,j)].format_key].format_str
                                   for j in range(sh.ncols)] for i in range(sh.nrows)])
                                for sh in book.sheets()]
                    for sheet,rows0,formats0 in sheets:
                        prefix=' '.join(str(v) for row in rows0[:25] for v in row if v is not None)
                        if not re.search(r'DSP\s+Small\s+Cap\s+Fund',sheet+' '+prefix,re.I):continue
                        parsed=parse_sheet(rows0,formats0,family)
                        summary=None if parsed is None else {
                            'day':parsed['day'],'aum':parsed['aum'],'complete':parsed['complete'],
                            'positions':len(parsed['positions']),'unknown_rows':parsed.get('unknown_rows',[])[:40],
                            'weight_sum':round(sum(x['weight'] for x in parsed['positions']),6),
                        }
                        print('DSP_V87_SHEET '+json.dumps({'member':entry.filename,'sheet':sheet,'parsed':summary},ensure_ascii=False),flush=True)
        except Exception as exc:
            print(f"::warning::DSP v87 diagnostic: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v89':
        family='Edelweiss Small Cap Fund'
        url='https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf'
        try:
            providers.can_crawl(url)
            body,h,mime=providers.fetch(url,max_bytes=50*1024*1024)
            print(f'EDELWEISS_V89_FETCH bytes={len(body)} mime={mime} sig={body[:16].hex()}',flush=True)
            did=providers.save_document(family,'Edelweiss Factsheet September 2026',url,'factsheet','Fund',origin='AMC')
            providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'EDELWEISS_V89_PARSED count={count}',flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v89 current factsheet: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']>=20)
        if snap:print(f'EDELWEISS_V89_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v90':
        family='Edelweiss Small Cap Fund'
        url='https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf'
        try:
            import io
            from pypdf import PdfReader
            providers.can_crawl(url)
            body,h,mime=providers.fetch(url,max_bytes=50*1024*1024)
            reader=PdfReader(io.BytesIO(body))
            print(f'EDELWEISS_V90_PAGES {len(reader.pages)}',flush=True)
            for i,page in enumerate(reader.pages):
                txt=page.extract_text() or ''
                if re.search(r'Edelweiss\s+Small\s+Cap\s+Fund|Top\s*30\s+Holdings|Small\s+Cap\s+Fund',txt,re.I):
                    clean=re.sub(r'[ \t]+',' ',txt)
                    print(f'EDELWEISS_V90_PAGE_BEGIN {i+1}',flush=True)
                    print(clean[:26000],flush=True)
                    print(f'EDELWEISS_V90_PAGE_END {i+1}',flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v90 diagnostic: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v97':
        page='https://www.edelweissmf.com/statutory/portfolio-of-schemes'
        try:
            from bs4 import BeautifulSoup
            providers.can_crawl(page)
            raw,_,_=providers.fetch(page,max_bytes=10*1024*1024)
            soup=BeautifulSoup(raw,'html.parser')
            main_url=None
            for tag in soup.find_all('script'):
                src=tag.get('src')
                if not src:continue
                u=urljoin(page,src)
                if urlparse(u).netloc.endswith('edelweissmf.com') and re.search(r'/main\.[A-Za-z0-9]+\.js(?:[?#]|$)',u,re.I):
                    main_url=u;break
            if not main_url:raise ValueError('Edelweiss main bundle URL not found')
            providers.can_crawl(main_url)
            body,_,_=providers.fetch(main_url,max_bytes=10*1024*1024)
            js=body.decode('utf-8','ignore')
            print('EDELWEISS_V97_SCRIPT '+main_url,flush=True)
            for term in ('financials-portfolios','portfolio-of-schemes'):
                matches=list(re.finditer(re.escape(term),js,re.I))
                print(f'EDELWEISS_V97_TERM {term} count={len(matches)}',flush=True)
                for idx,m in enumerate(matches[:12]):
                    ctx=js[max(0,m.start()-1800):m.end()+2600]
                    ctx=re.sub(r'\s+',' ',ctx).strip()
                    print(f'EDELWEISS_V97_CONTEXT term={term} idx={idx} '+ctx[:4400],flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v97 diagnostic: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v98':
        page='https://www.edelweissmf.com/statutory/portfolio-of-schemes'
        try:
            from bs4 import BeautifulSoup
            providers.can_crawl(page)
            raw,_,_=providers.fetch(page,max_bytes=10*1024*1024)
            soup=BeautifulSoup(raw,'html.parser')
            main_url=None
            for tag in soup.find_all('script'):
                src=tag.get('src')
                if not src:continue
                u=urljoin(page,src)
                if urlparse(u).netloc.endswith('edelweissmf.com') and re.search(r'/main\.[A-Za-z0-9]+\.js(?:[?#]|$)',u,re.I):
                    main_url=u;break
            if not main_url:raise ValueError('Edelweiss main bundle URL not found')
            providers.can_crawl(main_url)
            body,_,_=providers.fetch(main_url,max_bytes=12*1024*1024)
            js=body.decode('utf-8','ignore')
            print('EDELWEISS_V98_SCRIPT '+main_url,flush=True)
            terms=(
                'Portfolio of scheme(s)','Portfolio of schemes','Portfolio Of Schemes',
                'innerDownloadTabs','otherDiscloserTab','downloadsSection',
                'portfolio-of-schemes','financials-portfolios'
            )
            for term in terms:
                matches=list(re.finditer(re.escape(term),js,re.I))
                print(f'EDELWEISS_V98_TERM {term} count={len(matches)}',flush=True)
                for idx,m in enumerate(matches[:6]):
                    ctx=js[max(0,m.start()-5000):m.end()+7000]
                    ctx=re.sub(r'\s+',' ',ctx).strip()
                    print(f'EDELWEISS_V98_CONTEXT term={term} idx={idx} '+ctx[:12000],flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v98 diagnostic: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(False)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v99':
        family='Edelweiss Small Cap Fund'
        url='https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf'
        try:
            providers.can_crawl(url)
            body,h,mime=providers.fetch(url,max_bytes=50*1024*1024)
            did=providers.save_document(family,'Edelweiss Factsheet September 2026',url,'factsheet','Fund',origin='AMC')
            providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'EDELWEISS_V99_PARSED count={count} mime={mime}',flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v99 factsheet: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']==10 and not snap['complete'])
        if snap:print(f'EDELWEISS_V99_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v102':
        family='Edelweiss Small Cap Fund'
        url='https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf'
        try:
            providers.can_crawl(url)
            body,h,mime=providers.fetch(url,max_bytes=50*1024*1024)
            did=providers.save_document(family,'Edelweiss Factsheet September 2026',url,'factsheet','Fund',origin='AMC')
            providers.doc_version(did,h)
            count=amc_reports.extract(body,family,url,h)
            print(f'EDELWEISS_V102_PARSED count={count} mime={mime}',flush=True)
        except Exception as exc:
            print(f"::warning::Edelweiss v102 factsheet: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']==10 and not snap['complete'])
        if snap:print(f'EDELWEISS_V102_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v105':
        # Temporary Mirae source diagnostic. The public portfolio page is
        # client-rendered; inspect only first-party HTML/script configuration.
        try:
            from bs4 import BeautifulSoup
            page='https://www.miraeassetmf.co.in/downloads/portfolio'
            providers.can_crawl(page)
            raw,_,_=providers.fetch(page,max_bytes=10*1024*1024)
            soup=BeautifulSoup(raw,'html.parser');txt=raw.decode('utf-8','ignore')
            print(f'MIRAE_V105_PAGE bytes={len(raw)}',flush=True)
            for tag in soup.find_all(['div','section','input','select','button','a']):
                vals=[]
                for k,v in tag.attrs.items():
                    value=' '.join(v) if isinstance(v,list) else str(v)
                    if re.search(r'portfolio|download|api|ajax|month|year',value,re.I):
                        vals.append(f'{k}={value}')
                if vals:
                    print('MIRAE_V105_ATTR '+tag.name+' '+' '.join(vals)[:1000],flush=True)
            scripts=[]
            for tag in soup.find_all('script'):
                src=tag.get('src')
                if src:
                    u=urljoin(page,src)
                    if (urlparse(u).hostname or '').endswith('miraeassetmf.co.in'):scripts.append(u)
                else:
                    body=tag.string or tag.get_text(' ',strip=True)
                    if re.search(r'portfolio|download|ajax|api',body,re.I):
                        print('MIRAE_V105_INLINE '+re.sub(r'\s+',' ',body)[:3500],flush=True)
            for u in list(dict.fromkeys(scripts)):
                try:
                    providers.can_crawl(u);body,_,_=providers.fetch(u,max_bytes=5*1024*1024)
                    st=body.decode('utf-8','ignore')
                except Exception as exc:
                    print(f'MIRAE_V105_SCRIPT_ERR {u} :: {(str(exc) or type(exc).__name__)[:180]}',flush=True);continue
                hits=[]
                for m in re.finditer(r'.{0,220}(?:portfolio|download|ajax|api|xlsx?|\.xls).{0,500}',st,re.I|re.S):
                    snippet=re.sub(r'\s+',' ',m.group(0)).strip()
                    if snippet not in hits:hits.append(snippet)
                    if len(hits)>=10:break
                if hits:
                    print('MIRAE_V105_SCRIPT '+u,flush=True)
                    for hit in hits:print('MIRAE_V105_HIT '+hit[:1400],flush=True)
        except Exception as exc:
            print(f"::warning::Mirae v105 source audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v106','amc-reports-2026-09-v107','amc-reports-2026-09-v108'):
        # Trace Mirae's ASP.NET AJAX proxy used by DownloadPortfolio.js.
        try:
            from bs4 import BeautifulSoup
            page='https://www.miraeassetmf.co.in/downloads/portfolio'
            providers.can_crawl(page)
            raw,_,_=providers.fetch(page,max_bytes=10*1024*1024)
            soup=BeautifulSoup(raw,'html.parser')
            scripts=[]
            for tag in soup.find_all('script'):
                src=tag.get('src')
                if not src:continue
                u=urljoin(page,src)
                if (urlparse(u).hostname or '').endswith('miraeassetmf.co.in'):
                    scripts.append(u)
                    if re.search(r'ajax|service|portfolio|download',u,re.I):
                        print('MIRAE_V106_SCRIPT_URL '+u,flush=True)
            for u in list(dict.fromkeys(scripts)):
                try:
                    providers.can_crawl(u);body,_,_=providers.fetch(u,max_bytes=6*1024*1024)
                    js=body.decode('utf-8','ignore')
                except Exception as exc:
                    continue
                if not re.search(r'GetDownloadsDataAsync|AjaxService|WebServiceProxy\.invoke',js,re.I):continue
                print('MIRAE_V106_SERVICE_SCRIPT '+u,flush=True)
                for m in list(re.finditer(r'.{0,500}(?:GetDownloadsDataAsync|AjaxService|WebServiceProxy\.invoke).{0,1200}',js,re.I|re.S))[:20]:
                    print('MIRAE_V106_SERVICE_HIT '+re.sub(r'\s+',' ',m.group(0)).strip()[:2200],flush=True)
            html=raw.decode('utf-8','ignore')
            for m in list(re.finditer(r'.{0,500}(?:GetDownloadsDataAsync|AjaxService|DownloadPortfolio\.js).{0,1200}',html,re.I|re.S))[:12]:
                print('MIRAE_V106_HTML_HIT '+re.sub(r'\s+',' ',m.group(0)).strip()[:2200],flush=True)
        except Exception as exc:
            print(f"::warning::Mirae v106 proxy trace: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v109':
        # Query the exact first-party endpoint used by DownloadPortfolio.js.
        try:
            endpoint='https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData'
            request={'request':{'modulename':'portfolio_tab1','pgno':1,'pgsize':50}}
            providers.can_crawl(endpoint)
            raw,_,mime=providers.fetch(endpoint,body=request,max_bytes=8*1024*1024)
            data=json.loads(raw)
            print(f'MIRAE_V109_ENDPOINT mime={mime} return={data.get("ReturnCode")} rows={len(data.get("Data") or [])} count={data.get("DataCount")}',flush=True)
            for row in (data.get('Data') or [])[:50]:
                print('MIRAE_V109_ROW '+json.dumps({
                    'Title':row.get('Title'),
                    'URL':row.get('URL'),
                    'PublishDate':row.get('PublishDate'),
                },ensure_ascii=False)[:1800],flush=True)
        except Exception as exc:
            print(f"::warning::Mirae v109 endpoint audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v110':
        from tracker import amc_discovery
        family='Mirae Asset Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('Mirae'):
                if discovered_family!=family:continue
                attempted+=1
                print(f'MIRAE_V110_CANDIDATE {attempted} {url} :: {title}',flush=True)
                try:
                    count=amc_discovery.store_report('Mirae',family,url,title)
                    print(f'MIRAE_V110_PARSED {attempted} count={count}',flush=True)
                except Exception as exc:
                    print(f"::warning::Mirae v110 candidate {attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap:print(f'MIRAE_V110_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
                if snap and snap['as_of']>='2026-08-31':break
        except Exception as exc:
            print(f"::warning::Mirae v110 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31')
        if current:print(f'Mirae current portfolio verified at {snap["as_of"]}: {snap["positions"]} positions, complete={snap["complete"]}',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Mirae current portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v111':
        from tracker import amc_discovery
        family='Quant Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('quant Mutual'):
                if discovered_family!=family:continue
                attempted+=1
                print(f'QUANT_V111_CANDIDATE {attempted} {url} :: {title}',flush=True)
                try:
                    count=amc_discovery.store_report('quant Mutual',family,url,title)
                    print(f'QUANT_V111_PARSED {attempted} count={count}',flush=True)
                except Exception as exc:
                    print(f"::warning::Quant v111 candidate {attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap:print(f'QUANT_V111_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
                if snap and snap['as_of']>='2026-08-31':break
                if attempted>=4:break
        except Exception as exc:
            print(f"::warning::Quant v111 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31')
        if current:print(f'Quant current portfolio verified at {snap["as_of"]}: {snap["positions"]} positions, complete={snap["complete"]}',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Quant current portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v112':
        from bs4 import BeautifulSoup
        pages=(
            'https://quantmutual.com/statutory-disclosures',
            'https://www.quantmutual.com/downloads/Notice-of-Monthly-Fortnightly-Portfolio',
        )
        try:
            for page in pages:
                providers.can_crawl(page)
                raw,_,_=providers.fetch(page,max_bytes=10*1024*1024)
                html=raw.decode('utf-8','ignore');soup=BeautifulSoup(raw,'html.parser')
                print(f'QUANT_V112_PAGE {page} bytes={len(raw)}',flush=True)
                for m in list(re.finditer(r'.{0,1800}(?:August\s+31,?\s+2026|31[./-]08[./-]2026|Monthly\s+Portfolio).{0,3500}',html,re.I|re.S))[:16]:
                    print('QUANT_V112_HTML '+re.sub(r'\s+',' ',m.group(0)).strip()[:5200],flush=True)
                scripts=[]
                for tag in soup.find_all('script'):
                    src=tag.get('src')
                    if src:
                        u=urljoin(page,src)
                        if (urlparse(u).hostname or '').endswith('quantmutual.com'):scripts.append(u)
                    else:
                        body=tag.string or tag.get_text(' ',strip=True)
                        if re.search(r'portfolio|download|archive|ajax|August',body,re.I):
                            print('QUANT_V112_INLINE '+re.sub(r'\s+',' ',body)[:4500],flush=True)
                for u in list(dict.fromkeys(scripts)):
                    try:
                        providers.can_crawl(u);body,_,_=providers.fetch(u,max_bytes=5*1024*1024)
                        js=body.decode('utf-8','ignore')
                    except Exception:continue
                    hits=[]
                    for m in re.finditer(r'.{0,300}(?:portfolio|download|archive|ajax|\.xlsx?|\.xls).{0,900}',js,re.I|re.S):
                        hit=re.sub(r'\s+',' ',m.group(0)).strip()
                        if hit not in hits:hits.append(hit)
                        if len(hits)>=10:break
                    if hits:
                        print('QUANT_V112_SCRIPT '+u,flush=True)
                        for hit in hits:print('QUANT_V112_HIT '+hit[:1600],flush=True)
        except Exception as exc:
            print(f"::warning::Quant v112 markup audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v113','amc-reports-2026-09-v114','amc-reports-2026-09-v115'):
        endpoint='https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser1'
        try:
            providers.can_crawl(endpoint)
            raw,_,mime=providers.fetch(endpoint,body={'id':'2026','cat':'MONTHLY PORTFOLIO - FUND - WISE'},max_bytes=5*1024*1024)
            data=json.loads(raw)
            html=str(data.get('d') or '')
            print(f'QUANT_V113_LEVEL1 mime={mime} bytes={len(raw)} html={len(html)}',flush=True)
            print('QUANT_V113_LEVEL1_HTML '+re.sub(r'\s+',' ',html)[:12000],flush=True)
            # Trace any follow-up IDs/tabs emitted by the first endpoint.
            pairs=[]
            for m in re.finditer(r'submit_event2\(\s*["\']?([^,"\')]+)["\']?\s*,\s*["\']MONTHLY PORTFOLIO - FUND - WISE["\']\s*,\s*["\']([^"\']+)',html,re.I):
                pair=(m.group(1).strip(),m.group(2).strip())
                if pair not in pairs:pairs.append(pair)
            print('QUANT_V113_LEVEL1_PAIRS '+json.dumps(pairs[:20]),flush=True)
            endpoint2='https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser2'
            for idx,(ident,tab) in enumerate(pairs[:8],1):
                try:
                    providers.can_crawl(endpoint2)
                    raw2,_,mime2=providers.fetch(endpoint2,body={'id':ident,'cat':'MONTHLY PORTFOLIO - FUND - WISE','tab':tab},max_bytes=5*1024*1024)
                    data2=json.loads(raw2);html2=str(data2.get('d') or '')
                    print(f'QUANT_V113_LEVEL2 {idx} id={ident} tab={tab} mime={mime2} html={len(html2)}',flush=True)
                    print('QUANT_V113_LEVEL2_HTML '+re.sub(r'\s+',' ',html2)[:16000],flush=True)
                except Exception as exc:
                    print(f"::warning::Quant v113 level2 {idx}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        except Exception as exc:
            print(f"::warning::Quant v113 endpoint audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v116':
        endpoint='https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser2'
        try:
            providers.can_crawl(endpoint)
            raw,_,mime=providers.fetch(endpoint,body={'id':'8','cat':'MONTHLY PORTFOLIO - FUND - WISE','tab':'2026'},max_bytes=5*1024*1024)
            data=json.loads(raw);html=str(data.get('d') or '')
            print(f'QUANT_V116_LEVEL2 mime={mime} bytes={len(raw)} html={len(html)}',flush=True)
            print('QUANT_V116_LEVEL2_HTML '+re.sub(r'\s+',' ',html)[:24000],flush=True)
        except Exception as exc:
            print(f"::warning::Quant v116 level2 audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v117','amc-reports-2026-09-v118','amc-reports-2026-09-v121','amc-reports-2026-09-v123'):
        from tracker import amc_discovery
        family='Quant Small Cap Fund';attempted=0
        try:
            for discovered_family,url,title in amc_discovery.discover('quant Mutual'):
                if discovered_family!=family:continue
                attempted+=1
                print(f'QUANT_V117_CANDIDATE {attempted} {url} :: {title}',flush=True)
                try:
                    count=amc_discovery.store_report('quant Mutual',family,url,title)
                    print(f'QUANT_V117_PARSED {attempted} count={count}',flush=True)
                except Exception as exc:
                    print(f"::warning::Quant v117 candidate {attempted}: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap:
                    print(f'QUANT_V117_SNAPSHOT {snap["as_of"]} complete={snap["complete"]} positions={snap["positions"]}',flush=True)
                if snap and snap['as_of']>='2026-08-31':
                    if not snap['complete'] and url.lower().endswith(('.xlsx','.xls')):
                        try:
                            import io,openpyxl,xlrd
                            from tracker.portfolio_parser import parse_sheet
                            saved=db.one("""SELECT a.path FROM fetches f JOIN archives a ON a.hash=f.hash
                              WHERE f.url=? AND f.status='ok' ORDER BY f.id DESC LIMIT 1""",(url,))
                            if saved:
                                body=(db.DATA/saved['path']).read_bytes()
                                if body.startswith(b'PK'):
                                    book=openpyxl.load_workbook(io.BytesIO(body),read_only=True,data_only=True)
                                    sheets=[(sh.title,[[x.value for x in row] for row in sh.iter_rows()],
                                             [[x.number_format or '' for x in row] for row in sh.iter_rows()])
                                            for sh in book.worksheets]
                                    book.close()
                                elif body.startswith(b'\xd0\xcf'):
                                    book=xlrd.open_workbook(file_contents=body,formatting_info=True)
                                    sheets=[(sh.name,[sh.row_values(i) for i in range(sh.nrows)],
                                             [[book.format_map[book.xf_list[sh.cell_xf_index(i,j)].format_key].format_str
                                               for j in range(sh.ncols)] for i in range(sh.nrows)])
                                            for sh in book.sheets()]
                                else:sheets=[]
                                for sheet,rows0,formats0 in sheets:
                                    parsed=parse_sheet(rows0,formats0,family)
                                    if parsed:
                                        print('QUANT_V117_SHEET '+json.dumps({
                                            'sheet':sheet,'day':parsed['day'],'complete':parsed['complete'],
                                            'positions':len(parsed['positions']),
                                            'unknown_rows':parsed.get('unknown_rows',[])[:40],
                                            'weight_sum':round(sum(x['weight'] for x in parsed['positions']),6),
                                        },ensure_ascii=False),flush=True)
                        except Exception as diag_exc:
                            print(f"::warning::Quant v117 workbook diagnostic: {(str(diag_exc) or type(diag_exc).__name__).splitlines()[0][:300]}",flush=True)
                    break
                if attempted>=3:break
        except Exception as exc:
            print(f"::warning::Quant v117 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31')
        if current:print(f'Quant current portfolio verified at {snap["as_of"]}: {snap["positions"]} positions, complete={snap["complete"]}',flush=True)
        else:
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            print(f'::warning::Quant current portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        ok.append(current)
    if amc_reports.PARSER_VERSION in ('amc-reports-2026-09-v119','amc-reports-2026-09-v120','amc-reports-2026-09-v122'):
        family='Quant Small Cap Fund'
        url='https://quantmutual.com/Admin/disclouser/quant_Small_Cap_Fund_31_Aug_2026.xlsx'
        try:
            providers.can_crawl(url)
            body,h,_=providers.fetch(url,max_bytes=40*1024*1024)
            import io,openpyxl,xlrd
            if body.startswith(b'PK'):
                book=openpyxl.load_workbook(io.BytesIO(body),read_only=True,data_only=True)
                sheets=[(sh.title,[[x.value for x in row] for row in sh.iter_rows()]) for sh in book.worksheets]
                book.close()
            elif body.startswith(b'\xd0\xcf'):
                book=xlrd.open_workbook(file_contents=body,formatting_info=True)
                sheets=[(sh.name,[sh.row_values(i) for i in range(sh.nrows)]) for sh in book.sheets()]
            else:
                raise ValueError('Quant August workbook returned unsupported content')
            for sheet,rows0 in sheets:
                prefix=' '.join(str(v) for row in rows0[:25] for v in row if v not in (None,''))
                if not re.search(r'quant\s+Small\s+Cap\s+Fund',sheet+' '+prefix,re.I):continue
                print(f'QUANT_V119_SHEET {sheet} rows={len(rows0)}',flush=True)
                if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v122':
                    for j,row in enumerate(rows0[:18]):
                        print('QUANT_V122_HEAD '+json.dumps({'index':j,'row':row},default=str,ensure_ascii=False)[:5000],flush=True)
                    header_i=None
                    for j,row in enumerate(rows0[:35]):
                        cells=[str(v or '').lower() for v in row]
                        if any('isin' in v for v in cells) and any('%' in v and (re.search(r'nav|aum',v) or ('net' in v and 'asset' in v)) for v in cells):
                            header_i=j;break
                    if header_i is not None:
                        header=[str(v or '').lower() for v in rows0[header_i]]
                        def _col(pred):return next((k for k,v in enumerate(header) if pred(v)),None)
                        mapping={
                            'header_index':header_i,
                            'ic':_col(lambda v:'isin' in v),
                            'nc':_col(lambda v:'name' in v or 'instrument' in v or 'issuer' in v),
                            'wc':_col(lambda v:'%' in v and (re.search(r'nav|aum',v) or ('net' in v and 'asset' in v))),
                            'vc':_col(lambda v:re.search(r'market|mkt|fair',v) and re.search(r'value',v)),
                            'sc':_col(lambda v:'industry' in v or 'rating' in v or 'sector' in v),
                            'qc':_col(lambda v:'quantity' in v or bool(re.search(r'\\bqty\\b|no\\.?\\s*of\\s*(?:shares|units)',v,re.I))),
                            'header':header,
                        }
                        print('QUANT_V122_COLUMNS '+json.dumps(mapping,ensure_ascii=False)[:7000],flush=True)
                for i,row in enumerate(rows0):
                    flat=' | '.join(str(v) for v in row if v not in (None,''))
                    if re.search(r'Derivative|29/09/2026|NCA-NET CURRENT ASSETS',flat,re.I):
                        lo=max(0,i-3);hi=min(len(rows0),i+4)
                        for j in range(lo,hi):
                            print('QUANT_V119_ROW '+json.dumps({'index':j,'row':rows0[j]},default=str,ensure_ascii=False)[:5000],flush=True)
        except Exception as exc:
            print(f"::warning::Quant v119 derivative audit: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(True)
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v124':
        family='Tata Small Cap Fund';attempted=0;current=False;snap=None
        try:
            from tracker import amc_discovery
            for found_family,url,title in amc_discovery.discover('Tata'):
                attempted+=1
                try:
                    amc_discovery.store_report('Tata',found_family,url,title)
                except Exception as exc:
                    print(f"::warning::Tata current portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:
                    current=True;break
            if not current:
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, complete={snap["complete"]}'
            if current:print(f'Tata current complete portfolio verified: {detail}',flush=True)
            else:print(f'::warning::Tata current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        except Exception as exc:
            print(f"::warning::Tata v124 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(current)

    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v125':
        family='Trustmf Small Cap Fund';attempted=0;current=False;snap=None
        try:
            from tracker import amc_discovery
            for found_family,url,title in amc_discovery.discover('TRUST'):
                if not urlparse(url).path.lower().endswith(('.xls','.xlsx')):continue
                attempted+=1
                try:
                    amc_discovery.store_report('TRUST',found_family,url,title)
                except Exception as exc:
                    print(f"::warning::TRUSTMF current portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions,SUM(h.weight) weight
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                if snap and snap['as_of']>='2026-08-31' and snap['complete']:
                    current=True;break
            if not current:
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions,SUM(h.weight) weight
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                current=bool(snap and snap['as_of']>='2026-08-31' and snap['complete'])
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, {float(snap["weight"] or 0):.2f}% weight, complete={snap["complete"]}'
            if current:print(f'TRUSTMF current complete portfolio verified: {detail}',flush=True)
            else:print(f'::warning::TRUSTMF current complete portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        except Exception as exc:
            print(f"::warning::TRUSTMF v125 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(current)

    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v126':
        family='Sundaram Small Cap Fund';attempted=0;verified=False;snap=None
        try:
            from tracker import amc_discovery
            for found_family,url,title in amc_discovery.discover('Sundaram'):
                attempted+=1
                try:
                    amc_discovery.store_report('Sundaram',found_family,url,title)
                except Exception as exc:
                    print(f"::warning::Sundaram current portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
                snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions,SUM(h.weight) weight
                  FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
                  WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
                verified=bool(snap and snap['as_of']>='2026-08-31' and not snap['complete']
                              and snap['positions']>=77 and abs(float(snap['weight'] or 0)-100)<.02)
                if verified:break
            detail='none' if not snap else f'{snap["as_of"]}, {snap["positions"]} positions, {float(snap["weight"] or 0):.6f}% known weight, complete={snap["complete"]}'
            if verified:print(f'Sundaram richer partial portfolio verified: {detail}',flush=True)
            else:print(f'::warning::Sundaram richer partial portfolio not recovered; latest is {detail}; attempted={attempted}',flush=True)
        except Exception as exc:
            print(f"::warning::Sundaram v126 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(verified)

    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v127':
        family='Invesco India Small Cap Fund';attempted=0;verified=False;snaps=[]
        try:
            from tracker import amc_discovery
            for found_family,url,title in amc_discovery.discover('Invesco'):
                attempted+=1
                try:
                    amc_discovery.store_report('Invesco',found_family,url,title)
                except Exception as exc:
                    print(f"::warning::Invesco current portfolio candidate: {(str(exc) or type(exc).__name__).splitlines()[0][:250]}",flush=True)
            snaps=db.rows("""SELECT p.as_of,p.complete,COUNT(h.id) positions,SUM(h.weight) weight
              FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
              WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 2""",(family,))
            verified=bool(len(snaps)>=2
                          and snaps[0]['as_of']>='2026-08-31' and snaps[0]['complete']
                          and snaps[1]['as_of']>='2026-07-31' and snaps[1]['complete'])
            detail='; '.join(f'{x["as_of"]}, {x["positions"]} positions, {float(x["weight"] or 0):.2f}% weight, complete={x["complete"]}' for x in snaps) or 'none'
            if verified:print(f'Invesco current and prior complete portfolios verified: {detail}',flush=True)
            else:print(f'::warning::Invesco complete portfolio pair not recovered; latest snapshots: {detail}; attempted={attempted}',flush=True)
        except Exception as exc:
            print(f"::warning::Invesco v127 discovery: {(str(exc) or type(exc).__name__).splitlines()[0][:300]}",flush=True)
        ok.append(verified)

    # Dynamic AMC discovery is part of the immediately following daily
    # metrics collection. Parser upgrades only need to re-extract affected
    # archived/cataloged originals; do not crawl every AMC twice per push.
    checked,gaps=amc_reports.reprocess_archived()
    if amc_reports.PARSER_VERSION=='amc-reports-2026-09-v103':
        family='Edelweiss Small Cap Fund'
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1""",(family,))
        current=bool(snap and snap['as_of']>='2026-08-31' and snap['positions']==10 and not snap['complete'])
        detail='none' if not snap else f'{snap["as_of"]}, complete={snap["complete"]}, positions={snap["positions"]}'
        print(f'EDELWEISS_V103_ARCHIVE checked={checked} latest={detail}',flush=True)
        ok.append(current)
    print(f'{sum(ok)}/{len(rows)} official report sources processed; {checked} existing documents rechecked; {len(gaps)} extraction errors')
    # Most parser upgrades retry failed transfers on the next push. Union v45
    # is a completed transport audit: all reviewed official routes were tried,
    # while the normal nightly discovery path continues retrying the live source.
    transport_audit_complete=(amc_reports.PARSER_VERSION=='amc-reports-2026-09-v45' and not gaps)
    if (all(ok) or transport_audit_complete) and not gaps:
        with db.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,'true'))


if __name__=='__main__':run()
