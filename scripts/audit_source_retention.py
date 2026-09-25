"""Read-only source-retention proposal; never deletes files or changes a database.

Run against a closed restored checkpoint. Outputs go outside the data directory.
Link-only candidates are superseded discovery responses, not interchangeable
copies: dropping them sacrifices old page snapshots and needs explicit approval.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
from urllib.parse import urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Documented transport boundaries in docs/HANDOFF.md; not a new live probe.
FRAGILE_HOSTS = {'edelweissmf.com', 'unionmf.com', 'bajajamc.com',
                 'archive.icicipruamc.com', 'prod-api-investor.utimf.com'}
BINARY_EXTENSIONS = {'.pdf', '.xls', '.xlsx', '.xlsb', '.xml', '.csv', '.zip',
                     '.doc', '.docx', '.ppt', '.pptx'}
FINANCIAL_TABLES = {'metrics', 'portfolios', 'nav', 'nav_observations', 'benchmark',
                    'benchmark_observations', 'distributions', 'distribution_coverage', 'schemes'}
KNOWN_HASH_TABLES = {'archives', 'archive_retention', 'metrics', 'portfolios', 'fetches',
                     'document_versions', 'document_extractions'}
STATES = ('retain_evidence', 'retain_latest_or_review', 'link_only_candidate')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def quote(value):
    return '"' + value.replace('"', '""') + '"'


def host(url):
    return (urlparse(url).hostname or '').lower().removeprefix('www.')


def valid_url(url):
    try:
        p = urlparse(url)
        return bool(p.scheme in ('http', 'https') and p.hostname and not p.username and not p.password)
    except ValueError:
        return False


def response_kind(media_type, urls):
    paths = [Path(urlparse(u).path.lower()).suffix for u in urls]
    media = (media_type or '').lower().split(';')[0].strip()
    if any(ext in BINARY_EXTENSIONS for ext in paths): return 'publication_or_data_file'
    if media in ('text/html', 'application/xhtml+xml'): return 'html'
    if 'javascript' in media: return 'javascript'
    if media in ('application/json', 'text/json'): return 'json'
    if media == 'text/plain': return 'text'
    return 'publication_or_unknown_binary'


def classify(item):
    """Conservative precedence: any protected use protects the entire shared hash."""
    evidence = item['evidence_reasons']
    if evidence: return 'retain_evidence', sorted(set(evidence))
    reasons = []
    if not item['urls'] or not all(valid_url(u) for u in item['urls']): reasons.append('missing_or_nonportable_source_url')
    if item['kind'] in ('json', 'text'): reasons.append('request_parameters_or_data_semantics_require_review')
    if item['kind'] not in ('html', 'javascript', 'json', 'text'): reasons.append('original_publication_or_unknown_binary')
    if item['latest_for_urls']: reasons.append('latest_saved_response_for_at_least_one_url')
    if item.get('latest_document_ids'): reasons.append('latest_saved_download_for_at_least_one_document')
    if item['fragile_urls']: reasons.append('documented_transport_boundary')
    if item['latest_error_urls']: reasons.append('latest_retained_fetch_or_source_page_status_is_error')
    if item['pending_extractions']: reasons.append('unresolved_extraction_requires_review')
    if not item['superseded_for_all_urls']: reasons.append('no_strictly_newer_saved_response_for_every_url')
    if reasons: return 'retain_latest_or_review', sorted(set(reasons))
    return 'link_only_candidate', ['superseded_discovery_response_without_identified_financial_or_replay_dependency']


def collect(connection, root=ROOT):
    connection.row_factory = sqlite3.Row
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {'archives', 'fetches', 'metrics', 'portfolios', 'documents', 'document_versions'}
    if required - tables: raise ValueError('Missing required tables: ' + ', '.join(sorted(required - tables)))
    items = {}
    for r in connection.execute('SELECT * FROM archives ORDER BY hash'):
        a = dict(r)
        if not re.fullmatch(r'[0-9a-f]{64}', a['hash']) or a['bytes'] < 0: raise ValueError('Invalid archive identity')
        a.update(urls=set(), families=set(), titles=set(), reporting_dates=set(), references=Counter(),
                 evidence_reasons=[], pending_extractions=[], latest_for_urls=[], fragile_urls=[],
                 latest_error_urls=[], latest_document_ids=[], extraction_statuses=Counter())
        items[a['hash']] = a
    if 'archive_retention' in tables:
        for r in connection.execute('SELECT hash,classification,binary_state,reason,reviewed_at FROM archive_retention'):
            row=dict(r);x=items.get(row['hash'])
            if not x:continue
            x['stored_classification']=row['classification']
            x['binary_state']=row['binary_state']
            x['retention_reason']=row.get('reason')
            x['retention_reviewed_at']=row.get('reviewed_at')
    for x in items.values():
        x.setdefault('stored_classification','unclassified')
        x.setdefault('binary_state','retained')
        x.setdefault('retention_reason',None)
        x.setdefault('retention_reviewed_at',None)
    by_url = defaultdict(dict)
    latest_fetch = {}
    missing_hashes = set()

    def attach(h, url='', family='', reason=None, reference=None, when=None):
        if not h: return
        if h not in items:
            missing_hashes.add(h)
            return
        x = items[h]
        if url:
            x['urls'].add(url)
            if when: by_url[url][h] = max(by_url[url].get(h, ''), when)
        if family: x['families'].add(family)
        if reason: x['evidence_reasons'].append(reason)
        if reference: x['references'][reference] += 1

    for r in connection.execute('SELECT * FROM fetches ORDER BY fetched_at,id'):
        r = dict(r)
        latest_fetch[r['url']] = r
        if r['status'] == 'ok' and r.get('hash'):
            attach(r['hash'], r['url'], reference='fetches', when=r['fetched_at'])
    for table in ('metrics', 'portfolios'):
        for row in connection.execute('SELECT * FROM ' + table):
            r = dict(row)
            attach(r.get('hash'), r.get('source', ''), r.get('family', ''),
                   'historical_or_current_' + table + '_hash', table)
            if r.get('hash') in items: items[r['hash']]['reporting_dates'].add(r['as_of'])
    latest_document_pairs = {(r[0], r[1]) for r in connection.execute('''SELECT v.document_id,v.hash FROM document_versions v WHERE v.observed_at=(SELECT MAX(v2.observed_at) FROM document_versions v2 WHERE v2.document_id=v.document_id)''')}
    for row in connection.execute('''SELECT d.*,v.hash,v.observed_at FROM document_versions v
                                    JOIN documents d ON d.id=v.document_id'''):
        r = dict(row)
        attach(r['hash'], r['url'], r['family'], reference='document_versions', when=r['observed_at'])
        x = items.get(r['hash'])
        if not x: continue
        x['titles'].add(r['title'])
        if (r['id'], r['hash']) in latest_document_pairs: x['latest_document_ids'].append(r['id'])
        if r.get('published_at'): x['reporting_dates'].add('document_published:' + r['published_at'])
        # Publications with explicit dates or narrative/notice categories are not generic discovery shells.
        if r.get('published_at') or r['kind'] in ('newsletter', 'letter', 'market view', 'scheme document'):
            x['evidence_reasons'].append('dated_or_narrative_amc_publication')
    if 'document_extractions' in tables:
        for row in connection.execute('SELECT * FROM document_extractions'):
            r = dict(row)
            attach(r.get('hash'), r.get('url', ''), r.get('family', ''), reference='document_extractions')
            x = items.get(r.get('hash'))
            if not x: continue
            status = r.get('status', '')
            x['extraction_statuses'][status] += 1
            if status == 'parsed' or int(r.get('records') or 0) > 0:
                x['evidence_reasons'].append('successful_historical_extraction_including_pruned_portfolio_history')
            elif status == 'error': x['pending_extractions'].append(r.get('parser_version', status))
    # NAV/index/category evidence often has no hash column: preserve all archived versions
    # of the exact financial source URL, including historical alternate observations.
    financial_urls = defaultdict(set)
    for table in FINANCIAL_TABLES & tables:
        columns = {r[1] for r in connection.execute('PRAGMA table_info(' + quote(table) + ')')}
        for column in ('source', 'category_source'):
            if column not in columns: continue
            for r in connection.execute('SELECT DISTINCT ' + quote(column) + ' FROM ' + quote(table)):
                if r[0]: financial_urls[r[0]].add(table)
    for x in items.values():
        for u in x['urls']:
            if u in financial_urls:
                x['evidence_reasons'].append('exact_financial_source_url:' + ','.join(sorted(financial_urls[u])))
    # Fail-safe protection for future hash-bearing tables and string settings.
    for table in tables - KNOWN_HASH_TABLES:
        columns = [r[1] for r in connection.execute('PRAGMA table_info(' + quote(table) + ')')]
        for col in columns:
            if 'hash' not in col.lower() and table != 'settings': continue
            for r in connection.execute('SELECT DISTINCT ' + quote(col) + ' FROM ' + quote(table)):
                for h in re.findall(r'\b[0-9a-f]{64}\b', str(r[0] or '')):
                    if h in items: attach(h, reason='database_literal_hash_dependency:' + table + '.' + col)
    for folder in ('tracker', 'scripts', 'docs'):
        base = Path(root) / folder
        if not base.exists(): continue
        for path in sorted(base.rglob('*')):
            if path.suffix not in ('.py', '.json', '.md'): continue
            # Generated inventories must not self-protect every source on reruns.
            if path.name.startswith(('STORAGE-', 'SOURCE-RETENTION', 'source-retention')): continue
            for h in set(re.findall(r'\b[0-9a-f]{64}\b', path.read_text(errors='replace'))):
                if h in items: attach(h, reason='code_or_handoff_literal_hash:' + str(path.relative_to(root)))
    page_errors = set()
    if 'source_pages' in tables:
        for r in connection.execute('SELECT url,status FROM source_pages'):
            if re.search(r'error|fail|forbid|unavailable|refused|blocked', r['status'] or '', re.I): page_errors.add(r['url'])
    for h, x in items.items():
        x['kind'] = response_kind(x.get('media_type'), x['urls'])
        superseded = True
        for u in sorted(x['urls']):
            versions = by_url[u]
            t = versions.get(h)
            if not t or not any(other != h and seen > t for other, seen in versions.items()):
                superseded = False
                x['latest_for_urls'].append(u)
            domain = host(u)
            if any(domain == d or domain.endswith('.' + d) for d in FRAGILE_HOSTS): x['fragile_urls'].append(u)
            if (latest_fetch.get(u, {}).get('status') not in (None, 'ok')) or u in page_errors: x['latest_error_urls'].append(u)
        x['superseded_for_all_urls'] = bool(x['urls']) and superseded
        x['classification'], x['reasons'] = classify(x)
        x['primary_url'] = sorted(x['urls'])[0] if x['urls'] else ''
        x['host'] = host(x['primary_url'])
        x['latest_fetch_evidence'] = [dict(url=u, fetched_at=latest_fetch[u]['fetched_at'],
                                             status=latest_fetch[u]['status'], detail=latest_fetch[u].get('detail'))
                                      for u in sorted(x['urls']) if u in latest_fetch]
        for field in ('urls', 'families', 'titles', 'reporting_dates'): x[field] = sorted(x[field])
        x['evidence_reasons'] = sorted(set(x['evidence_reasons']))
    return items, sorted(missing_hashes)


def reference_assets(manifest):
    if not manifest: return set()
    if int(manifest.get('format', 1)) < 2: return {manifest['asset']}
    return {manifest['database']['asset'], *(p['asset'] for p in manifest.get('source_packs', []))}


def measure_packs(items, manifest, assets, repo):
    """Read and checksum immutable release packs; inspect ZIP sizes, no extraction/deletion."""
    by_name = {a['name']: a for a in assets}
    seen = set()
    verified = []
    with tempfile.TemporaryDirectory(prefix='smallcap-retention-packs-') as directory:
        for pack in manifest['source_packs']:
            name = pack['asset']
            if not re.fullmatch(r'sources-[A-Za-z0-9_.-]+\.zip', name): raise ValueError('Unexpected pack name')
            asset = by_name[name]
            subprocess.run(['gh', 'release', 'download', 'tracker-history', '--repo', repo,
                            '--pattern', name, '--dir', directory], check=True, capture_output=True)
            path = Path(directory) / name
            if path.stat().st_size != pack['bytes'] or path.stat().st_size != asset['size']: raise ValueError('Pack size mismatch')
            actual = sha256(path)
            if asset.get('digest') != 'sha256:' + actual: raise ValueError('Release pack digest missing or mismatched')
            found = set()
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir(): raise ValueError('Unexpected directory member')
                    h = info.filename.rsplit('/', 1)[-1]
                    if h not in items or info.filename != 'data/' + items[h]['path']: raise ValueError('Unknown ZIP member')
                    if items[h].get('binary_state','retained')!='retained':
                        raise ValueError('Active source pack contains a metadata-only hash')
                    if h in seen or h in found or info.file_size != items[h]['bytes']: raise ValueError('Duplicate or damaged member identity')
                    found.add(h)
                    items[h]['pack'] = name
                    items[h]['compressed_payload_bytes'] = info.compress_size
                if found != set(pack['hashes']): raise ValueError('Pack hash list mismatch')
            seen.update(found)
            verified.append({'asset': name, 'bytes': path.stat().st_size, 'sha256': actual, 'members': len(found)})
            print('Verified pack', len(verified), '/', len(manifest['source_packs']), name, flush=True)
            # Remove only the disposable downloaded audit copy, never release or production files.
            path.unlink()
    expected={h for h,x in items.items() if x.get('binary_state','retained')=='retained'}
    if seen != expected: raise ValueError('Source pack inventory does not cover retained binaries')
    return verified


def summarize(items, manifest, assets, database_bytes):
    rows = list(items.values())
    groups = {}
    for state in STATES:
        selected = [x for x in rows if x['classification'] == state]
        group = {'files': len(selected), 'raw_bytes': sum(x['bytes'] for x in selected)}
        if all('compressed_payload_bytes' in x for x in rows):
            group['compressed_payload_bytes'] = sum(x['compressed_payload_bytes'] for x in selected)
        groups[state] = group
    total = sum(x['bytes'] for x in rows)
    binary_states={
        state:{
            'files':sum(x.get('binary_state','retained')==state for x in rows),
            'raw_bytes':sum(x['bytes'] for x in rows if x.get('binary_state','retained')==state),
        }
        for state in ('retained','metadata_only')
    }
    candidate = groups['link_only_candidate']['raw_bytes']
    active = reference_assets(manifest)
    previous = reference_assets(manifest.get('previous'))
    host_rows = []
    for domain in sorted({x['host'] for x in rows}):
        selected = [x for x in rows if x['host'] == domain]
        host_rows.append({'host': domain, 'files': len(selected), 'raw_bytes': sum(x['bytes'] for x in selected),
                          'candidate_files': sum(x['classification'] == 'link_only_candidate' for x in selected),
                          'candidate_raw_bytes': sum(x['bytes'] for x in selected if x['classification'] == 'link_only_candidate')})
    return {'archive_files': len(rows), 'archive_raw_bytes': total, 'database_bytes': database_bytes,
            'groups': groups, 'binary_states': binary_states, 'candidate_percent_of_raw_archive': round(100 * candidate / total, 4) if total else 0,
            'proposed_raw_archive_bytes': total - candidate,
            'proposed_database_plus_sources_bytes': database_bytes + total - candidate,
            'bytes_actually_deleted': 0, 'files_actually_deleted': 0,
            'hosts': sorted(host_rows, key=lambda x: x['candidate_raw_bytes'], reverse=True),
            'top_candidates': sorted([x for x in rows if x['classification'] == 'link_only_candidate'], key=lambda x: x['bytes'], reverse=True)[:12],
            'release': {'current_checkpoint_created_at': manifest.get('created_at'),
                        'assets': len(assets), 'total_bytes': sum(a['size'] for a in assets),
                        'active_asset_bytes': sum(a['size'] for a in assets if a['name'] in active),
                        'previous_only_bytes': sum(a['size'] for a in assets if a['name'] in previous - active),
                        'unreferenced_assets': [{'name': a['name'], 'bytes': a['size']} for a in assets
                                                if a['name'] not in active | previous | {'latest.json'}]},
            'limitations': [
                'Metadata/dependency classification, not a semantic review of every original file.',
                'No live AMC link availability checks; retained fetch history is dated evidence only.',
                'Different hashes are different saved bytes, not proven duplicates. Candidate deletion loses those historical response snapshots.',
                'A URL or SHA-256 cannot reconstruct an overwritten or unavailable document.',
                'Original PDFs/workbooks and successful historical extractions are protected, including data beyond rolling parsed portfolio retention.',
                'Compressed payload totals exclude ZIP headers; actual release reduction requires approved repacking and rollback retirement.',
                'Existing restore, replay and website download code requires retained binaries. No deletion or policy change is enabled by this report.',
                'Legacy cumulative backup, current rollback checkpoint, repository bootstrap, and published Pages copies are separate and untouched.'
            ]}


def write_reports(output, report, items):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'SOURCE-RETENTION-SUMMARY.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (output / 'SOURCE-RETENTION-INVENTORY.json').write_text(json.dumps(list(items.values()), indent=2, ensure_ascii=False) + '\n')
    fields = ['hash', 'classification', 'stored_classification', 'binary_state', 'retention_reason',
              'retention_reviewed_at', 'bytes', 'compressed_payload_bytes', 'kind', 'media_type', 'host',
              'primary_url', 'first_seen', 'families', 'reporting_dates', 'titles', 'reasons', 'references',
              'urls', 'latest_for_urls', 'latest_document_ids', 'fragile_urls', 'latest_error_urls', 'pack']
    with (output / 'SOURCE-RETENTION-INVENTORY.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); writer.writeheader()
        for x in items.values():
            record = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in x.items()}
            # CSV formula safety for future text labels opened in spreadsheet tools.
            for key, value in record.items():
                if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')): record[key] = "'" + value
            writer.writerow(record)
    groups = report['groups']
    lines = ['# Source-retention audit — proposal only', '',
             'No archived file, source-pack asset, database row, production policy, schedule or website was changed.', '',
             '| Classification | Files | Uncompressed bytes | Compressed payload bytes |',
             '| --- | ---: | ---: | ---: |']
    for state, x in groups.items():
        lines.append(f"| {state} | {x['files']:,} | {x['raw_bytes']:,} | {x.get('compressed_payload_bytes', 'not measured')} |")
    lines += ['', f"Audit time: {report['audited_at']}. Checkpoint: `{report['checkpoint']['asset']}`.", '',
              f"Potential link-only reduction: **{groups['link_only_candidate']['raw_bytes']:,} raw bytes** ({report['candidate_percent_of_raw_archive']}% of originals). **Actual deletion: 0 bytes.**", '',
              '## Decision rules', '',
              'Retain all sources tied by hash or exact source URL to financial records; successful historical extractions; dated/narrative AMC publications; literal code/handoff hash dependencies. Original PDFs, workbooks and other downloadable/unknown files remain retained or under review. Protect the latest saved version of every document, independently of later URL fetches, and every exact URL; also protect sources with documented transport boundaries or a latest recorded error.', '',
              'Only superseded HTML/JavaScript responses with a strictly newer retained version for every associated URL and no identified evidence/replay dependency become link-only candidates. JSON/plain-text responses stay under review because request parameters and data semantics are not fully recorded. These are distinct response snapshots, not verified byte duplicates. Link-only means knowingly giving up old discovery-response bytes while retaining metadata and newer responses.', '',
              '## Before any deletion', '',
              'Obtain explicit approval of the exact candidate hashes. Add explicit binary-retention state without deleting provenance metadata. Make restore, verification, reprocessing, archive serving, publication selection and download labels retention-aware. Prevent re-archiving the same discardable responses. Build replacement packs and validate all retained members, sources and the complete website before switching an atomic manifest. Keep rollback packs until independently verified. This audit does not implement those steps.', '',
              '## Important limits', '']
    lines += ['- ' + x for x in report['limitations']]
    lines += ['', '## Largest candidate hosts', '', '| Host | Candidate files | Candidate raw bytes |', '| --- | ---: | ---: |']
    for x in report['hosts'][:10]:
        if x['candidate_files']: lines.append(f"| {x['host']} | {x['candidate_files']} | {x['candidate_raw_bytes']:,} |")
    lines += ['', 'Full inventory: `SOURCE-RETENTION-INVENTORY.csv` and `.json`. Every unique hash has a classification, source URLs, reasons, reporting/publication dates where known, and measured byte counts.', '']
    (output / 'SOURCE-RETENTION-AUDIT.md').write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repo')
    p.add_argument('--measure-packs', action='store_true')
    args = p.parse_args()
    database = args.database.resolve(strict=True)
    output = args.output.resolve()
    if output == database.parent or output.is_relative_to(database.parent): raise ValueError('Output must be outside the data directory')
    if any(Path(str(database) + suffix).exists() for suffix in ('-wal', '-journal')): raise ValueError('Use a closed checkpoint copy, not a live writer database')
    before = sha256(database)
    manifest_before = sha256(args.manifest)
    manifest = json.loads(args.manifest.read_text())
    if int(manifest.get('format', 1)) != 2: raise ValueError('Split checkpoint format required')
    assets = json.loads(args.assets.read_text())
    if assets and isinstance(assets[0], list): assets = [a for page in assets for a in page]
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as c:
        c.execute('PRAGMA query_only=ON')
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Database integrity failed')
        if c.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Foreign key check failed')
        items, missing = collect(c)
        table_counts = {r[0]: c.execute('SELECT COUNT(*) FROM ' + quote(r[0])).fetchone()[0]
                        for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    packed = [h for pack in manifest['source_packs'] for h in pack['hashes']]
    expected_packed={h for h,x in items.items() if x.get('binary_state','retained')=='retained'}
    if len(packed) != len(set(packed)) or set(packed) != expected_packed:
        raise ValueError('Manifest/retained-binary hash coverage mismatch')
    if missing: raise ValueError('Unresolved nonempty source hashes: ' + str(missing[:10]))
    measured = []
    if args.measure_packs:
        if not args.repo or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo): raise ValueError('Valid repository required')
        measured = measure_packs(items, manifest, assets, args.repo)
    if sha256(database) != before or sha256(args.manifest) != manifest_before: raise ValueError('Audit input changed')
    report = summarize(items, manifest, assets, database.stat().st_size)
    report.update(audited_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  mode='read_only_proposal', checkpoint=manifest['database'],
                  database_sha256_before=before, database_sha256_after=sha256(database),
                  database_unchanged=True, input_manifest_unchanged=True,
                  table_counts=table_counts, logical_rows=sum(table_counts.values()),
                  unique_hash_coverage_verified=True, verified_packs=measured,
                  live_amc_urls_checked=0)
    write_reports(output, report, items)
    print(json.dumps({k: report[k] for k in ('archive_files', 'archive_raw_bytes', 'database_bytes', 'groups', 'database_unchanged', 'logical_rows')}, indent=2))


if __name__ == '__main__': main()
