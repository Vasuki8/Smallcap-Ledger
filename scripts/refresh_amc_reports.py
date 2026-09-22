"""Apply an AMC parser upgrade to the restored archive without replacing history.

Known official report URLs provide reproducible starting coverage. The daily
document collector discovers subsequent reports from their registered AMC pages.
"""
from pathlib import Path
import json
import sys
import httpx
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db,providers,disclosures,amc_reports


def probe_bandhan_amfi():
    base='https://www.amfiindia.com/gateway/pollingsebi'
    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Accept':'application/json, text/plain, */*',
        'Referer':'https://www.amfiindia.com/otherdata/fund-performance',
    }
    try:
        with httpx.Client(base_url=base,headers=headers,timeout=60,follow_redirects=True) as c:
            f=c.post('/api/amfi/fundperformancefilters',json={});f.raise_for_status();filters=f.json().get('data',f.json())
            funds=filters.get('mutualFundList',[]) if isinstance(filters,dict) else []
            bandhan=next((x for x in funds if 'bandhan' in str(x.get('name','')).lower()),None)
            sc=c.post('/api/amfi/getsubcategory',json={'category':1});sc.raise_for_status();subs=sc.json().get('data',sc.json())
            small=next((x for x in subs if 'small' in str(x.get('name','')).lower() and 'cap' in str(x.get('name','')).lower()),None)
            print('AMFI Bandhan probe IDs: '+json.dumps({'bandhan':bandhan,'small_cap':small},ensure_ascii=False),flush=True)
            if not bandhan or not small:return
            for day in ('21-Sep-2026','18-Sep-2026','31-Aug-2026'):
                body={'maturityType':1,'category':1,'subCategory':small.get('id'),'mfid':bandhan.get('id'),'reportDate':day}
                p=c.post('/api/amfi/fundperformance',json=body);p.raise_for_status();payload=p.json();rows=payload.get('data',payload)
                if not isinstance(rows,list):rows=[rows]
                matches=[x for x in rows if isinstance(x,dict) and 'bandhan small cap fund' in str(x.get('schemeName','')).lower()]
                print('AMFI Bandhan probe '+day+': '+json.dumps(matches[:2],ensure_ascii=False)[:8000],flush=True)
                if matches:break
    except Exception as e:
        print('::warning::AMFI Bandhan performance probe: '+(str(e) or type(e).__name__).splitlines()[0][:350],flush=True)


def run():
    db.init();disclosures.seed_sources();probe_bandhan_amfi()
    from tracker import reviewed_reports
    print(f'{reviewed_reports.apply()} reviewed official figures retained with source notes',flush=True)
    key='amc_upgrade_'+amc_reports.PARSER_VERSION
    if db.setting(key,False):
        print('This AMC parser upgrade has already been applied; nightly discovery remains active.');return
    rows=json.loads((ROOT/'tracker/report_catalog.json').read_text())
    def collect(row):
        try:
            url=row['url'];family=row['family']
            # Catalog is committed, reviewed configuration; it must still belong
            # to a registered AMC domain before any public request is made.
            amc=next((a for a,u,_ in json.loads((ROOT/'tracker/sources.json').read_text()) if a.lower()==row['amc'].lower()),None)
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
    from tracker import amc_discovery
    print(amc_discovery.update(lambda msg:print(msg,flush=True)),flush=True)
    checked,gaps=amc_reports.reprocess_archived()
    print(f'{sum(ok)}/{len(rows)} official report sources processed; {checked} existing documents rechecked; {len(gaps)} extraction errors')
    # A failed transfer/extraction is retried on the next build. Old facts remain.
    if all(ok) and not gaps:
        with db.connect() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,'true'))


if __name__=='__main__':run()
