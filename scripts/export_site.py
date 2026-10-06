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
from tracker.csv_safe import safe_record

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


def fund_slug(value):
    slug=re.sub(r'[^a-z0-9]+','-',str(value).lower()).strip('-')
    return slug or 'fund'


def public_base_url(repository):
    parts=str(repository or '').strip('/').split('/')
    if len(parts)!=2 or not all(parts):
        return ''
    owner,name=parts
    return f"https://{owner.lower()}.github.io/{name}/"


def preferred_family_series(rows):
    """Choose one stable representative for each family, preferring Direct Growth."""
    chosen={}
    def rank(row):
        return (
            0 if row.get('plan')=='Direct' else 1,
            0 if row.get('option')=='Growth' else 1,
            int(row.get('code') or 0),
        )
    for row in rows:
        family=row['family']
        if family not in chosen or rank(row)<rank(chosen[family]):
            chosen[family]=row
    return [chosen[k] for k in sorted(chosen)]


def _seo_value(metric,suffix=''):
    if not metric or metric.get('value') in (None,''):return 'Not available'
    return html.escape(str(metric['value']))+suffix


def render_fund_landing(row,base_url):
    family=html.escape(row['family']);amc=html.escape(row.get('amc') or '')
    slug=fund_slug(row['family']);canonical=base_url+f"funds/{slug}/" if base_url else ''
    nav=row.get('nav') or {};metrics=row.get('metrics') or {}
    fee=metrics.get('ter') or metrics.get('ter_observed') or metrics.get('base_expense_ratio') or metrics.get('expense_ratio')
    benchmark=metrics.get('benchmark')
    portfolio=row.get('portfolio')
    description=(
        f"{row['family']} mutual fund: NAV, AUM, expense ratio, returns, benchmark "
        "and portfolio reporting dates with AMC source evidence."
    )
    interactive=(base_url+f"#/fund/{row['code']}") if base_url else f"../../#/fund/{row['code']}"
    root=base_url or "../../"
    facts=[
        ("NAV",("₹"+html.escape(str(nav.get('value')))) if nav.get('value') is not None else "Not available",
         nav.get('date')),
        ("AUM",_seo_value(metrics.get('aum')," ₹ crore"),metrics.get('aum',{}).get('as_of') if metrics.get('aum') else None),
        ("Expense",_seo_value(fee,"% p.a."),fee.get('as_of') if fee else None),
        ("Benchmark",html.escape(str(benchmark.get('value'))) if benchmark else "Not available",
         benchmark.get('as_of') if benchmark else None),
        ("Portfolio",("Complete" if portfolio and portfolio.get('complete') else "Partial" if portfolio else "Not available"),
         portfolio.get('as_of') if portfolio else None),
    ]
    returns=row.get('returns') or {}
    return_rows=''.join(
        f"<tr><th>{html.escape(label)}</th><td>{value}</td><td>{html.escape(str(day)) if day else '—'}</td></tr>"
        for label,value,day in facts
    )
    perf=''.join(
        f"<li><strong>{label}</strong>: {html.escape(f'{returns.get(year):.2f}%') if returns.get(year) is not None else 'Not available'}</li>"
        for label,year in (("1Y return","1"),("3Y CAGR","3"),("5Y CAGR","5"))
    )
    structured={
        "@context":"https://schema.org",
        "@type":"FinancialProduct",
        "name":row['family'],
        "provider":{"@type":"Organization","name":row.get('amc') or ''},
        "url":canonical or None,
        "description":description,
    }
    canonical_tag=f'<link rel="canonical" href="{html.escape(canonical)}">' if canonical else ''
    og_url=f'<meta property="og:url" content="{html.escape(canonical)}">' if canonical else ''
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{family} · Smallcap Ledger</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{family} · Smallcap Ledger">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="website">
{og_url}
{canonical_tag}
<link rel="stylesheet" href="../../style.css">
</head>
<body>
<main style="max-width:900px;margin:3rem auto;padding:0 1.25rem">
<p><a href="{html.escape(root)}">← Smallcap Ledger</a></p>
<h1>{family}</h1>
<p>{amc} · {html.escape(str(row.get('plan') or ''))} · {html.escape(str(row.get('option') or ''))}</p>
<p>This crawlable summary uses retained dated observations. Missing values are not estimated.</p>
<h2>Latest reported data</h2>
<table><thead><tr><th>Metric</th><th>Value</th><th>Reporting date</th></tr></thead><tbody>{return_rows}</tbody></table>
<h2>Performance</h2><ul>{perf}</ul>
<p><a href="{html.escape(interactive)}">Open interactive fund research →</a></p>
</main>
<script type="application/ld+json">{json.dumps(structured,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')}</script>
</body>
</html>"""


def render_fund_directory(rows,base_url):
    links=''.join(
        f'<li><a href="{html.escape((base_url if base_url else "../")+"funds/"+fund_slug(r["family"])+"/")}">{html.escape(r["family"])}</a> · {html.escape(r.get("amc") or "")}</li>'
        for r in rows
    )
    canonical=base_url+"funds/" if base_url else ''
    canonical_tag=f'<link rel="canonical" href="{html.escape(canonical)}">' if canonical else ''
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Indian small-cap mutual funds · Smallcap Ledger</title>
<meta name="description" content="Browse Indian small-cap mutual fund pages with dated NAV, AUM, expenses, returns, benchmark and portfolio information.">
{canonical_tag}<link rel="stylesheet" href="../style.css"></head><body>
<main style="max-width:900px;margin:3rem auto;padding:0 1.25rem"><p><a href="{html.escape(base_url or '../')}">← Smallcap Ledger</a></p>
<h1>Indian small-cap mutual funds</h1><p>Dated fund summaries with AMC source evidence.</p><ul>{links}</ul></main></body></html>"""


def write_discoverability(output,index,repository):
    rows=preferred_family_series(index['funds']);base=public_base_url(repository)
    root=output/'funds';root.mkdir(exist_ok=True)
    (root/'index.html').write_text(render_fund_directory(rows,base),encoding='utf-8')
    urls=[]
    for row in rows:
        slug=fund_slug(row['family']);folder=root/slug;folder.mkdir(exist_ok=True)
        (folder/'index.html').write_text(render_fund_landing(row,base),encoding='utf-8')
        if base:urls.append(base+f"funds/{slug}/")
    if base:
        all_urls=[base,base+'funds/',*urls]
        xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(
            f'<url><loc>{html.escape(url)}</loc></url>\n' for url in all_urls
        )+'</urlset>\n'
        (output/'sitemap.xml').write_text(xml,encoding='utf-8')
        (output/'robots.txt').write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n",encoding='utf-8')
    return rows


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
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(safe_record(r) for r in rows)
    index=funds();write('funds.json',index)
    seo_rows=write_discoverability(output,index,repository)
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
    print(json.dumps({'site':str(output),'bytes':total,'funds':len(done),'series':len(index['funds']),'seo_fund_pages':len(seo_rows),'aum_funds':report['counts']['aum_funds'],'fee_funds':report['counts']['fee_funds'],'latest_nav_date':report['counts']['latest_nav_date'],'official_publication_files':len(hashes),'official_publication_bytes':published_publication_bytes},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'site');p.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY',''));a=p.parse_args();export(a.output,a.repository)
