"""Apply source-retention classifications without deleting or deactivating any bytes.

This is infrastructure preparation only. It records the reviewed audit class for
known archive hashes, leaves binary_state unchanged, validates provenance-table
stability, and proves protected hashes remain covered by the active source-pack
manifest. It never unlinks files or rewrites source packs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db
from scripts import github_state
from scripts import audit_source_retention as retention_audit

INVENTORY=ROOT/'docs'/'SOURCE-RETENTION-INVENTORY.json'
REVIEWED_AT='2026-09-25'
REASON='Classification imported from reviewed 2026-09-25 source-retention audit; binary state unchanged'
SCAN_REASON_PREFIX='Reviewed audit classification strengthened by current dependency scan: '
PRECEDENCE={'unclassified':0,'link_only_candidate':1,
            'retain_latest_or_review':2,'retain_evidence':3}


def independently_reviewed_existing(row):
    """Return a stored class only when it did not come from our audit importer."""
    if not row or row['classification']=='unclassified':
        return None
    reason=row.get('reason') or ''
    if reason==REASON or reason.startswith(SCAN_REASON_PREFIX):
        return None
    return row['classification']


def choose_classification(reviewed,current_item,existing):
    choices=[current_item['classification']]
    if reviewed:choices.append(reviewed['classification'])
    trusted=independently_reviewed_existing(existing)
    if trusted:choices.append(trusted)
    return max(choices,key=lambda x:PRECEDENCE[x])


def classification_reason(target,reviewed,current_item,existing):
    trusted=independently_reviewed_existing(existing)
    reviewed_class=reviewed['classification'] if reviewed else 'unclassified'
    if trusted==target and PRECEDENCE[trusted]>=PRECEDENCE[current_item['classification']] \
            and PRECEDENCE[trusted]>=PRECEDENCE[reviewed_class]:
        return existing.get('reason') or 'Existing independently reviewed retention state'
    if PRECEDENCE[current_item['classification']]>PRECEDENCE[reviewed_class]:
        return SCAN_REASON_PREFIX+', '.join(current_item.get('reasons') or [current_item['classification']])[:600]
    if reviewed:
        return REASON
    return 'Fresh post-audit classification from current conservative dependency scan: '+ \
           ', '.join(current_item.get('reasons') or [current_item['classification']])[:600]


def write_delta_review(path,markdown_path,candidate_path,new_hashes,current_items,before,after,archives):
    rows=[]
    for h in sorted(new_hashes):
        item=current_items[h]
        rows.append({
            'hash':h,
            'bytes':archives[h]['bytes'],
            'media_type':archives[h].get('media_type'),
            'first_seen':archives[h].get('first_seen'),
            'classification_before':before[h]['classification'],
            'classification_after':after[h]['classification'],
            'binary_state_after':after[h]['binary_state'],
            'primary_url':item.get('primary_url'),
            'host':item.get('host'),
            'kind':item.get('kind'),
            'reasons':item.get('reasons') or [],
            'evidence_reasons':item.get('evidence_reasons') or [],
            'latest_for_urls':item.get('latest_for_urls') or [],
            'urls':item.get('urls') or [],
        })
    classes=Counter(x['classification_after'] for x in rows)
    class_bytes=Counter()
    for x in rows:class_bytes[x['classification_after']]+=int(x['bytes'] or 0)
    candidates=[x for x in rows if x['classification_after']=='link_only_candidate']
    report={
        'reviewed_at':db.now(),
        'scope':'post_original_audit_hashes_only',
        'original_reviewed_inventory_hashes':len(json.loads(INVENTORY.read_text(encoding='utf-8'))),
        'new_hashes_reviewed':len(rows),
        'binary_state_policy':'all_retained',
        'files_deleted':0,
        'bytes_deleted':0,
        'classifications':dict(classes),
        'classification_bytes':dict(class_bytes),
        'new_link_only_candidates':len(candidates),
        'new_link_only_candidate_raw_bytes':sum(int(x['bytes'] or 0) for x in candidates),
        'migration_set_policy':'delta_not_merged_into_approved_695_hash_proposal',
        'rows':rows,
    }
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    candidate_payload={
        'reviewed_at':report['reviewed_at'],
        'scope':'new_hash_delta_only',
        'count':len(candidates),
        'raw_bytes':report['new_link_only_candidate_raw_bytes'],
        'production_binary_state_changes':0,
        'merged_into_existing_695_hash_proposal':False,
        'candidates':candidates,
    }
    cp=Path(candidate_path);cp.parent.mkdir(parents=True,exist_ok=True)
    cp.write_text(json.dumps(candidate_payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=[
        '# Source-retention post-audit delta review','',
        f"Reviewed **{len(rows)}** hashes added after the original audited inventory.",
        '**Every binary remains retained. Deleted files/bytes: 0 / 0.**','',
        '| Classification | Files | Raw bytes |','| --- | ---: | ---: |',
    ]
    for name in ('retain_evidence','retain_latest_or_review','link_only_candidate','unclassified'):
        lines.append(f"| {name} | {classes.get(name,0):,} | {class_bytes.get(name,0):,} |")
    lines += [
        '',
        f"New link-only candidates: **{len(candidates)} files / {report['new_link_only_candidate_raw_bytes']:,} raw bytes**.",
        'These are a separate review delta and are not merged into the existing approval-gated 695-hash migration proposal.',
        '',
        'Full per-hash review: SOURCE-RETENTION-DELTA.json.',
        'Candidate-only delta: SOURCE-RETENTION-NEW-CANDIDATES.json.',
        ''
    ]
    mp=Path(markdown_path);mp.parent.mkdir(parents=True,exist_ok=True)
    mp.write_text('\n'.join(lines),encoding='utf-8')
    return report


def digest_rows(rows):
    payload=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def table_fingerprints(exclude=('archive_retention',)):
    """Hash every logical row outside the new metadata table."""
    ignored=set(exclude)
    with db.connect() as c:
        tables=[r['name'] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall() if r['name'] not in ignored]
        out={}
        for name in tables:
            quoted='"'+name.replace('"','""')+'"'
            columns=[r['name'] for r in c.execute(f'PRAGMA table_info({quoted})').fetchall()]
            order=','.join('"'+x.replace('"','""')+'"' for x in columns)
            h=hashlib.sha256();count=0
            for row in c.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
                h.update((repr(tuple(row))+'\n').encode());count+=1
            out[name]={'rows':count,'sha256':h.hexdigest()}
        return out


def active_manifest_hashes():
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if not repo:
        return None,None
    with tempfile.TemporaryDirectory(prefix='smallcap-retention-manifest-') as tmp:
        manifest=github_state._current_release_manifest(repo,Path(tmp))
    if int(manifest.get('format',1))<2:
        return manifest,None
    packed={h for pack in manifest.get('source_packs',[]) for h in pack.get('hashes',[])}
    return manifest,packed


def prepare(*,apply=False,report_path=None,delta_path=None,delta_markdown=None,candidate_delta=None):
    db.init()
    inventory=json.loads(INVENTORY.read_text(encoding='utf-8'))
    if not isinstance(inventory,list) or not inventory:
        raise ValueError('Retention inventory is empty or invalid')
    audited={row['hash']:row for row in inventory}
    if len(audited)!=len(inventory):
        raise ValueError('Retention inventory contains duplicate hashes')
    archives={r['hash']:r for r in db.rows(
        'SELECT hash,path,bytes,media_type,first_seen FROM archives ORDER BY hash')}
    new_hashes=set(archives)-set(audited)
    missing=sorted(set(audited)-set(archives))
    if missing:
        raise ValueError('Reviewed retention hash is absent from current archive metadata: '+missing[0])
    with db.connect() as connection:
        current_items,current_missing=retention_audit.collect(connection,ROOT)
    if current_missing:
        raise ValueError('Current dependency scan found an unresolved source hash: '+current_missing[0])

    before_fingerprints=table_fingerprints()
    protected_hashes=sorted(h for h,row in audited.items() if row['classification']=='retain_evidence')
    protected_rows=[archives[h] for h in protected_hashes]
    protected_digest_before=digest_rows(protected_rows)

    stored_before={r['hash']:r for r in db.rows(
        'SELECT hash,classification,binary_state,reason,reviewed_at FROM archive_retention')}
    if apply:
        stamp=db.now()
        records=[]
        for h in sorted(archives):
            reviewed=audited.get(h)
            item=current_items[h]
            existing=stored_before[h]
            target=choose_classification(reviewed,item,existing)
            reason=classification_reason(target,reviewed,item,existing)
            reviewed_at=(reviewed.get('reviewed_at') if reviewed and reviewed.get('reviewed_at')
                         else (existing.get('reviewed_at') or REVIEWED_AT))
            records.append((target,reason,reviewed_at,stamp,h))
        with db.connect() as c:
            c.executemany("""UPDATE archive_retention SET
              classification=?,reason=?,reviewed_at=?,updated_at=?
              WHERE hash=?""",records)

    after_fingerprints=table_fingerprints()
    if before_fingerprints!=after_fingerprints:
        raise ValueError('Retention metadata preparation changed a provenance/data table')
    protected_after={r['hash']:r for r in db.rows(
        'SELECT hash,path,bytes,media_type,first_seen FROM archives ORDER BY hash')
        if r['hash'] in set(protected_hashes)}
    protected_digest_after=digest_rows([protected_after[h] for h in protected_hashes])
    if protected_digest_before!=protected_digest_after:
        raise ValueError('Protected archive metadata changed')

    retention=db.rows("""SELECT classification,binary_state,COUNT(*) files,
      COALESCE(SUM(a.bytes),0) bytes
      FROM archive_retention r JOIN archives a ON a.hash=r.hash
      GROUP BY classification,binary_state
      ORDER BY classification,binary_state""")
    invalid=db.rows("""SELECT r.hash,r.classification,r.binary_state FROM archive_retention r
      WHERE (r.binary_state='metadata_only' AND r.classification!='link_only_candidate')
         OR (r.classification='retain_evidence' AND r.binary_state!='retained')""")
    if invalid:raise ValueError('Unsafe archive retention state: '+invalid[0]['hash'])
    states=Counter()
    classes=Counter()
    stored_after={r['hash']:r for r in db.rows(
        'SELECT hash,classification,binary_state,reason,reviewed_at FROM archive_retention')}
    for row in stored_after.values():
        states[row['binary_state']]+=1;classes[row['classification']]+=1

    delta_report=None
    if delta_path or delta_markdown or candidate_delta:
        if not (delta_path and delta_markdown and candidate_delta):
            raise ValueError('All delta output paths are required together')
        delta_report=write_delta_review(
            delta_path,delta_markdown,candidate_delta,new_hashes,current_items,
            stored_before,stored_after,archives)

    manifest,packed=active_manifest_hashes()
    protected_manifest_ok=None
    candidate_manifest_ok=None
    if packed is not None:
        protected_manifest_ok=set(protected_hashes)<=packed
        if not protected_manifest_ok:raise ValueError('Active source packs do not cover all protected evidence')
        candidate_hashes={h for h,row in stored_after.items()
                          if row['classification']=='link_only_candidate'}
        candidate_manifest_ok=candidate_hashes<=packed
        if states['metadata_only']==0 and not candidate_manifest_ok:
            raise ValueError('Zero-deletion rollout lost a reviewed link-only candidate from active packs')

    try:inventory_label=str(INVENTORY.relative_to(ROOT))
    except ValueError:inventory_label=str(INVENTORY)
    report={
        'prepared_at':db.now(),
        'mode':'apply_classifications_no_binary_change' if apply else 'dry_run',
        'inventory_file':inventory_label,
        'reviewed_inventory_hashes':len(audited),
        'historical_link_only_candidates':sum(
            row['classification']=='link_only_candidate' for row in audited.values()),
        'historical_candidates_strengthened_by_current_scan':sum(
            row['classification']=='link_only_candidate'
            and choose_classification(row,current_items[h],stored_before[h])!='link_only_candidate'
            for h,row in audited.items()),
        'post_audit_hashes_reviewed':len(new_hashes),
        'post_audit_delta':({k:v for k,v in delta_report.items() if k!='rows'}
                            if delta_report else None),
        'current_dependency_scan_missing_hashes':len(current_missing),
        'current_archive_hashes':len(archives),
        'new_unclassified_hashes':classes['unclassified'],
        'retention_groups':retention,
        'binary_states':dict(states),
        'classifications':dict(classes),
        'protected_archive_metadata_sha256_before':protected_digest_before,
        'protected_archive_metadata_sha256_after':protected_digest_after,
        'protected_archive_metadata_unchanged':protected_digest_before==protected_digest_after,
        'non_retention_table_fingerprints_unchanged':before_fingerprints==after_fingerprints,
        'non_retention_table_fingerprints':after_fingerprints,
        'files_actually_deleted':0,
        'bytes_actually_deleted':0,
        'active_checkpoint_format':int(manifest.get('format',1)) if manifest else None,
        'active_checkpoint_created_at':manifest.get('created_at') if manifest else None,
        'protected_hashes_covered_by_active_source_manifest':protected_manifest_ok,
        'link_only_candidates_still_covered_by_active_source_manifest':candidate_manifest_ok,
        'deletion_enabled':False,
        'source_pack_repack_performed':False,
        'legacy_or_rollback_assets_retired':False,
        'readiness':{
            'retention_metadata_schema_ready':True,
            'archive_serving_retention_aware':True,
            'selective_materialization_retention_aware':True,
            'replay_retention_aware':True,
            'source_pack_planning_retention_aware':True,
            'publication_selection_retention_aware':True,
            'approved_for_binary_deletion':False,
        },
    }
    if report_path:
        path=Path(report_path);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    p.add_argument('--report',type=Path)
    p.add_argument('--delta-report',type=Path)
    p.add_argument('--delta-markdown',type=Path)
    p.add_argument('--candidate-delta',type=Path)
    args=p.parse_args()
    prepare(apply=args.apply,report_path=args.report,
            delta_path=args.delta_report,delta_markdown=args.delta_markdown,
            candidate_delta=args.candidate_delta)
