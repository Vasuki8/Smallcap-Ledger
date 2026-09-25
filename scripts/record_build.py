"""Commit the deployed collection and coverage audits after each successful build."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
status=json.loads((ROOT/'site/data/status.json').read_text())
coverage=json.loads((ROOT/'site/data/coverage.json').read_text())

from tracker.portfolio_recovery_queue import report as recovery_queue_report, markdown as recovery_queue_markdown
recovery_queue=recovery_queue_report()
queue_json=ROOT/'docs'/'PORTFOLIO-RECOVERY-QUEUE.json'
queue_json.write_text(json.dumps(recovery_queue,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
queue_md=ROOT/'docs'/'PORTFOLIO-RECOVERY-QUEUE.md'
queue_md.write_text(recovery_queue_markdown(recovery_queue),encoding='utf-8')

target=ROOT/'deployment/update-status.json';target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps({'built_at':status['server_time'],'counts':status['counts'],'recent_jobs':[{k:j[k] for k in ('kind','started_at','finished_at','status')} for j in status['jobs'][:4]],'schedule':status['hosting']},indent=2)+'\n')

coverage_json=ROOT/'COVERAGE-AS-OF.json'
coverage_json.write_text(json.dumps(coverage,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def esc(value):
    return str(value or '').replace('|','\\|').replace('\n',' ')

def number(value,places=2):
    try:return f"{float(value):,.{places}f}"
    except (TypeError,ValueError):return str(value or 'Gap')

def aum_cell(row):
    x=row.get('aum')
    if not x:return 'Gap'
    return f"₹ {number(x['value'])} · {esc(x['as_of'])}"

def fee_cell(row):
    x=row.get('fee')
    if not x:return 'Gap'
    labels={'ter':'TER','ter_observed':'TER · observed','base_expense_ratio':'BER','expense_ratio':'Expense ratio · type not specified'}
    return f"{number(x['value'],4).rstrip('0').rstrip('.')}% {labels.get(x.get('metric'),esc(x.get('metric')))} · {esc(x['as_of'])}"

def portfolio_cell(row):
    x=row.get('portfolio')
    if not x:return 'Gap'
    quality='complete' if x.get('complete') else 'partial'
    freshness='current' if row.get('portfolio_fresh') else 'older'
    return f"{x.get('positions',0)} positions · {esc(x.get('as_of'))} · {quality} · {freshness}"

def benchmark_cell(row):
    x=row.get('benchmark')
    if not x:return 'Gap'
    return f"{esc(x.get('value'))} · {esc(x.get('as_of'))}"

counts=coverage['counts'];c=status['counts']
lines=[
    '# Included data coverage','',
    f"Prepared: {coverage['built_at']}",'',
    f"**{counts['funds']} funds, {c['plans']} NAV series, {c['nav_points']:,} NAV observations. Latest included NAV: {c.get('latest_nav_date','Gap')}.**",'',
    f"AUM: **{counts['aum']} / {counts['funds']} funds**. Direct fee figure: **{counts.get('fee',0)} / {counts['funds']} funds**. Portfolio: **{counts['portfolio']} / {counts['funds']} any**, **{counts.get('portfolio_complete',0)} complete**, **{counts.get('portfolio_fresh',0)} current**, **{counts.get('portfolio_fresh_complete',0)} current + complete** (expected month-end {coverage.get('portfolio_expected_as_of','Gap')}). Reported benchmark identity: **{counts['benchmark_identity']} / {counts['funds']} funds**.",'',
    'Values retain their own reporting or observation dates. AUM is fund-wide in ₹ crore; do not add Direct and Regular rows together. TER, BER and an unqualified expense-ratio observation are distinct and remain labelled separately. A gap means no verified record has been collected, not zero.','',
    '| Fund | AUM · ₹ Cr / date | Direct fee / date | Latest parsed portfolio | Reported benchmark / date | AMC publications |',
    '| --- | --- | --- | --- | --- | ---: |',
]
for row in coverage['funds']:
    lines.append('| '+' | '.join([
        esc(row['family']),aum_cell(row),fee_cell(row),portfolio_cell(row),benchmark_cell(row),str(row.get('official_publications',0))
    ])+' |')
gap_labels={
    'facts_only_no_portfolio':'Facts parsed; no holdings',
    'unsupported_document_layout':'Unsupported document layout',
    'source_unavailable':'Source unavailable',
    'source_not_exposing_portfolio':'Source checked; no portfolio exposed',
    'no_portfolio_document':'No portfolio/factsheet document identified',
    'no_official_document':'No official document collected',
    'document_not_archived':'Document known but not archived',
    'document_not_parsed':'Archived document not parsed',
    'extraction_error':'Parser error',
    'no_holdings_extracted':'No holdings extracted',
}
gaps=[row for row in coverage['funds'] if row.get('portfolio_gap')]
if gaps:
    lines.extend(['','## Portfolio gap diagnosis','',
        '| Fund | Diagnosis | Latest official portfolio/factsheet | Parser evidence | Latest source check |',
        '| --- | --- | --- | --- | --- |'])
    for row in gaps:
        audit=row['portfolio_gap'];doc=audit.get('document') or {};ext=audit.get('extraction') or {};source=audit.get('source_page') or {}
        doc_text='Gap'
        if doc:
            doc_text=f"{esc(doc.get('kind'))}: {esc(doc.get('title'))}"
            if doc.get('observed_at'):doc_text+=f" · archived {esc(doc.get('observed_at'))[:10]}"
        parser='Gap'
        if ext:
            parser=f"{esc(ext.get('status'))} · {ext.get('records',0)} records"
            if ext.get('detail'):parser+=f" · {esc(ext.get('detail'))[:120]}"
        source_text='Gap'
        if source:
            source_text=f"{esc(source.get('status'))}"
            if source.get('last_checked'):source_text+=f" · {esc(source.get('last_checked'))[:10]}"
            if source.get('detail'):source_text+=f" · {esc(source.get('detail'))[:100]}"
        lines.append('| '+' | '.join([
            esc(row['family']),gap_labels.get(audit.get('reason'),esc(audit.get('reason'))),doc_text,parser,source_text
        ])+' |')

lines.extend(['','## Notes',''])
for note in coverage.get('notes',[]):lines.append('- '+esc(note))
lines.extend([
    '- AUM now includes the official AMFI fund-performance feed when it provides a plausible category-wide daily response; the original dated response is retained as source evidence.',
    '- Fund communications remains restricted to AMC-origin publications. The public Pages site carries a bounded set of saved binaries; the cumulative tracker-history release retains full saved history.',
    '- Source URLs and structured per-fund records are available in COVERAGE-AS-OF.json and on the live fund pages.',''
])
(ROOT/'COVERAGE-AS-OF.md').write_text('\n'.join(lines),encoding='utf-8')

def git(*args,check=True):return subprocess.run(['git',*args],cwd=ROOT,check=check)
git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
git('add','deployment','COVERAGE-AS-OF.json','COVERAGE-AS-OF.md',
    'docs/PORTFOLIO-RECOVERY-QUEUE.json','docs/PORTFOLIO-RECOVERY-QUEUE.md')
if git('diff','--cached','--quiet',check=False).returncode:
    git('commit','-m','Record daily collection status and coverage [skip ci]')
    git('pull','--rebase','origin','main')
    git('push','origin','HEAD:main')
