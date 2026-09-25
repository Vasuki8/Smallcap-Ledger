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

INVENTORY=ROOT/'docs'/'SOURCE-RETENTION-INVENTORY.json'
REVIEWED_AT='2026-09-25'
REASON='Classification imported from reviewed 2026-09-25 source-retention audit; binary state unchanged'


def digest_rows(rows):
    payload=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def table_counts(exclude=('archive_retention',)):
    ignored=set(exclude)
    tables=[r['name'] for r in db.rows(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ) if r['name'] not in ignored]
    return {name:db.one(f'SELECT COUNT(*) n FROM "{name}"')['n'] for name in tables}


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


def prepare(*,apply=False,report_path=None):
    db.init()
    inventory=json.loads(INVENTORY.read_text(encoding='utf-8'))
    if not isinstance(inventory,list) or not inventory:
        raise ValueError('Retention inventory is empty or invalid')
    audited={row['hash']:row for row in inventory}
    if len(audited)!=len(inventory):
        raise ValueError('Retention inventory contains duplicate hashes')
    archives={r['hash']:r for r in db.rows(
        'SELECT hash,path,bytes,media_type,first_seen FROM archives ORDER BY hash')}
    missing=sorted(set(audited)-set(archives))
    if missing:
        raise ValueError('Reviewed retention hash is absent from current archive metadata: '+missing[0])

    before_counts=table_counts()
    protected_hashes=sorted(h for h,row in audited.items() if row['classification']=='retain_evidence')
    protected_rows=[archives[h] for h in protected_hashes]
    protected_digest_before=digest_rows(protected_rows)

    if apply:
        stamp=db.now()
        precedence={'unclassified':0,'link_only_candidate':1,
                    'retain_latest_or_review':2,'retain_evidence':3}
        current={r['hash']:r for r in db.rows(
            'SELECT hash,classification,binary_state FROM archive_retention')}
        records=[]
        for h,row in audited.items():
            reviewed=row['classification']
            if reviewed not in db.RETENTION_CLASSIFICATIONS-{'unclassified'}:
                raise ValueError('Invalid reviewed classification for '+h)
            existing=current[h]['classification']
            # Historical audit metadata may strengthen an unclassified row, but
            # must never downgrade a hash promoted by a newer current fetch.
            classification=reviewed if precedence[reviewed]>precedence[existing] else existing
            records.append((classification,REASON,REVIEWED_AT,stamp,h))
        with db.connect() as c:
            c.executemany("""UPDATE archive_retention SET
              classification=?,reason=?,reviewed_at=?,updated_at=?
              WHERE hash=?""",records)

    after_counts=table_counts()
    if before_counts!=after_counts:
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
    for row in db.rows('SELECT classification,binary_state FROM archive_retention'):
        states[row['binary_state']]+=1;classes[row['classification']]+=1

    manifest,packed=active_manifest_hashes()
    protected_manifest_ok=None
    candidate_manifest_ok=None
    if packed is not None:
        protected_manifest_ok=set(protected_hashes)<=packed
        if not protected_manifest_ok:raise ValueError('Active source packs do not cover all protected evidence')
        candidate_hashes={h for h,row in audited.items() if row['classification']=='link_only_candidate'}
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
        'current_archive_hashes':len(archives),
        'new_unclassified_hashes':classes['unclassified'],
        'retention_groups':retention,
        'binary_states':dict(states),
        'classifications':dict(classes),
        'protected_archive_metadata_sha256_before':protected_digest_before,
        'protected_archive_metadata_sha256_after':protected_digest_after,
        'protected_archive_metadata_unchanged':protected_digest_before==protected_digest_after,
        'non_retention_table_counts_unchanged':before_counts==after_counts,
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
    args=p.parse_args()
    prepare(apply=args.apply,report_path=args.report)
