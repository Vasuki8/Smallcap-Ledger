from __future__ import annotations
import csv
import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from contextlib import asynccontextmanager
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI,HTTPException,Request,UploadFile,File,Form
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from . import db,analytics,providers,disclosures
from .sync import updater


@asynccontextmanager
async def lifespan(app):
    db.init(recover=True);disclosures.seed_sources()
    if os.environ.get("SMALLCAP_NO_SCHEDULER")!="1": updater.start()
    yield
    updater.stop.set()

app=FastAPI(title="Smallcap Ledger",lifespan=lifespan,docs_url=None,redoc_url=None)


@app.get('/api/health')
def health():
    return {'app':'smallcap-ledger','version':'1.0.0'}


@app.middleware("http")
async def local_only(request,call_next):
    host=request.headers.get("host","").split(":")[0]
    if host not in ("127.0.0.1","localhost","testserver"):
        return Response("This tracker only accepts local requests",status_code=403)
    if request.method not in ("GET","HEAD","OPTIONS"):
        origin=request.headers.get("origin")
        if request.headers.get("x-smallcap-client")!="local" or (origin and urlparse(origin).netloc!=request.headers.get("host")):
            return Response("Open the tracker locally to make this change",status_code=403)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="no-referrer"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    return response


def scheme(code):
    s=db.one("SELECT * FROM schemes WHERE code=?",(code,))
    if not s:raise HTTPException(404,"Scheme not found")
    return s


def option_label(s):
    if s['option']!='IDCW':return s['option']
    meta=json.loads(s.get('metadata_json') or '{}')
    text=(meta.get('amfi_option') or meta.get('scheme_name') or s.get('name') or '').lower()
    reinvest='reinvest' in text;payout='payout' in text
    if s.get('reinvestment_isin'):return 'IDCW · payout / reinvestment'
    if reinvest and not payout:return 'IDCW · reinvestment'
    if payout and not reinvest:return 'IDCW · payout'
    return 'IDCW'


def metrics_for(s):
    records=db.rows("SELECT * FROM metrics WHERE family=? AND plan IN ('All',?) ORDER BY as_of DESC,id DESC",(s['family'],s['plan']))
    latest={}
    for x in records:
        if x['metric'] not in latest:latest[x['metric']]=x
    return latest


def dated_return(code,latest,years):
    d=analytics.shift_years(date.fromisoformat(latest['date']),years)
    p=db.one("SELECT date,value FROM nav WHERE code=? AND date<=? ORDER BY date DESC LIMIT 1",(code,d.isoformat()))
    if not p or (d-date.fromisoformat(p['date'])).days>7:return None
    days=(date.fromisoformat(latest['date'])-date.fromisoformat(p['date'])).days
    return ((latest['value']/p['value'])**(365.25/days)-1)*100 if days>0 else None


@app.get('/api/funds')
def funds():
    records=db.rows("SELECT * FROM schemes ORDER BY family,plan,option,code")
    for s in records:
        s['option_label']=option_label(s)
        latest=db.rows("SELECT date,value,source FROM nav WHERE code=? ORDER BY date DESC LIMIT 2",(s['code'],))
        coverage=db.one("SELECT MIN(date) first,MAX(date) last,COUNT(*) points FROM nav WHERE code=?",(s['code'],))
        s['nav']=latest[0] if latest else None
        s['nav_change']=((latest[0]['value']/latest[1]['value']-1)*100) if len(latest)>1 else None
        s['coverage']=coverage
        s['returns']={str(y):dated_return(s['code'],latest[0],y) if latest and s['option']=='Growth' else None for y in (1,3,5)}
        s['metrics']=metrics_for(s)
        s['documents']=db.one("SELECT COUNT(*) n FROM documents WHERE family=? AND kind!='source page'",(s['family'],))['n']
        s['portfolio']=db.one("SELECT id,as_of,complete FROM portfolios WHERE family=? ORDER BY as_of DESC,complete DESC,id DESC LIMIT 1",(s['family'],))
        s['stale_days']=(date.today()-date.fromisoformat(coverage['last'])).days if coverage['last'] else None
    return {"funds":records,"as_of":db.now()}


@app.get('/api/funds/{code}')
def fund(code:int):
    s=scheme(code);s['metrics']=metrics_for(s)
    s['option_label']=option_label(s)
    s['nav_coverage']=db.one("SELECT MIN(date) first,MAX(date) last,COUNT(*) points FROM nav WHERE code=?",(code,))
    s['plans']=db.rows("SELECT code,name,plan,option,isin,reinvestment_isin,metadata_json FROM schemes WHERE family=? ORDER BY plan,option",(s['family'],))
    for p in s['plans']:p['option_label']=option_label(p)
    s['metric_history']=db.rows("SELECT * FROM metrics WHERE family=? ORDER BY as_of DESC,id DESC",(s['family'],))
    s['portfolios']=db.rows("SELECT p.*,COUNT(h.id) holding_count,SUM(h.weight) disclosed_weight FROM portfolios p LEFT JOIN holdings h ON p.id=h.snapshot_id WHERE family=? GROUP BY p.id ORDER BY as_of DESC,complete DESC,p.id DESC",(s['family'],))
    s['sources']=db.rows("SELECT * FROM source_pages WHERE instr(lower(?),lower(amc_match))>0 ORDER BY id",(s['amc'],))
    s['distribution_coverage']=db.one("SELECT * FROM distribution_coverage WHERE code=?",(code,))
    return s


@app.get('/api/funds/{code}/performance')
def performance(code:int,start:str|None=None,end:str|None=None,benchmark:str=providers.BENCHMARK,monthly:float=10000):
    s=scheme(code)
    if not 100<=monthly<=100000000:raise HTTPException(400,"Monthly SIP must be between ₹100 and ₹10 crore")
    try:
        if start:date.fromisoformat(start)
        if end:date.fromisoformat(end)
        if start and end and start>end:raise ValueError()
    except ValueError:raise HTTPException(400,"Enter a valid date range")
    nav=[[x['date'],x['value']] for x in db.rows("SELECT date,value FROM nav WHERE code=? ORDER BY date",(code,))]
    coverage=db.one("SELECT * FROM distribution_coverage WHERE code=?",(code,))
    total_points=nav if s['option']=='Growth' else []
    method="Growth NAV; fund expenses already reflected. Tax and exit loads excluded."
    if s['option']=='IDCW':
        method="NAV-only view. IDCW cash distributions are not included; total-return comparisons and SIP results are unavailable without a complete distribution history."
        if coverage:
            events=db.rows("SELECT * FROM distributions WHERE code=? ORDER BY ex_date",(code,))
            total_points=analytics.reinvested(nav,events,coverage['start'],coverage['end'])
            method="Hypothetical reinvested IDCW total return, using user-confirmed complete distributions and reinvestment NAVs. Tax and exit loads excluded."
    elif s['option']!='Growth':
        method="NAV-only view. Bonus allotments or other unit adjustments are not yet mapped; adjusted total returns and SIP results are unavailable for this option."
    selected=[p for p in total_points if (not start or p[0]>=start) and (not end or p[0]<=end)]
    nav_selected=[p for p in nav if (not start or p[0]>=start) and (not end or p[0]<=end)]
    bp=[[x['date'],x['value']] for x in db.rows("SELECT date,value FROM benchmark WHERE name=? ORDER BY date",(benchmark,))]
    aligned=analytics.aligned(selected,bp)
    full=analytics.performance(total_points)
    selected_stats=analytics.performance(selected)
    full_aligned=analytics.aligned([p for p in total_points if not end or p[0]<=end],bp)
    aligned_f=[[p[0],p[1]] for p in full_aligned];aligned_b=[[p[0],p[2]] for p in full_aligned]
    return {"nav":nav_selected,"total_return_series":selected,"method":method,"can_total_return":bool(selected),
            "benchmark":benchmark,"comparison":aligned,"stats":full,"range_stats":selected_stats,
            "comparison_stats":{"fund":analytics.performance(aligned_f)['returns'],"benchmark":analytics.performance(aligned_b)['returns']},
            "sip":analytics.sip(selected,monthly) if selected else None,
            "latest_nav":nav[-1] if nav else None,
            "first_nav":nav[0][0] if nav else None,"last_nav":nav[-1][0] if nav else None,
            "benchmark_source":db.one("SELECT source,MAX(date) last,MIN(date) first,COUNT(*) points FROM benchmark WHERE name=?",(benchmark,)),
            "distribution_coverage":coverage}


@app.get('/api/portfolios/{snapshot_id}')
def holdings(snapshot_id:int):
    p=db.one("SELECT * FROM portfolios WHERE id=?",(snapshot_id,))
    if not p:raise HTTPException(404,"Snapshot not found")
    p['holdings']=db.rows("SELECT * FROM holdings WHERE snapshot_id=? ORDER BY weight DESC",(snapshot_id,))
    prior=db.one("SELECT * FROM portfolios WHERE family=? AND as_of<? AND complete=? ORDER BY as_of DESC,id DESC LIMIT 1",(p['family'],p['as_of'],p['complete']))
    p['previous']=prior;p['changes']=[]
    if prior:
        old=db.rows("SELECT * FROM holdings WHERE snapshot_id=?",(prior['id'],))
        key=lambda h:h['isin'] or h['name'].lower().strip()
        before={key(h):h for h in old};after={key(h):h for h in p['holdings']}
        for k in set(before)|set(after):
            a=before.get(k);b=after.get(k);change=(b['weight'] if b else 0)-(a['weight'] if a else 0)
            if abs(change)<0.005:continue
            label=('Added' if not a else 'Removed' if not b else 'Weight change') if p['complete'] and prior['complete'] else ('Entered disclosed list' if not a else 'Left disclosed list' if not b else 'Disclosed weight change')
            p['changes'].append({"name":(b or a)['name'],"before":a['weight'] if a else None,"after":b['weight'] if b else None,"change":change,"type":label})
        p['changes'].sort(key=lambda x:abs(x['change']),reverse=True)
    return p


@app.get('/api/funds/{code}/documents')
def documents(code:int):
    s=scheme(code)
    docs=db.rows("SELECT * FROM documents WHERE family=? AND kind!='news' AND (origin='AMC' OR origin LIKE 'User import%') ORDER BY COALESCE(published_at,first_seen) DESC,id DESC",(s['family'],))
    from .publications import exclusion_reason
    # Apply current ownership rules to previously archived associations as well.
    # No historical document, version, or source file is deleted.
    docs=[d for d in docs if not exclusion_reason(s['amc'],d['url'],d['title'])]
    for d in docs:
        d['title']=providers.document_title(d['title'],d['url'])
        d['versions']=db.rows("SELECT v.*,a.media_type,a.bytes FROM document_versions v JOIN archives a ON a.hash=v.hash WHERE document_id=? ORDER BY v.id DESC",(d['id'],))
    return docs


@app.get('/api/status')
def status():
    return {"running":updater.status(),"settings":{x['key']:json.loads(x['value']) for x in db.rows("SELECT * FROM settings WHERE key NOT LIKE 'nifty_year_%' AND key NOT LIKE 'amfi_fee_month_%'")},
            "counts":db.one("SELECT (SELECT COUNT(*) FROM schemes) plans,(SELECT COUNT(DISTINCT family) FROM schemes) funds,(SELECT COUNT(*) FROM nav) nav_points,(SELECT COUNT(*) FROM benchmark) benchmark_points,(SELECT COUNT(*) FROM portfolios) portfolios,(SELECT COUNT(*) FROM document_versions) documents,(SELECT SUM(bytes) FROM archives) archive_bytes"),
            "jobs":db.rows("SELECT * FROM jobs ORDER BY id DESC LIMIT 30"),"sources":db.rows("SELECT * FROM source_pages ORDER BY amc_match,id"),
            "benchmarks":db.rows("SELECT name,MIN(date) first,MAX(date) last,COUNT(*) points FROM benchmark GROUP BY name"),
            "data_location":str(db.DATA),"server_time":db.now()}


@app.post('/api/refresh')
async def refresh(request:Request):
    body=await request.json();kind=body.get('kind','all')
    kinds=['nav','benchmark','documents','metrics'] if kind=='all' else [kind]
    try:return {"started":{k:updater.launch(k) for k in kinds}}
    except ValueError as e:raise HTTPException(400,str(e))


@app.post('/api/settings')
async def settings(request:Request):
    body=await request.json();allowed={'nav_interval_minutes':(30,1440),'disclosure_interval_hours':(6,168)}
    with db.connect() as c:
        for k,v in body.items():
            if k=='auto_update' and type(v) is bool:pass
            elif k in allowed and type(v) is int and allowed[k][0]<=v<=allowed[k][1]:pass
            else:raise HTTPException(400,"Invalid update setting")
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(k,json.dumps(v)))
    return {'ok':True}


@app.post('/api/sources')
async def add_source(request:Request):
    b=await request.json()
    if not b.get('amc_match') or not b.get('label'):raise HTTPException(400,"Choose a fund house and enter a label")
    try:providers.public_url(b['url'])
    except (ValueError,OSError,KeyError) as e:raise HTTPException(400,str(e))
    with db.connect() as c:c.execute("INSERT OR IGNORE INTO source_pages(amc_match,url,label) VALUES(?,?,?)",(b['amc_match'][:100],b['url'],b['label'][:150]))
    return {'ok':True}


@app.post('/api/sources/{source_id}')
async def toggle_source(source_id:int,request:Request):
    b=await request.json()
    if type(b.get('enabled')) is not bool:raise HTTPException(400,'enabled must be true or false')
    with db.connect() as c:c.execute("UPDATE source_pages SET enabled=? WHERE id=?",(int(b['enabled']),source_id))
    return {'ok':True}


@app.get('/api/archive/{content_hash}')
def download_archive(content_hash:str):
    if not re.fullmatch('[0-9a-f]{64}',content_hash):raise HTTPException(404)
    r=db.one("SELECT * FROM archives WHERE hash=?",(content_hash,))
    if not r:raise HTTPException(404,'Archived file is unavailable')
    p=(db.DATA/r['path']).resolve()
    if not p.is_relative_to(db.DATA) or not p.is_file():raise HTTPException(404,'Archived file is missing; original link remains available')
    typ=r['media_type'] or ''
    ext='.pdf' if 'pdf' in typ else '.xlsx' if 'spreadsheetml' in typ else '.xls' if 'excel' in typ else '.xml' if 'xml' in typ else '.html' if 'html' in typ else '.json' if 'json' in typ else '.csv' if 'csv' in typ else '.txt'
    # Some public CDNs serve documents as application/octet-stream.
    # Preserve a usable extension while always downloading as an attachment.
    if ext=='.txt':
        with p.open('rb') as stream:signature=stream.read(8)
        if signature.startswith(b'%PDF-'):ext='.pdf'
        elif signature.startswith(b'\xd0\xcf\x11\xe0'):ext='.xls'
        elif signature.startswith(b'PK\x03\x04'):
            try:
                with zipfile.ZipFile(p) as z:
                    if 'xl/workbook.xml' in z.namelist():ext='.xlsx'
            except zipfile.BadZipFile:pass
    return FileResponse(p,filename='source-'+content_hash[:12]+ext,media_type='application/octet-stream')


def csv_response(records,filename):
    s=io.StringIO(newline='')
    if records:
        w=csv.DictWriter(s,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    return Response(s.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{filename}"'})


@app.get('/api/export/nav/{code}')
def export_nav(code:int):
    scheme(code)
    return csv_response(db.rows("SELECT date,value AS nav,source,observed_at FROM nav WHERE code=? ORDER BY date",(code,)),f'nav-{code}.csv')


@app.get('/api/export/metrics/{code}')
def export_metrics(code:int):
    s=scheme(code)
    return csv_response(db.rows("SELECT metric,plan,as_of,value,unit,source,observed_at FROM metrics WHERE family=? ORDER BY as_of",(s['family'],)),f'metrics-{code}.csv')


@app.get('/api/export/portfolio/{snapshot_id}')
def export_portfolio(snapshot_id:int):
    p=holdings(snapshot_id)
    return csv_response([{k:h[k] for k in ('isin','name','sector','weight','asset_type')} for h in p['holdings']],f'portfolio-{p["as_of"]}.csv')


@app.get('/api/export/backup')
def backup():
    temp=Path(tempfile.mkdtemp(prefix='smallcap-backup-'))
    with db.connect() as source:
        dest=sqlite3.connect(temp/'ledger.sqlite3');source.backup(dest);dest.close()
    zpath=temp/'smallcap-data-backup.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(temp/'ledger.sqlite3','data/ledger.sqlite3')
        for p in (db.DATA/'archive').rglob('*'):
            if p.is_file() and p.suffix!='.tmp':z.write(p,'data/'+str(p.relative_to(db.DATA)))
        z.writestr('RESTORE.txt','Close Smallcap Ledger first. Copy the data folder from this ZIP over the data folder in your app. Keep a backup of your current data before restoring. Reopen START-WINDOWS.cmd.\n')
    import shutil
    return FileResponse(zpath,filename='smallcap-data-backup.zip',background=BackgroundTask(shutil.rmtree,temp))


@app.post('/api/import')
async def import_csv(file:UploadFile=File(...),kind:str=Form(...),code:int=Form(0),source:str=Form(...),as_of:str=Form(''),
                     benchmark:str=Form(providers.BENCHMARK),complete:bool=Form(False),coverage_from:str=Form(''),coverage_to:str=Form(''),
                     title:str=Form(''),document_kind:str=Form('disclosure'),scope:str=Form('Fund')):
    content=await file.read(10*1024*1024+1)
    if len(content)>10*1024*1024:raise HTTPException(400,'Maximum import size is 10 MB')
    if not source.startswith(('http://','https://')):raise HTTPException(400,'Provide the original public source URL')
    try:
        if kind=='document':
            s=scheme(code);ext=Path(file.filename or '').suffix.lower()
            types={'.pdf':'application/pdf','.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','.xls':'application/vnd.ms-excel','.xml':'application/xml','.csv':'text/csv'}
            if ext not in types or document_kind not in ('factsheet','portfolio','disclosure','scheme document','market view') or scope not in ('Fund','AMC'):
                raise ValueError('Choose a supported document type and scope')
            h=db.archive(content,types[ext]);did=providers.save_document(s['family'],title.strip() or file.filename,source,document_kind,scope,origin='User import · AMC source')
            providers.doc_version(did,h);parse_note='Original document archived.'
            try:
                if ext=='.xml':disclosures.summary_xml(content,s['family'],source,h)
                elif ext in ('.xls','.xlsx'):disclosures.spreadsheet(content,s['family'],source,h)
                elif ext=='.pdf' and document_kind in ('factsheet','portfolio'):disclosures.factsheet_pdf(content,s['family'],source,h)
            except Exception:parse_note+=' Layout could not be parsed automatically; the original remains available.'
            return {'ok':True,'rows':1,'kind':kind,'note':parse_note}
        records=list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
        if not records or len(records)>100000:raise ValueError('CSV must contain 1–100,000 records')
        h=db.archive(content,'text/csv')
        if kind=='benchmark':
            if not benchmark.strip() or not re.search(r'TRI|total.return',benchmark,re.I):raise ValueError('Benchmark name must identify a total-return index (TRI)')
            points=[(providers.iso(r['date']),providers.number(r['value'])) for r in records]
            if any(v<=0 or d>date.today().isoformat() for d,v in points):raise ValueError('Benchmark values must be positive and dates cannot be in the future')
            db.save_benchmark(benchmark.strip(),points,source)
        elif kind=='portfolio':
            s=scheme(code);day=providers.iso(as_of)
            if day>date.today().isoformat():raise ValueError('Portfolio date cannot be in the future')
            positions=[{'name':r['name'].strip(),'isin':r.get('isin') or None,'sector':r.get('sector') or None,'weight':providers.number(r['weight']),'asset_type':r.get('asset_type') or 'Equity'} for r in records]
            if any(not p['name'] for p in positions):raise ValueError('Each holding needs a name')
            if complete and not 95<=sum(p['weight'] for p in positions)<=105:raise ValueError('A complete portfolio must total approximately 100%; include cash and other assets, or leave completeness unchecked')
            disclosures.portfolio(s['family'],day,positions,complete,source,h)
        elif kind=='metrics':
            s=scheme(code);valid=[]
            allowed={'aum','ter','base_expense_ratio','brokerage','transaction_cost','statutory_levies','exit_load','benchmark','managers','fund_launch','objective','risk','minimum_sip','minimum_lumpsum'}
            numeric={'aum','ter','base_expense_ratio','brokerage','transaction_cost','statutory_levies','minimum_sip','minimum_lumpsum'}
            for r in records:
                name=r['metric'];plan=r.get('plan') or 'All';day=providers.iso(r['as_of'])
                if name not in allowed or plan not in ('All','Direct','Regular') or day>date.today().isoformat():raise ValueError('Unknown metric, plan or future date')
                value=providers.number(r['value']) if name in numeric else r['value']
                if name in numeric and value<0:raise ValueError('Metric cannot be negative')
                unit='INR crore' if name=='aum' else '% p.a.' if name in ('ter','base_expense_ratio','brokerage','transaction_cost','statutory_levies') else 'INR' if name.startswith('minimum_') else 'Reported'
                if name in ('ter','base_expense_ratio') and value>10:raise ValueError('Fee must be percentage points, e.g. 0.65 for 0.65%')
                valid.append((plan,name,day,value,unit))
            for plan,name,day,value,unit in valid:db.metric(s['family'],plan,name,day,value,unit,source,h)
        elif kind=='distributions':
            s=scheme(code)
            if s['option']!='IDCW':raise ValueError('Select an IDCW scheme')
            first=providers.iso(coverage_from);last=providers.iso(coverage_to)
            if not complete or first>last or last>date.today().isoformat():raise ValueError('Confirm complete payout history and specify a valid coverage window')
            events=[(code,providers.iso(r['ex_date']),providers.number(r['amount']),providers.number(r['reinvestment_nav']),source,db.now()) for r in records]
            if any(x[2]<0 or x[3]<=0 or not first<=x[1]<=last for x in events):raise ValueError('Invalid distribution value or date outside coverage')
            with db.connect() as c:
                # The source document is versioned; replace the declared window atomically
                # so an ex-date correction does not leave a duplicate old distribution.
                c.execute('DELETE FROM distributions WHERE code=? AND ex_date BETWEEN ? AND ?',(code,first,last))
                c.executemany('INSERT OR REPLACE INTO distributions VALUES(?,?,?,?,?,?)',events)
                c.execute('INSERT OR REPLACE INTO distribution_coverage VALUES(?,?,?,?,?)',(code,first,last,source,db.now()))
            did=providers.save_document(s['family'],'Imported IDCW distribution history',source,'disclosure','Fund',origin='User import');providers.doc_version(did,h)
        else:raise ValueError('Unsupported import type')
        with db.connect() as c:c.execute('INSERT INTO fetches(url,fetched_at,status,hash,detail) VALUES(?,?,?,?,?)',(source,db.now(),'imported',h,kind))
        return {'ok':True,'rows':len(records),'kind':kind}
    except (ValueError,KeyError,UnicodeError) as e:raise HTTPException(400,'Import not accepted: '+str(e))


@app.get('/api/templates/{kind}')
def template(kind:str):
    templates={'benchmark':'date,value\n','portfolio':'isin,name,sector,weight,asset_type\n','metrics':'metric,plan,as_of,value\n','distributions':'ex_date,amount,reinvestment_nav\n'}
    if kind not in templates:raise HTTPException(404)
    return Response(templates[kind],media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind}-template.csv"'})

app.mount('/',StaticFiles(directory=db.ROOT/'dist',html=True),name='web')
