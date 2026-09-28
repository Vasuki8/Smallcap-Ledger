"""Commit the deployed collection and coverage audits after each successful build."""
import json
import os
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

from tracker.performance_coverage import report as performance_coverage_report, markdown as performance_coverage_markdown
performance_coverage=performance_coverage_report()
performance_json=ROOT/'docs'/'PERFORMANCE-COVERAGE-AUDIT.json'
performance_json.write_text(json.dumps(performance_coverage,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
performance_md=ROOT/'docs'/'PERFORMANCE-COVERAGE-AUDIT.md'
performance_md.write_text(performance_coverage_markdown(performance_coverage),encoding='utf-8')

from tracker.publication_coverage import report as publication_coverage_report, markdown as publication_coverage_markdown
from tracker.publication_provenance import push_generated_status_commit
publication_coverage=publication_coverage_report()
publication_json=ROOT/'docs'/'PUBLICATION-COVERAGE-AUDIT.json'
publication_json.write_text(json.dumps(publication_coverage,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
publication_md=ROOT/'docs'/'PUBLICATION-COVERAGE-AUDIT.md'
publication_md.write_text(publication_coverage_markdown(publication_coverage),encoding='utf-8')

target=ROOT/'deployment/update-status.json';target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps({'built_at':status['server_time'],'counts':status['counts'],'record_dates':status.get('record_dates',{}),'recent_jobs':[{k:j[k] for k in ('kind','started_at','finished_at','status')} for j in status['jobs'][:4]],'schedule':status['hosting']},indent=2)+'\n')

coverage_json=ROOT/'COVERAGE-AS-OF.json'
coverage_json.write_text(json.dumps(coverage,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

# Current operational storage health. Historical STORAGE-AUDIT / STORAGE-VALIDATION
# files remain immutable evidence of the 2026-09-25 migration.
from tracker import db
from tracker.release_health import release_health
db.init()
with db.connect() as connection:
    integrity=connection.execute('PRAGMA integrity_check').fetchone()[0]
    foreign_keys=[dict(row) for row in connection.execute('PRAGMA foreign_key_check').fetchall()]
retention_rows=db.rows("""SELECT binary_state,COUNT(*) files,COALESCE(SUM(a.bytes),0) bytes
    FROM archive_retention r JOIN archives a ON a.hash=r.hash
    GROUP BY binary_state ORDER BY binary_state""")
retention_by_state={row['binary_state']:{'files':row['files'],'bytes':row['bytes']}
                    for row in retention_rows}
hosting=status['hosting']
hard_budget=int(hosting.get('publication_file_budget_bytes') or 0)
selected_bytes=int(hosting.get('publication_bytes_included') or 0)
selection_limit=int(hosting.get('publication_selection_limit_bytes') or hard_budget)
release_archive=release_health()
storage_health={
    'checked_at':status['server_time'],
    'scope':'current_production_operational_health',
    'database':{
        'bytes':int(status['counts'].get('database_bytes') or 0),
        'integrity':integrity,
        'foreign_key_violations':foreign_keys,
    },
    'archive':{
        'files':int(status['counts'].get('archive_binary_files') or 0),
        'bytes':int(status['counts'].get('archive_bytes') or 0),
        'metadata_only_files':int(status['counts'].get('archive_metadata_only_files') or 0),
        'metadata_only_bytes':int(status['counts'].get('archive_metadata_only_bytes') or 0),
        'retention_by_binary_state':retention_by_state,
    },
    'release_archive':release_archive,
    'publication':{
        'hard_budget_bytes':hard_budget,
        'reserve_bytes':int(hosting.get('publication_file_reserve_bytes') or 0),
        'selection_limit_bytes':selection_limit,
        'selected_files':int(hosting.get('publication_files_included') or 0),
        'selected_bytes':selected_bytes,
        'headroom_to_selection_limit_bytes':selection_limit-selected_bytes,
        'headroom_to_hard_budget_bytes':hard_budget-selected_bytes,
    },
    'coverage':coverage['counts'],
    'safety':{
        'all_archive_binaries_retained':(
            int(status['counts'].get('archive_metadata_only_files') or 0)==0
            and retention_by_state.get('retained',{}).get('files',0)
                ==int(status['counts'].get('archive_binary_files') or 0)
        ),
        'publication_within_selection_limit':selected_bytes<=selection_limit,
        'database_integrity_ok':integrity=='ok',
        'foreign_keys_ok':not foreign_keys,
    },
    'historical_evidence_note':(
        'docs/STORAGE-AUDIT.json, docs/STORAGE-VALIDATION.json and '
        'deployment/storage-live-verification.json are historical migration/verification '
        'artifacts and are intentionally not overwritten by this current-health report.'
    ),
}
storage_health_path=ROOT/'deployment'/'storage-health.json'
storage_health_path.write_text(json.dumps(storage_health,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

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

counts=coverage['counts'];c=status['counts'];record_dates=coverage.get('record_dates',{})
def record_date_text(key):
    span=record_dates.get(key) or {}
    first=span.get('earliest');last=span.get('latest')
    if not first or not last:return 'Gap'
    return esc(last) if first==last else f"{esc(first)} → {esc(last)}"

lines=[
    '# Included data coverage','',
    f"Prepared: {coverage['built_at']}",'',
    f"**{counts['funds']} funds, {c['plans']} NAV series, {c['nav_points']:,} NAV observations. Latest included NAV: {c.get('latest_nav_date','Gap')}.**",'',
    f"AUM: **{counts['aum']} / {counts['funds']} funds**. Direct fee figure: **{counts.get('fee',0)} / {counts['funds']} funds**. Portfolio: **{counts['portfolio']} / {counts['funds']} any**, **{counts.get('portfolio_complete',0)} complete**, **{counts.get('portfolio_fresh',0)} current**, **{counts.get('portfolio_fresh_complete',0)} current + complete** (expected month-end {coverage.get('portfolio_expected_as_of','Gap')}). Reported benchmark identity: **{counts['benchmark_identity']} / {counts['funds']} funds**.",'',
    f"Selected record dates — AUM: **{record_date_text('aum')}**; Direct fee: **{record_date_text('direct_fee')}**; reported benchmark identity: **{record_date_text('benchmark_identity')}**.",'',
    'Coverage counts mean a selected dated record exists. The ranges above are reporting/effective dates, not source-check timestamps; an older effective date can remain current until superseded. AUM is fund-wide in ₹ crore; do not add Direct and Regular rows together. TER, BER and an unqualified expense-ratio observation are distinct and remain labelled separately. A gap means no verified record has been collected, not zero.','',
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
    'docs/PORTFOLIO-RECOVERY-QUEUE.json','docs/PORTFOLIO-RECOVERY-QUEUE.md',
    'docs/PERFORMANCE-COVERAGE-AUDIT.json','docs/PERFORMANCE-COVERAGE-AUDIT.md',
    'docs/PUBLICATION-COVERAGE-AUDIT.json','docs/PUBLICATION-COVERAGE-AUDIT.md',
    'docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json','docs/MIDCAP-SOURCE-COVERAGE-AUDIT.md',
    'docs/MIDCAP-TER-GAP-AUDIT.json','docs/MIDCAP-TER-GAP-AUDIT.md',
    'docs/MIDCAP-TER-FIRST-PARTY-BATCH1.json','docs/MIDCAP-TER-FIRST-PARTY-BATCH1.md',
    'docs/MIDCAP-TER-FIRST-PARTY-BATCH2.json','docs/MIDCAP-TER-FIRST-PARTY-BATCH2.md',
    'docs/MIDCAP-TER-READINESS.json','docs/MIDCAP-TER-READINESS.md',
    'docs/MIDCAP-BENCHMARK-BATCH1.json','docs/MIDCAP-BENCHMARK-BATCH1.md',
    'docs/MIDCAP-BENCHMARK-BATCH2.json','docs/MIDCAP-BENCHMARK-BATCH2.md',
    'docs/MIDCAP-BENCHMARK-READINESS.json','docs/MIDCAP-BENCHMARK-READINESS.md',
    'docs/MIDCAP-PORTFOLIO-BATCH1.json','docs/MIDCAP-PORTFOLIO-BATCH1.md',
    'docs/MIDCAP-PORTFOLIO-BATCH2.json','docs/MIDCAP-PORTFOLIO-BATCH2.md',
    'docs/MIDCAP-PORTFOLIO-BATCH3.json','docs/MIDCAP-PORTFOLIO-BATCH3.md',
    'docs/MIDCAP-PORTFOLIO-BATCH4.json','docs/MIDCAP-PORTFOLIO-BATCH4.md',
    'docs/MIDCAP-PORTFOLIO-BATCH5.json','docs/MIDCAP-PORTFOLIO-BATCH5.md',
    'docs/MIDCAP-PORTFOLIO-READINESS.json','docs/MIDCAP-PORTFOLIO-READINESS.md',
    'docs/MIDCAP-LAUNCH-READINESS.json','docs/MIDCAP-LAUNCH-READINESS.md',
    'docs/MIDCAP-PORTFOLIO-BATCH3-CONTRACTS.json',
    'docs/RETENTION-PROPOSED-MANIFEST.json','docs/RETENTION-MIGRATION-CANDIDATES.json',
    'docs/RETENTION-REPLACEMENT-SIMULATION.md',
    'docs/SOURCE-RETENTION-DELTA.json','docs/SOURCE-RETENTION-DELTA.md',
    'docs/SOURCE-RETENTION-NEW-CANDIDATES.json',
    'deployment/communication-transport-wealth-uti.json')
if git('diff','--cached','--quiet',check=False).returncode:
    git('commit','-m','Record daily collection status and coverage [skip ci]')
    expected_build_sha=os.environ.get('SMALLCAP_BUILD_SHA','').strip()
    if not expected_build_sha:
        raise RuntimeError('SMALLCAP_BUILD_SHA is required for automated status publication')
    push_generated_status_commit(ROOT,expected_build_sha)
