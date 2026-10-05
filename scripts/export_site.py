"""Export the live SQLite archive into a fully static GitHub Pages website."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['SMALLCAP_NO_SCHEDULER']='1'
from tracker import db
from tracker.app import funds,fund,holdings,documents,status
from tracker.categories import assert_publication_scope

PUBLIC_PUBLICATION_BUDGET=250*1024*1024
# Keep deterministic headroom for publication metadata, routing files and archive
# growth between selection and artifact packaging. This changes only what Pages
# materializes; cumulative originals remain retained in source packs.
PUBLIC_PUBLICATION_RESERVE=5*1024*1024
PUBLIC_PUBLICATION_SELECTION_LIMIT=PUBLIC_PUBLICATION_BUDGET-PUBLIC_PUBLICATION_RESERVE
SITE_SIZE_LIMIT=400*1024*1024


def public_documents(records):
    """Only verified AMC-origin documents are eligible for public Pages export."""
    return [d for d in records if d.get('origin')=='AMC']


def fund_slug(value):
    slug=re.sub(r'[^a-z0-9]+','-',str(value).lower()).strip('-')
    return slug or hashlib.sha256(str(value).encode()).hexdigest()[:12]


def github_pages_root(repository):
    if not repository or '/' not in repository:return None
    owner,name=repository.split('/',1)
    host=f"https://{owner.lower()}.github.io/"
    return host if name.lower()==owner.lower()+'.github.io' else host+name.strip('/')+'/'


def seo_fee(record):
    metrics=record.get('metrics') or {}
    return metrics.get('ter') or metrics.get('ter_observed') or metrics.get('base_expense_ratio') or metrics.get('expense_ratio')


def _display(value,suffix=''):
    if value is None or value=='':return 'Not available'
    return html.escape(str(value))+suffix


def write_crawlable_fund_pages(output,index,repository):
    """Write one semantic HTML landing page per fund family plus crawl metadata."""
    root=github_pages_root(repository)
    ranked={}
    for row in index.get('funds',[]):
        rank=(0 if row.get('plan')=='Direct' and row.get('option')=='Growth' else
              1 if row.get('option')=='Growth' else 2,
              int(row.get('code') or 0))
        current=ranked.get(row['family'])
        if current is None or rank<current[0]:ranked[row['family']]=(rank,row)
    urls=[]
    slugs={}
    for family,(_,row) in sorted(ranked.items()):
        slug=fund_slug(family)
        if slug in slugs and slugs[slug]!=family:
            slug+='-'+hashlib.sha256(family.encode()).hexdigest()[:8]
        slugs[slug]=family
        target=output/'funds'/slug/'index.html';target.parent.mkdir(parents=True,exist_ok=True)
        canonical=(root+'funds/'+slug+'/') if root else None
        title=f"{family} – NAV, AUM, Expense Ratio & Returns | Smallcap Ledger"
        metrics=row.get('metrics') or {};aum=metrics.get('aum');fee=seo_fee(row);benchmark=metrics.get('benchmark')
        description=(f"{family} mutual fund research: latest retained NAV, AUM, expense ratio, "
                     "1Y/3Y/5Y returns, reported benchmark and source dates.")
        facts=[
            ('Plan',f"{row.get('plan','')} · {row.get('option_label') or row.get('option','')}"),
            ('Latest NAV',('₹'+str(row['nav']['value'])) if row.get('nav') else 'Not available'),
            ('AUM',('₹'+str(aum['value'])+' crore') if aum else 'Not available'),
            ('Expense', (str(fee['value'])+'%') if fee else 'Not available'),
            ('1Y return', (str(row.get('returns',{}).get('1'))+'%') if row.get('returns',{}).get('1') is not None else 'Not available'),
            ('3Y CAGR', (str(row.get('returns',{}).get('3'))+'%') if row.get('returns',{}).get('3') is not None else 'Not available'),
            ('5Y CAGR', (str(row.get('returns',{}).get('5'))+'%') if row.get('returns',{}).get('5') is not None else 'Not available'),
            ('Reported benchmark', str(benchmark['value']) if benchmark else 'Not available'),
        ]
        canonical_tag=f'<link rel="canonical" href="{html.escape(canonical,quote=True)}">' if canonical else ''
        og_url=f'<meta property="og:url" content="{html.escape(canonical,quote=True)}">' if canonical else ''
        fact_html=''.join(f'<div class="fact"><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>' for label,value in facts)
        source_notes=[]
        for label,item in [('AUM',aum),('Expense',fee),('Benchmark',benchmark)]:
            if item and item.get('source'):
                source_notes.append(f'<li>{html.escape(label)} · {html.escape(str(item.get("as_of") or "date unavailable"))} · '
                                    f'<a href="{html.escape(item["source"],quote=True)}" rel="nofollow noopener">{html.escape(item["source"])}</a></li>')
        source_html='<ul>'+''.join(source_notes)+'</ul>' if source_notes else '<p>Source details are available in the research desk.</p>'
        target.write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description,quote=True)}">
{canonical_tag}<meta property="og:title" content="{html.escape(title,quote=True)}"><meta property="og:description" content="{html.escape(description,quote=True)}">{og_url}
<link rel="stylesheet" href="../../style.css"></head><body>
<main id="main" style="max-width:1000px;margin:0 auto;padding:32px 20px">
<div class="page-heading"><div><div class="eyebrow">{html.escape(str(row.get('amc') or 'Mutual fund'))}</div><h1>{html.escape(family)}</h1>
<p>{html.escape(description)}</p></div></div>
<section class="panel"><h2>Fund snapshot</h2><dl class="facts">{fact_html}</dl>
<p class="footer-note">Values are retained observations with their own reporting dates. Missing is not zero. Past performance is not a forecast.</p></section>
<section class="panel"><h2>Source evidence</h2>{source_html}</section>
<p><a class="primary-link" href="../../#/fund/{int(row['code'])}">Open interactive research page →</a></p>
</main></body></html>
''',encoding='utf-8')
        if canonical:urls.append(canonical)
    robots="User-agent: *\nAllow: /\n"
    if root:
        sitemap=root+'sitemap.xml';robots+=f"Sitemap: {sitemap}\n"
        all_urls=[root]+urls
        xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml+=''.join(f'  <url><loc>{html.escape(url)}</loc></url>\n' for url in all_urls)
        xml+='</urlset>\n'
        (output/'sitemap.xml').write_text(xml,encoding='utf-8')
    (output/'robots.txt').write_text(robots,encoding='utf-8')
    return {'fund_pages':len(ranked),'sitemap_urls':len(urls)+(1 if root else 0),'site_root':root}


def select_publication_candidates(candidates,limit=PUBLIC_PUBLICATION_SELECTION_LIMIT):
    selected=set();total=0
    for item in sorted(candidates,key=lambda x:(x['priority'],x['date']),reverse=True):
        h=item['hash']
        if h in selected:
            item['doc']['versions']=[item['version']]
            continue
        size=max(0,int(item.get('bytes') or 0))
        if total+size>limit:
            continue
        selected.add(h);total+=size
        item['doc']['versions']=[item['version']]
    return selected,total


def export(output:Path,repository=''):
    output=output.resolve()
    if output==ROOT or output==db.DATA or output==ROOT/'dist':raise ValueError('Choose a separate generated site folder')
    db.init()
    # Fail before deleting/replacing the last known-good output if a staged or
    # ambiguous category ever reaches the retained scheme table.
    publication_rows=db.rows("SELECT code,family,amc,category FROM schemes ORDER BY code")
    assert_publication_scope(publication_rows)
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
    index=funds();write('funds.json',index)
    seo=write_crawlable_fund_pages(output,index,repository)
    from tracker.coverage import report as coverage_report
    coverage=coverage_report()
    write('coverage.json',coverage)
    done=set();snapshot_ids=set();hashes=set();communication_payloads=[];publication_candidates=[]
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
            done.add(family_id);docs=public_documents(documents(code))
            assert all(d.get('origin')=='AMC' and d['kind']!='news' for d in docs)
            # The cumulative tracker-history release retains every archived version.
            # GitHub Pages publishes only a bounded subset of the newest saved copies
            # so growing document history can never block fresh NAV/metric deployment.
            for d in docs:
                versions=d.get('versions') or []
                d['saved_version_count']=len(versions)
                d['versions']=[]
                if versions:
                    latest=versions[0]
                    publication_candidates.append({
                        'date':latest.get('observed_at') or d.get('published_at') or d.get('first_seen') or '',
                        'priority':1 if d.get('kind')!='source page' else 0,
                        'hash':latest['hash'],'bytes':int(latest.get('bytes') or 0),
                        'doc':d,'version':latest})
            communication_payloads.append((family_id,docs))
            csv_file(Path('downloads')/f'metrics-{family_id}.csv',detail['metric_history'],['metric','plan','as_of','value','unit','source','observed_at'])
    hashes,published_publication_bytes=select_publication_candidates(publication_candidates)
    for family_id,docs in communication_payloads:
        write(Path('communications')/f'{family_id}.json',docs)
    for sid in snapshot_ids:
        p=holdings(sid);write(Path('portfolios')/f'{sid}.json',p)
        csv_file(Path('downloads')/f'portfolio-{sid}.csv',p['holdings'],['isin','name','sector','quantity','previous_quantity','share_change','weight','previous_weight','weight_change','asset_type'])
        downloads[f'/api/export/portfolio/{sid}']=f'data/downloads/portfolio-{sid}.csv'
    benchmark={}
    for b in db.rows('SELECT name,MIN(date) first,MAX(date) last,COUNT(*) points FROM benchmark GROUP BY name'):
        b['source']=db.one('SELECT source FROM benchmark WHERE name=? ORDER BY date DESC LIMIT 1',(b['name'],))['source']
        b['data']=[[p['date'],p['value']] for p in db.rows('SELECT date,value FROM benchmark WHERE name=? ORDER BY date',(b['name'],))]
        benchmark[b['name']]=b
    write('benchmarks.json',benchmark)
    # Only AMC publications are exposed as files. Raw NAV responses remain in the
    # full private/local archive; archived web pages are served as inert text.
    missing_publications=[]
    for h in hashes:
        a=db.archive_retention(h)
        if not a or a['binary_state']!='retained':
            raise RuntimeError('Publication points to a metadata-only or unknown source '+h)
        original=db.archive_binary_path(h)
        if not original:
            missing_publications.append(h)
    if missing_publications:
        from scripts.github_state import materialize_hashes
        materialize_hashes(missing_publications)
    for h in sorted(hashes):
        a=db.archive_retention(h);original=db.archive_binary_path(h);typ=a['media_type'] or ''
        if not original:raise RuntimeError('Missing retained original publication '+h)
        signature=original.read_bytes()[:8]
        ext='.pdf' if signature.startswith(b'%PDF-') else '.xlsx' if signature.startswith(b'PK') and ('sheet' in typ or 'excel' in typ or 'octet' in typ) else '.xls' if signature.startswith(b'\xd0\xcf') else '.xml' if 'xml' in typ and 'html' not in typ else '.csv' if 'csv' in typ else '.txt'
        dest=data/'files'/(h+ext);dest.parent.mkdir(exist_ok=True);shutil.copyfile(original,dest)
        downloads['/api/archive/'+h]='data/files/'+dest.name
    write('downloads.json',downloads)
    report=status();report['running']={};report['data_location']='Daily GitHub archive';report['jobs']=[j for j in report['jobs'] if j['kind']!='news']
    report['hosting']={'provider':'GitHub Pages','repository':repository,'timezone':'Asia/Kolkata','schedule':'00:00 IST daily','cron':'30 18 * * *','scheduled_time_is_not_guaranteed':True}
    report['counts']['aum_funds']=coverage['counts']['aum']
    report['counts']['fee_funds']=coverage['counts']['fee']
    report['counts']['latest_nav_date']=db.one('SELECT MAX(date) last FROM nav')['last']
    report['record_dates']=coverage.get('record_dates',{})
    report['hosting']['publication_file_budget_bytes']=PUBLIC_PUBLICATION_BUDGET
    report['hosting']['publication_file_reserve_bytes']=PUBLIC_PUBLICATION_RESERVE
    report['hosting']['publication_selection_limit_bytes']=PUBLIC_PUBLICATION_SELECTION_LIMIT
    report['hosting']['publication_files_included']=len(hashes)
    report['hosting']['publication_bytes_included']=published_publication_bytes
    write('status.json',report)
    config={'mode':'github','repository':repository,'timezone':'Asia/Kolkata','schedule':'00:00 IST daily'}
    (output/'runtime-config.js').write_text('window.SMALLCAP_CONFIG='+json.dumps(config)+';\n')
    (output/'.nojekyll').write_text('')
    total=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total>SITE_SIZE_LIMIT:raise RuntimeError('Site exceeded the configured static publication budget; existing online version should be retained.')
    print(json.dumps({'site':str(output),'bytes':total,'funds':len(done),'series':len(index['funds']),'aum_funds':report['counts']['aum_funds'],'fee_funds':report['counts']['fee_funds'],'latest_nav_date':report['counts']['latest_nav_date'],'official_publication_files':len(hashes),'official_publication_bytes':published_publication_bytes,'crawlable_fund_pages':seo['fund_pages']},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'site');p.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY',''));a=p.parse_args();export(a.output,a.repository)
