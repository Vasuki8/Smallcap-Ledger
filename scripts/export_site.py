"""Export the live SQLite archive into a fully static GitHub Pages website."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['SMALLCAP_NO_SCHEDULER']='1'
from tracker import db
from tracker.app import funds,fund,holdings,documents,status


def export(output:Path,repository=''):
    output=output.resolve()
    if output==ROOT or output==db.DATA or output==ROOT/'dist':raise ValueError('Choose a separate generated site folder')
    if output.exists():shutil.rmtree(output)
    shutil.copytree(ROOT/'dist',output)
    data=output/'data';data.mkdir()
    downloads={}
    def write(path,record):
        p=data/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(record,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    def csv_file(path,rows,fields):
        p=data/path;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    db.init()
    index=funds();write('funds.json',index)
    from tracker.coverage import report as coverage_report
    write('coverage.json',coverage_report())
    done=set();snapshot_ids=set();hashes=set()
    for s in index['funds']:
        code=s['code'];detail=fund(code);family_id=hashlib.sha256(s['family'].encode()).hexdigest()[:20];detail['family_id']=family_id
        detail['distributions']=db.rows('SELECT * FROM distributions WHERE code=? ORDER BY ex_date',(code,))
        write(Path('funds')/f'{code}.json',detail)
        nav=db.rows('SELECT date,value AS nav,source,observed_at FROM nav WHERE code=? ORDER BY date',(code,))
        write(Path('nav')/f'{code}.json',[[p['date'],p['nav']] for p in nav])
        csv_file(Path('downloads')/f'nav-{code}.csv',nav,['date','nav','source','observed_at'])
        downloads[f'/api/export/nav/{code}']=f'data/downloads/nav-{code}.csv'
        downloads[f'/api/export/metrics/{code}']=f'data/downloads/metrics-{family_id}.csv'
        snapshot_ids.update(p['id'] for p in detail['portfolios'])
        if family_id not in done:
            done.add(family_id);docs=documents(code)
            assert not any(d['kind']=='news' for d in docs)
            write(Path('communications')/f'{family_id}.json',docs)
            hashes.update(v['hash'] for d in docs for v in d['versions'])
            csv_file(Path('downloads')/f'metrics-{family_id}.csv',detail['metric_history'],['metric','plan','as_of','value','unit','source','observed_at'])
    for sid in snapshot_ids:
        p=holdings(sid);write(Path('portfolios')/f'{sid}.json',p)
        csv_file(Path('downloads')/f'portfolio-{sid}.csv',p['holdings'],['isin','name','sector','weight','asset_type'])
        downloads[f'/api/export/portfolio/{sid}']=f'data/downloads/portfolio-{sid}.csv'
    benchmark={}
    for b in db.rows('SELECT name,MIN(date) first,MAX(date) last,COUNT(*) points FROM benchmark GROUP BY name'):
        b['source']=db.one('SELECT source FROM benchmark WHERE name=? ORDER BY date DESC LIMIT 1',(b['name'],))['source']
        b['data']=[[p['date'],p['value']] for p in db.rows('SELECT date,value FROM benchmark WHERE name=? ORDER BY date',(b['name'],))]
        benchmark[b['name']]=b
    write('benchmarks.json',benchmark)
    # Only AMC publications are exposed as files. Raw NAV responses remain in the
    # full private/local archive; archived web pages are served as inert text.
    for h in sorted(hashes):
        a=db.one('SELECT * FROM archives WHERE hash=?',(h,));original=db.DATA/a['path'];typ=a['media_type'] or ''
        if not original.is_file():raise RuntimeError('Missing original publication '+h)
        signature=original.read_bytes()[:8]
        ext='.pdf' if signature.startswith(b'%PDF-') else '.xlsx' if signature.startswith(b'PK') and ('sheet' in typ or 'excel' in typ or 'octet' in typ) else '.xls' if signature.startswith(b'\xd0\xcf') else '.xml' if 'xml' in typ and 'html' not in typ else '.csv' if 'csv' in typ else '.txt'
        dest=data/'files'/(h+ext);dest.parent.mkdir(exist_ok=True);shutil.copyfile(original,dest)
        downloads['/api/archive/'+h]='data/files/'+dest.name
    write('downloads.json',downloads)
    report=status();report['running']={};report['data_location']='Daily GitHub archive';report['jobs']=[j for j in report['jobs'] if j['kind']!='news']
    report['hosting']={'provider':'GitHub Pages','repository':repository,'timezone':'Asia/Kolkata','schedule':'00:00 IST daily','cron':'30 18 * * *','scheduled_time_is_not_guaranteed':True}
    report['counts']['aum_funds']=len({s['family'] for s in index['funds'] if s['metrics'].get('aum')})
    report['counts']['fee_funds']=len({s['family'] for s in index['funds'] if any(s['metrics'].get(k) for k in ('ter','ter_observed','base_expense_ratio'))})
    write('status.json',report)
    config={'mode':'github','repository':repository,'timezone':'Asia/Kolkata','schedule':'00:00 IST daily'}
    (output/'runtime-config.js').write_text('window.SMALLCAP_CONFIG='+json.dumps(config)+';\n')
    (output/'.nojekyll').write_text('')
    total=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total>900*1024*1024:raise RuntimeError('Site approaches the GitHub Pages size limit; existing online version should be retained.')
    print(json.dumps({'site':str(output),'bytes':total,'funds':len(done),'series':len(index['funds']),'aum_funds':report['counts']['aum_funds'],'fee_funds':report['counts']['fee_funds'],'official_publication_files':len(hashes)},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'site');p.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY',''));a=p.parse_args();export(a.output,a.repository)
