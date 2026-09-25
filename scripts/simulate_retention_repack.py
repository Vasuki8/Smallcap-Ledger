"""Isolated source-pack reduction simulation.

This script never changes the live archive_retention state, uploads release
assets, deletes release assets, switches latest.json, or deletes source files.
It copies the live SQLite checkpoint, marks the reviewed link-only candidates
metadata-only only in that copy, rebuilds only affected source packs in a
temporary workspace, and validates the proposed active set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db
from scripts import github_state

INVENTORY=ROOT/'docs'/'SOURCE-RETENTION-INVENTORY.json'
QUEUE=ROOT/'docs'/'PORTFOLIO-RECOVERY-QUEUE.json'


def sha256(path):
    return github_state.digest(path)


def json_sha(value):
    payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def load_candidates():
    rows=json.loads(INVENTORY.read_text(encoding='utf-8'))
    candidates=[r for r in rows if r.get('classification')=='link_only_candidate']
    if len(candidates)!=700:
        raise ValueError(f'Expected exactly 700 reviewed candidates, found {len(candidates)}')
    if len({r['hash'] for r in candidates})!=len(candidates):
        raise ValueError('Candidate inventory contains duplicate hashes')
    return candidates


def ensure_no_actionable_portfolio_change():
    queue=json.loads(QUEUE.read_text(encoding='utf-8'))
    summary=queue.get('summary') or {}
    changed=[x['family'] for x in queue.get('items',[])
             if (x.get('source_change_watch') or {}).get('changed')]
    if summary.get('actionable_now') or summary.get('source_changes_detected') or changed:
        raise ValueError('Portfolio source-change watch became actionable; storage simulation must pause')
    return summary


def backup_database(target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with db.connect() as source,sqlite3.connect(target) as dest:
        source.backup(dest)
    return target


def db_fingerprints(path,exclude=('archive_retention',)):
    with sqlite3.connect(path) as c:
        c.row_factory=sqlite3.Row
        ignored=set(exclude)
        names=[r['name'] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall() if r['name'] not in ignored]
        result={}
        for name in names:
            quoted='"'+name.replace('"','""')+'"'
            cols=[r['name'] for r in c.execute(f'PRAGMA table_info({quoted})').fetchall()]
            order=','.join('"'+x.replace('"','""')+'"' for x in cols)
            h=hashlib.sha256();count=0
            for row in c.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
                h.update((repr(tuple(row))+'\n').encode());count+=1
            result[name]={'rows':count,'sha256':h.hexdigest()}
        return result


def simulate_database(target,candidate_hashes):
    backup_database(target)
    before=db_fingerprints(target)
    marks=','.join('?' for _ in candidate_hashes)
    with sqlite3.connect(target) as c:
        c.row_factory=sqlite3.Row
        states={r['hash']:dict(r) for r in c.execute(
            f'''SELECT hash,classification,binary_state FROM archive_retention
                WHERE hash IN ({marks})''',tuple(candidate_hashes))}
        if set(states)!=set(candidate_hashes):
            raise ValueError('Simulation database does not contain every reviewed candidate')
        bad=[h for h,r in states.items()
             if r['classification']!='link_only_candidate' or r['binary_state']!='retained']
        if bad:
            raise ValueError('Reviewed candidate is no longer an eligible retained link-only candidate: '+bad[0])
        stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
        c.execute('BEGIN IMMEDIATE')
        c.execute(f'''UPDATE archive_retention SET binary_state='metadata_only',
                      reason='SIMULATION ONLY - proposed replacement-pack migration',
                      updated_at=? WHERE hash IN ({marks})''',(stamp,*candidate_hashes))
        changed=c.execute("SELECT COUNT(*) FROM archive_retention WHERE binary_state='metadata_only'").fetchone()[0]
        if changed!=len(candidate_hashes):
            raise ValueError('Simulation changed an unexpected number of binary states')
        protected=c.execute("""SELECT COUNT(*) FROM archive_retention
          WHERE classification='retain_evidence' AND binary_state!='retained'""").fetchone()[0]
        if protected:
            raise ValueError('Simulation changed protected evidence binary state')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Simulated database integrity failed')
        c.commit()
    after=db_fingerprints(target)
    if before!=after:
        raise ValueError('Simulation changed non-retention database content')
    return before


def zip_database(database,target):
    database=Path(database);target=Path(target)
    with sqlite3.connect(database) as c:c.execute('VACUUM')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(database,'data/ledger.sqlite3')
    return {'asset':'SIMULATED-DATABASE-NOT-UPLOADED.zip',
            'bytes':target.stat().st_size,'sha256':sha256(target)}


def release_assets(repo):
    release=github_state.release(repo)
    if not release:raise ValueError('tracker-history release is missing')
    return release,{a['name']:a for a in release.get('assets',[])}


def copy_zipinfo(info):
    clone=zipfile.ZipInfo(info.filename,info.date_time)
    clone.compress_type=zipfile.ZIP_DEFLATED
    clone.comment=info.comment;clone.extra=info.extra
    clone.create_system=info.create_system;clone.create_version=info.create_version
    clone.extract_version=info.extract_version;clone.flag_bits=info.flag_bits
    clone.volume=info.volume;clone.internal_attr=info.internal_attr
    clone.external_attr=info.external_attr
    return clone


def repack_filtered(source,target,pack,rows,candidates):
    """Create a local replacement ZIP and verify every old/reused member."""
    source=Path(source);target=Path(target)
    expected_old=set(pack['hashes'])
    retained=[h for h in pack['hashes'] if h not in candidates]
    removed=[h for h in pack['hashes'] if h in candidates]
    found=set()
    if retained:
        with zipfile.ZipFile(source) as zin,zipfile.ZipFile(
                target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            infos={i.filename:i for i in zin.infolist() if not i.is_dir()}
            for h in pack['hashes']:
                row=rows[h];member='data/'+row['path']
                info=infos.get(member)
                if not info:raise ValueError('Active source pack is missing '+h)
                if info.file_size!=row['bytes']:raise ValueError('Active source pack member size mismatch')
                body=zin.read(info)
                if hashlib.sha256(body).hexdigest()!=h:raise ValueError('Active source pack member checksum mismatch')
                found.add(h)
                if h in candidates:continue
                zout.writestr(copy_zipinfo(info),body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
        if found!=expected_old:raise ValueError('Active source pack membership mismatch')
        plan={'members':[rows[h] for h in retained]}
        github_state.verify_source_pack_zip(target,plan)
    else:
        with zipfile.ZipFile(source) as zin:
            infos={i.filename:i for i in zin.infolist() if not i.is_dir()}
            for h in pack['hashes']:
                row=rows[h];member='data/'+row['path']
                info=infos.get(member)
                if not info:raise ValueError('Active source pack is missing '+h)
                body=zin.read(info)
                if info.file_size!=row['bytes'] or hashlib.sha256(body).hexdigest()!=h:
                    raise ValueError('Active source pack member verification failed')
                found.add(h)
        if found!=expected_old:raise ValueError('Active source pack membership mismatch')
    return retained,removed


def proposed_pack_name(old_name,retained):
    stem=old_name[:-4] if old_name.endswith('.zip') else old_name
    fingerprint=hashlib.sha256(('\n'.join(retained)).encode()).hexdigest()[:16]
    return f'{stem}-replacement-{fingerprint}.zip'


def materialization_checks(sim_data,replacement_examples,candidate_hashes):
    previous=db.DATA;db.DATA=sim_data
    try:
        sample_candidate=next(iter(sorted(candidate_hashes)))
        try:
            github_state.materialize_hashes([sample_candidate])
        except ValueError as exc:
            if 'metadata-only' not in str(exc):
                raise
            candidate_blocked=True
        else:
            raise ValueError('Metadata-only candidate was materialized unexpectedly')

        retained_checked=None
        for pack_path,retained in replacement_examples:
            if not retained:continue
            h=retained[0]
            written=github_state._extract_source_hashes(pack_path,[h],sim_data)
            path=db.archive_binary_path(h)
            if written not in (0,1) or not path or sha256(path)!=h:
                raise ValueError('Retained replacement-pack member could not be selectively restored')
            retained_checked=h
            path.unlink(missing_ok=True)
            break
        if not retained_checked:
            raise ValueError('No retained replacement-pack member was available for materialization validation')
        return {'metadata_only_candidate_blocked':candidate_blocked,
                'retained_replacement_hash_materialized':retained_checked}
    finally:
        db.DATA=previous


def replay_checks(sim_data,candidate_hashes):
    previous=db.DATA;db.DATA=sim_data
    try:
        from tracker import amc_reports
        from tracker.providers import classify
        from tracker.publications import exclusion_reason
        amc_reports.init()
        rows=db.rows('''SELECT DISTINCT d.family,d.url,v.hash,a.path FROM documents d
          JOIN document_versions v ON v.document_id=d.id JOIN archives a ON a.hash=v.hash
          LEFT JOIN archive_retention r ON r.hash=a.hash
          LEFT JOIN document_extractions e ON e.family=d.family AND e.hash=v.hash AND e.parser_version=?
          WHERE d.origin='AMC' AND e.hash IS NULL
            AND COALESCE(r.binary_state,'retained')='retained'
          ORDER BY d.last_seen DESC''',(amc_reports.PARSER_VERSION,))
        eligible=[]
        for row in rows:
            if not amc_reports.parser_upgrade_applies(row['family']):continue
            if exclusion_reason(row['family'],row['url']):continue
            if classify('',row['url']) not in ('factsheet','portfolio','scheme document'):continue
            if not amc_reports.should_reprocess_existing(row['family'],row['url'],row['hash']):continue
            eligible.append(row)
        if set(r['hash'] for r in eligible)&set(candidate_hashes):
            raise ValueError('Metadata-only candidate entered replay eligibility')
        hashes=sorted({r['hash'] for r in eligible})
        if hashes:github_state.materialize_hashes(hashes)
        checked,gaps=amc_reports.reprocess_archived()
        if gaps:raise ValueError('Simulated AMC replay has gaps: '+str(gaps[:3]))
        return {'eligible_retained_hashes':len(hashes),'reprocessed':checked,'gaps':0}
    finally:
        db.DATA=previous


def document_checks(sim_data,candidate_hashes):
    previous=db.DATA;db.DATA=sim_data
    try:
        from fastapi.testclient import TestClient
        from tracker.app import app
        client=TestClient(app)
        sample=next(iter(sorted(candidate_hashes)))
        r=client.get('/api/archive/'+sample)
        if r.status_code!=404 or 'not retained' not in r.json().get('detail',''):
            raise ValueError('Metadata-only archive endpoint did not return the expected unavailable state')
        marks=','.join('?' for _ in candidate_hashes)
        row=db.one(f'''SELECT d.family,v.hash FROM document_versions v
          JOIN documents d ON d.id=v.document_id
          WHERE v.hash IN ({marks}) LIMIT 1''',tuple(candidate_hashes))
        hidden=None
        if row:
            scheme=db.one('SELECT code FROM schemes WHERE family=? ORDER BY code LIMIT 1',(row['family'],))
            if scheme:
                docs=client.get(f"/api/funds/{scheme['code']}/documents").json()
                visible={v['hash'] for d in docs for v in d.get('versions',[])}
                if row['hash'] in visible:
                    raise ValueError('Metadata-only document version remains exposed as a saved copy')
                hidden=row['hash']
        return {'archive_endpoint_blocked':True,'metadata_only_document_version_hidden':hidden}
    finally:
        db.DATA=previous


def site_checks(sim_data,root,repo,candidate_hashes):
    site=root/'simulated-site'
    env=os.environ.copy()
    env['SMALLCAP_DATA_DIR']=str(sim_data)
    env['SMALLCAP_NO_SCHEDULER']='1'
    env['GITHUB_REPOSITORY']=repo
    subprocess.run([sys.executable,str(ROOT/'scripts'/'export_site.py'),'--output',str(site),
                    '--repository',repo],cwd=ROOT,env=env,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts'/'validate_site.py'),str(site)],
                   cwd=ROOT,env=env,check=True)
    downloads=json.loads((site/'data'/'downloads.json').read_text())
    exposed={key.rsplit('/',1)[-1] for key in downloads if key.startswith('/api/archive/')}
    bad=exposed&set(candidate_hashes)
    if bad:raise ValueError('Simulated static site publishes a metadata-only candidate')
    return {'site_bytes':sum(p.stat().st_size for p in site.rglob('*') if p.is_file()),
            'saved_archive_downloads':len(exposed),
            'metadata_only_candidates_published':0}


def markdown(report):
    s=report['savings'];v=report['validation']
    return '\n'.join([
        '# Retention replacement-pack simulation - no production mutation','',
        f"Simulation time: **{report['simulated_at']}**.",
        f"Active checkpoint: **{report['active_manifest_created_at']}**.",
        '',
        '**No release asset was uploaded, deleted or switched. No production binary state changed.**','',
        '## Proposed steady-state reduction','',
        f"- reviewed candidates simulated metadata-only: **{report['candidate_count']}**",
        f"- candidate raw source bytes: **{s['candidate_raw_bytes']:,}**",
        f"- candidate compressed payload bytes from reviewed pack audit: **{s['candidate_compressed_payload_bytes']:,}**",
        f"- affected active source packs: **{report['affected_pack_count']}**",
        f"- proposed replacement packs: **{report['replacement_pack_count']}**",
        f"- source-pack asset bytes now: **{s['current_source_pack_asset_bytes']:,}**",
        f"- proposed source-pack asset bytes: **{s['proposed_source_pack_asset_bytes']:,}**",
        f"- exact proposed source-pack asset savings: **{s['source_pack_asset_savings_bytes']:,}**",
        f"- current active database ZIP: **{s['current_database_asset_bytes']:,}**",
        f"- simulated database ZIP: **{s['proposed_database_asset_bytes']:,}**",
        f"- exact proposed active-set savings including database ZIP change: **{s['active_set_savings_bytes']:,}**",
        '',
        '## Migration safety','',
        f"- non-retention database fingerprints unchanged: **{v['non_retention_fingerprints_unchanged']}**",
        f"- proposed pack membership exact: **{v['proposed_manifest_exact_coverage']}**",
        f"- protected evidence retained: **{v['protected_evidence_retained']}**",
        f"- metadata-only selective materialization blocked: **{v['materialization']['metadata_only_candidate_blocked']}**",
        f"- AMC replay gaps: **{v['replay']['gaps']}**",
        f"- metadata-only archive endpoint blocked: **{v['documents']['archive_endpoint_blocked']}**",
        f"- metadata-only candidates published on simulated site: **{v['site']['metadata_only_candidates_published']}**",
        '',
        '## Rollback and authorization boundary','',
        f"- current active source packs preserved as rollback: **{report['rollback']['active_source_packs_preserved']}**",
        f"- current active manifest switched: **{report['production_mutations']['active_manifest_switched']}**",
        f"- release uploads: **{report['production_mutations']['release_uploads']}**",
        f"- release deletions: **{report['production_mutations']['release_deletions']}**",
        f"- production binary-state changes: **{report['production_mutations']['production_binary_state_changes']}**",
        '',
        'Exact proposed manifest: RETENTION-PROPOSED-MANIFEST.json.',
        'Exact candidate list: RETENTION-MIGRATION-CANDIDATES.json.',
        '',
    ])


def simulate(report_path,manifest_path,candidates_path,markdown_path):
    queue_summary=ensure_no_actionable_portfolio_change()
    candidates=load_candidates();candidate_hashes={r['hash'] for r in candidates}
    reviewed_payload=sum(int(r.get('compressed_payload_bytes') or 0) for r in candidates)
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('GITHUB_REPOSITORY is required for the simulation')
    release,assets=release_assets(repo)

    with tempfile.TemporaryDirectory(prefix='smallcap-retention-simulation-') as tmp:
        root=Path(tmp);manifest=github_state._current_release_manifest(repo,root)
        if int(manifest.get('format',1))!=2:raise ValueError('Split checkpoint format required')
        active_packs=manifest.get('source_packs',[])
        pack_for_hash={}
        for pack in active_packs:
            for h in pack.get('hashes',[]):
                if h in pack_for_hash:raise ValueError('Active manifest contains duplicate source hash')
                pack_for_hash[h]=pack
        live_rows={r['hash']:r for r in db.rows(
            'SELECT hash,path,bytes,first_seen FROM archives ORDER BY hash')}
        if set(pack_for_hash)!=set(live_rows):
            raise ValueError('Active source-pack manifest does not cover the current database exactly')
        if not candidate_hashes<=set(live_rows):
            raise ValueError('Candidate hash missing from current database')

        sim_data=root/'sim-data';sim_data.mkdir()
        sim_db=sim_data/'ledger.sqlite3'
        before=simulate_database(sim_db,sorted(candidate_hashes))
        after=db_fingerprints(sim_db)
        if before!=after:raise ValueError('Isolated simulation changed provenance/data content')
        retained_hashes=set(live_rows)-candidate_hashes

        proposed_packs=[];replacement_examples=[];affected=[];retired=[]
        current_pack_bytes=0;proposed_pack_bytes=0
        for pack in active_packs:
            name=pack['asset'];asset=assets.get(name)
            if not asset:raise ValueError('Active source-pack asset is missing: '+name)
            old_bytes=int(pack.get('bytes') or asset['size'])
            if old_bytes!=asset['size']:raise ValueError('Active source-pack asset size mismatch')
            if not asset.get('digest','').startswith('sha256:'):
                raise ValueError('Active source-pack asset is missing a release digest')
            current_pack_bytes+=old_bytes
            removed=sorted(set(pack['hashes'])&candidate_hashes)
            if not removed:
                proposed_packs.append({**pack,'reuse':True,'release_digest':asset['digest']})
                proposed_pack_bytes+=old_bytes
                continue
            affected.append(name)
            old=github_state.download_asset(repo,name,root)
            if old.stat().st_size!=old_bytes:raise ValueError('Downloaded active pack size mismatch')
            if 'sha256:'+sha256(old)!=asset['digest']:raise ValueError('Downloaded active pack digest mismatch')
            retained=[h for h in pack['hashes'] if h not in candidate_hashes]
            removed_ordered=[h for h in pack['hashes'] if h in candidate_hashes]
            if retained:
                new_name=proposed_pack_name(name,retained);new_path=root/new_name
                retained2,removed2=repack_filtered(old,new_path,pack,live_rows,candidate_hashes)
                if retained2!=retained or removed2!=removed_ordered:
                    raise ValueError('Replacement pack filter was not deterministic')
                new_bytes=new_path.stat().st_size
                replacement={
                    'asset':new_name,'simulated':True,'replaces':name,
                    'bytes':new_bytes,'sha256':sha256(new_path),
                    'raw_bytes':sum(int(live_rows[h]['bytes']) for h in retained),
                    'members':len(retained),'hashes':retained,
                    'removed_hashes':removed_ordered,
                    'removed_raw_bytes':sum(int(live_rows[h]['bytes']) for h in removed_ordered),
                    'old_asset_bytes':old_bytes,
                    'steady_state_asset_savings_bytes':old_bytes-new_bytes,
                }
                proposed_packs.append(replacement);proposed_pack_bytes+=new_bytes
                replacement_examples.append((new_path,retained))
            else:
                retired.append(name)
            old.unlink()

        proposed_coverage=[h for p in proposed_packs for h in p.get('hashes',[])]
        if len(proposed_coverage)!=len(set(proposed_coverage)) or set(proposed_coverage)!=retained_hashes:
            raise ValueError('Proposed manifest does not cover retained hashes exactly')

        protected={r['hash'] for r in db.rows(
            "SELECT hash FROM archive_retention WHERE classification='retain_evidence'")}
        if not protected<=retained_hashes:
            raise ValueError('Proposed migration would remove protected evidence')

        db_zip=root/'simulated-database.zip'
        proposed_database=zip_database(sim_db,db_zip)
        current_db_asset=assets.get(manifest['database']['asset'])
        if not current_db_asset:raise ValueError('Active database asset is missing')
        current_database_bytes=int(manifest['database'].get('bytes') or current_db_asset['size'])
        if current_database_bytes!=current_db_asset['size']:
            raise ValueError('Active database asset size mismatch')

        previous_data=db.DATA;db.DATA=sim_data
        try:
            materialization=materialization_checks(sim_data,replacement_examples,candidate_hashes)
            replay=replay_checks(sim_data,candidate_hashes)
            documents=document_checks(sim_data,candidate_hashes)
        finally:
            db.DATA=previous_data
        site=site_checks(sim_data,root,repo,candidate_hashes)

        candidate_output={
            'simulated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'classification':'link_only_candidate',
            'proposed_binary_state':'metadata_only',
            'count':len(candidates),
            'raw_bytes':sum(int(live_rows[h]['bytes']) for h in candidate_hashes),
            'candidates':[
                {
                    'hash':r['hash'],'bytes':int(live_rows[r['hash']]['bytes']),
                    'current_pack':pack_for_hash[r['hash']]['asset'],
                    'host':r.get('host'),'primary_url':r.get('primary_url'),
                    'kind':r.get('kind'),'classification':r.get('classification'),
                }
                for r in sorted(candidates,key=lambda x:x['hash'])
            ],
        }

        proposed_manifest={
            'simulation_only':True,
            'format':2,
            'based_on_active_manifest_created_at':manifest.get('created_at'),
            'based_on_database_asset':manifest['database']['asset'],
            'database':proposed_database,
            'source_packs':proposed_packs,
            'source_pack_raw_limit':manifest.get('source_pack_raw_limit'),
            'candidate_count':len(candidate_hashes),
            'candidate_hashes_sha256':json_sha(sorted(candidate_hashes)),
            'retained_hash_count':len(retained_hashes),
            'rollback':{
                'active_manifest':github_state._checkpoint_summary(manifest),
                'active_source_pack_assets':[p['asset'] for p in active_packs],
            },
            'production_mutations_authorized':False,
        }

        current_active=current_database_bytes+current_pack_bytes
        proposed_active=proposed_database['bytes']+proposed_pack_bytes
        report={
            'simulated_at':candidate_output['simulated_at'],
            'mode':'isolated_replacement_pack_simulation',
            'repository':repo,
            'queue_summary':queue_summary,
            'active_manifest_created_at':manifest.get('created_at'),
            'active_database_asset':manifest['database']['asset'],
            'current_archive_hashes':len(live_rows),
            'candidate_count':len(candidate_hashes),
            'retained_hash_count':len(retained_hashes),
            'affected_pack_count':len(affected),
            'replacement_pack_count':sum(not p.get('reuse',False) for p in proposed_packs),
            'fully_retired_pack_count':len(retired),
            'affected_active_packs':affected,
            'fully_retired_active_packs':retired,
            'savings':{
                'candidate_raw_bytes':candidate_output['raw_bytes'],
                'candidate_compressed_payload_bytes':reviewed_payload,
                'current_source_pack_asset_bytes':current_pack_bytes,
                'proposed_source_pack_asset_bytes':proposed_pack_bytes,
                'source_pack_asset_savings_bytes':current_pack_bytes-proposed_pack_bytes,
                'current_database_asset_bytes':current_database_bytes,
                'proposed_database_asset_bytes':proposed_database['bytes'],
                'current_active_set_bytes':current_active,
                'proposed_active_set_bytes':proposed_active,
                'active_set_savings_bytes':current_active-proposed_active,
                'replacement_assets_to_upload_bytes_before_any_retirement':
                    sum(p['bytes'] for p in proposed_packs if not p.get('reuse',False))+proposed_database['bytes'],
                'release_bytes_reclaimed_before_retirement':0,
            },
            'validation':{
                'non_retention_fingerprints_unchanged':before==after,
                'proposed_manifest_exact_coverage':set(proposed_coverage)==retained_hashes,
                'proposed_manifest_duplicate_hashes':len(proposed_coverage)-len(set(proposed_coverage)),
                'protected_evidence_retained':protected<=retained_hashes,
                'protected_evidence_count':len(protected),
                'materialization':materialization,
                'replay':replay,
                'documents':documents,
                'site':site,
            },
            'rollback':{
                'active_manifest_preserved':True,
                'active_source_packs_preserved':len(active_packs),
                'active_database_asset_preserved':True,
            },
            'production_mutations':{
                'release_uploads':0,'release_deletions':0,'active_manifest_switched':False,
                'production_binary_state_changes':0,'production_source_files_deleted':0,
                'legacy_zip_retired':False,
            },
            'next_action_requires_explicit_approval':True,
        }

        for path,value in ((Path(report_path),report),(Path(manifest_path),proposed_manifest),
                           (Path(candidates_path),candidate_output)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        md=Path(markdown_path);md.parent.mkdir(parents=True,exist_ok=True);md.write_text(markdown(report),encoding='utf-8')
        print(json.dumps(report,indent=2))
        return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--report',type=Path,default=ROOT/'deployment'/'retention-pack-simulation.json')
    p.add_argument('--manifest',type=Path,default=ROOT/'docs'/'RETENTION-PROPOSED-MANIFEST.json')
    p.add_argument('--candidates',type=Path,default=ROOT/'docs'/'RETENTION-MIGRATION-CANDIDATES.json')
    p.add_argument('--markdown',type=Path,default=ROOT/'docs'/'RETENTION-REPLACEMENT-SIMULATION.md')
    a=p.parse_args()
    simulate(a.report,a.manifest,a.candidates,a.markdown)
