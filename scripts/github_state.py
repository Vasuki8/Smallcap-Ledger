"""Durable, verified history for a stateless GitHub Actions runner.

Release format 2 separates the changing SQLite database from reusable source-file
packs. Restore remains backward compatible with the original cumulative ZIP.
The latest pointer is switched only after every required asset is uploaded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db

TAG='tracker-history'
MAX_ZIP=1800*1024*1024
MAX_EXPANDED=6*1024**3
SOURCE_PACK_RAW_LIMIT=128*1024*1024
FORMAT=2


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def _database_snapshot(path):
    path=Path(path)
    with db.connect() as source,sqlite3.connect(path) as dest:source.backup(dest)
    # Compact only the disposable checkpoint copy. This reclaims free SQLite
    # pages without mutating the live cumulative database or deleting records.
    with sqlite3.connect(path) as compact:compact.execute('VACUUM')


def _has_retention_table(connection=None):
    if connection is not None:
        return bool(connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_retention'"
        ).fetchone())
    return bool(db.one(
        "SELECT 1 ok FROM sqlite_master WHERE type='table' AND name='archive_retention'"
    ))


def retained_archive_rows(order_by='hash'):
    """Return only hashes whose binary is logically retained; old DBs mean all."""
    ordering={'hash':('hash','a.hash'),
              'first_seen,hash':('first_seen,hash','a.first_seen,a.hash')}
    if order_by not in ordering:raise ValueError('Unsafe archive ordering')
    legacy_order,joined_order=ordering[order_by]
    if not _has_retention_table():
        return db.rows(f'SELECT hash,path,bytes,first_seen FROM archives ORDER BY {legacy_order}')
    return db.rows(f'''SELECT a.hash,a.path,a.bytes,a.first_seen
      FROM archives a LEFT JOIN archive_retention r ON r.hash=a.hash
      WHERE COALESCE(r.binary_state,'retained')='retained'
      ORDER BY {joined_order}''')


def pack_database(target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/'ledger.sqlite3';_database_snapshot(snapshot)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(snapshot,'data/ledger.sqlite3')
    if target.stat().st_size>MAX_ZIP:raise ValueError('Database checkpoint approaches the GitHub release asset size limit')
    return {'asset':target.name,'sha256':digest(target),'bytes':target.stat().st_size}


def _archive_bucket(first_seen):
    match=re.match(r'^(\d{4}-\d{2})',str(first_seen or ''))
    return match.group(1) if match else 'undated'


def source_pack_plan(rows,raw_limit=SOURCE_PACK_RAW_LIMIT):
    """Return deterministic append-stable source packs grouped by first-seen month."""
    if raw_limit<=0:raise ValueError('Source pack limit must be positive')
    groups={}
    for row in rows:
        item=dict(row);item['bytes']=int(item['bytes'])
        if item['bytes']<0:raise ValueError('Archive byte count cannot be negative')
        groups.setdefault(_archive_bucket(item.get('first_seen')),[]).append(item)
    plans=[]
    for bucket in sorted(groups):
        ordered=sorted(groups[bucket],key=lambda x:(x.get('first_seen') or '',x['hash']))
        parts=[];current=[];size=0
        for item in ordered:
            if current and size+item['bytes']>raw_limit:
                parts.append(current);current=[];size=0
            current.append(item);size+=item['bytes']
        if current:parts.append(current)
        for number,members in enumerate(parts,1):
            identity='\n'.join(f"{m['hash']}:{m['bytes']}:{m['path']}" for m in members)
            fingerprint=hashlib.sha256(identity.encode()).hexdigest()[:16]
            plans.append({'asset':f'sources-{bucket}-p{number:03d}-{fingerprint}.zip',
                          'bucket':bucket,'part':number,
                          'raw_bytes':sum(m['bytes'] for m in members),
                          'members':members})
    return plans


def pack_source_pack(target,plan):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for row in plan['members']:
            p=(db.DATA/row['path']).resolve()
            if not p.is_relative_to(db.DATA.resolve()) or not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['hash']:
                raise ValueError('Missing or damaged original '+row['hash'])
            z.write(p,'data/'+row['path'])
    if target.stat().st_size>MAX_ZIP:raise ValueError('Source pack approaches the GitHub release asset size limit')
    return {'asset':target.name,'bucket':plan['bucket'],'part':plan['part'],
            'raw_bytes':plan['raw_bytes'],'members':len(plan['members']),
            'hashes':[row['hash'] for row in plan['members']],
            'bytes':target.stat().st_size}



def verify_source_pack_zip(archive,plan):
    """Verify an already-uploaded immutable source pack before reusing it."""
    archive=Path(archive)
    expected={'data/'+row['path']:row for row in plan['members']}
    with zipfile.ZipFile(archive) as z:
        infos=[i for i in z.infolist() if not i.is_dir()]
        if set(i.filename for i in infos)!=set(expected):
            raise ValueError('Source pack contents do not match expected archive members')
        for info in infos:
            _validate_zip_member(info,'data/archive/')
            row=expected[info.filename]
            if info.file_size!=row['bytes']:raise ValueError('Source pack member size mismatch')
            h=hashlib.sha256()
            with z.open(info) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=row['hash']:raise ValueError('Source pack member checksum failed: '+row['hash'])
    return True

def verify_database(folder):
    folder=Path(folder)
    with sqlite3.connect(f'file:{(folder/"ledger.sqlite3").as_posix()}?mode=ro',uri=True) as c:
        if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Archive database is damaged')
        if not c.execute('SELECT COUNT(*) FROM schemes').fetchone()[0]:raise ValueError('Archive contains no schemes')
        if not c.execute('SELECT COUNT(*) FROM nav').fetchone()[0]:raise ValueError('Archive contains no NAV history')
        c.execute('SELECT COUNT(*) FROM archives').fetchone()


def verify_data(folder):
    folder=Path(folder);verify_database(folder)
    with sqlite3.connect(f'file:{(folder/"ledger.sqlite3").as_posix()}?mode=ro',uri=True) as c:
        has_retention=_has_retention_table(c)
        query=('''SELECT a.hash,a.path,a.bytes FROM archives a
          LEFT JOIN archive_retention r ON r.hash=a.hash
          WHERE COALESCE(r.binary_state,'retained')='retained' '''
          if has_retention else 'SELECT hash,path,bytes FROM archives')
        for h,path,size in c.execute(query):
            p=(folder/path).resolve()
            if not p.is_relative_to(folder.resolve()) or not p.is_file():raise ValueError('Missing retained archive file '+h)
            if p.stat().st_size!=size or digest(p)!=h:raise ValueError('Source-file checksum failed: '+h)
        if has_retention:
            bad=c.execute("""SELECT COUNT(*) FROM archive_retention
              WHERE binary_state NOT IN ('retained','metadata_only')
                 OR classification NOT IN ('unclassified','retain_evidence','retain_latest_or_review','link_only_candidate')
                 OR (binary_state='metadata_only' AND classification!='link_only_candidate')
                 OR (classification='retain_evidence' AND binary_state!='retained')""").fetchone()[0]
            if bad:raise ValueError('Invalid archive retention state')


def pack(target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/'ledger.sqlite3';_database_snapshot(snapshot)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(snapshot,'data/ledger.sqlite3')
            for r in retained_archive_rows('hash'):
                p=db.DATA/r['path']
                if not p.is_file() or digest(p)!=r['hash']:raise ValueError('Missing or damaged original '+r['hash'])
                z.write(p,'data/'+r['path'])
    if target.stat().st_size>MAX_ZIP:raise ValueError('Archive approaches the GitHub release asset size limit')
    return {'asset':target.name,'sha256':digest(target),'bytes':target.stat().st_size,'created_at':db.now(),'format':1}


def unpack(archive,destination):
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('Restore requires an empty data directory')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        with zipfile.ZipFile(archive) as z:
            total=0;names=set()
            for info in z.infolist():
                name=PurePosixPath(info.filename)
                if name.is_absolute() or '..' in name.parts or '\\' in info.filename or not name.parts or name.parts[0]!='data':raise ValueError('Unsafe archive path')
                if info.filename in names:raise ValueError('Duplicate archive entry')
                names.add(info.filename);total+=info.file_size
                if total>MAX_EXPANDED or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Invalid archive size or symlink')
            if 'data/ledger.sqlite3' not in names:raise ValueError('The archive has no database')
            z.extractall(tmp)
        verify_data(Path(tmp)/'data')
        if destination.exists():destination.rmdir()
        shutil.move(str(Path(tmp)/'data'),str(destination))


def _validate_zip_member(info,prefix):
    name=PurePosixPath(info.filename)
    if name.is_absolute() or '..' in name.parts or '\\' in info.filename or not name.parts:
        raise ValueError('Unsafe archive path')
    if not str(name).startswith(prefix) or (info.external_attr>>16)&0o170000==0o120000:
        raise ValueError('Invalid archive member '+info.filename)
    return name


def _restore_split_assets(database_zip,source_zips,destination,database_meta=None,pack_meta=None):
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('Restore requires an empty data directory')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        tmp=Path(tmp);stage=tmp/'data';stage.mkdir()
        if database_meta:
            if database_zip.stat().st_size!=database_meta['bytes'] or digest(database_zip)!=database_meta['sha256']:
                raise ValueError('Database checkpoint checksum failed')
        with zipfile.ZipFile(database_zip) as z:
            infos=z.infolist()
            if len(infos)!=1 or infos[0].filename!='data/ledger.sqlite3':
                raise ValueError('Database checkpoint has unexpected contents')
            _validate_zip_member(infos[0],'data/ledger.sqlite3')
            z.extractall(tmp)
        seen=set();expanded=(stage/'ledger.sqlite3').stat().st_size
        metas=pack_meta or [{} for _ in source_zips]
        for archive,meta in zip(source_zips,metas):
            if meta.get('bytes') is not None and archive.stat().st_size!=meta['bytes']:
                raise ValueError('Source pack size check failed: '+archive.name)
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    name=_validate_zip_member(info,'data/archive/')
                    if info.is_dir():continue
                    if info.filename in seen:raise ValueError('Duplicate source file across packs')
                    seen.add(info.filename);expanded+=info.file_size
                    if expanded>MAX_EXPANDED:raise ValueError('Expanded archive is too large')
                z.extractall(tmp)
        verify_data(stage)
        if destination.exists():destination.rmdir()
        shutil.move(str(stage),str(destination))


def _restore_database_only(database_zip,destination,database_meta=None):
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('Restore requires an empty data directory')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        tmp=Path(tmp);stage=tmp/'data';stage.mkdir()
        if database_meta:
            if database_zip.stat().st_size!=database_meta['bytes'] or digest(database_zip)!=database_meta['sha256']:
                raise ValueError('Database checkpoint checksum failed')
        with zipfile.ZipFile(database_zip) as z:
            infos=z.infolist()
            if len(infos)!=1 or infos[0].filename!='data/ledger.sqlite3':
                raise ValueError('Database checkpoint has unexpected contents')
            _validate_zip_member(infos[0],'data/ledger.sqlite3');z.extractall(tmp)
        verify_database(stage)
        if destination.exists():destination.rmdir()
        shutil.move(str(stage),str(destination))


def _extract_source_hashes(archive,hashes,destination):
    destination=Path(destination).resolve();wanted=set(hashes)
    if not wanted:return 0
    placeholders=','.join('?' for _ in wanted)
    if _has_retention_table():
        rows={r['hash']:r for r in db.rows(
            '''SELECT a.hash,a.path,a.bytes FROM archives a
               LEFT JOIN archive_retention r ON r.hash=a.hash
               WHERE a.hash IN (%s) AND COALESCE(r.binary_state,'retained')='retained' '''%placeholders,
            tuple(sorted(wanted)))}
    else:
        rows={r['hash']:r for r in db.rows(
            'SELECT hash,path,bytes FROM archives WHERE hash IN (%s)'%placeholders,
            tuple(sorted(wanted)))}
    if set(rows)!=wanted:
        raise ValueError('Requested source hash is metadata-only, unknown, or not retained')
    written=0
    with zipfile.ZipFile(archive) as z:
        for h,row in rows.items():
            member='data/'+row['path']
            try:info=z.getinfo(member)
            except KeyError:raise ValueError('Source pack is missing '+h)
            _validate_zip_member(info,'data/archive/')
            if info.file_size!=row['bytes']:raise ValueError('Source pack member size mismatch')
            target=(destination/row['path']).resolve()
            if not target.is_relative_to(destination):raise ValueError('Unsafe source destination')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.is_file() and target.stat().st_size==row['bytes'] and digest(target)==h:continue
            temp=target.with_suffix('.tmp')
            digestor=hashlib.sha256()
            with z.open(info) as source,temp.open('wb') as out:
                for block in iter(lambda:source.read(1024*1024),b''):
                    digestor.update(block);out.write(block)
            if digestor.hexdigest()!=h:
                temp.unlink(missing_ok=True);raise ValueError('Source pack member checksum failed: '+h)
            temp.replace(target);written+=1
    return written


def _current_release_manifest(repo,folder):
    override=os.environ.get('SMALLCAP_ARCHIVE_MANIFEST_PATH')
    if override:
        pointer=Path(override).resolve()
        if not pointer.is_file():raise ValueError('Archive manifest override is missing')
        manifest=json.loads(pointer.read_text())
        if int(manifest.get('format',1))<2:raise ValueError('Archive manifest override must use split format')
        return manifest
    pointer=download_asset(repo,'latest.json',folder)
    manifest=json.loads(pointer.read_text());pointer.unlink()
    return manifest


def materialize_hashes(hashes):
    """Restore only source binaries needed by the current operation."""
    requested=set(hashes)
    if not requested:return 0
    if _has_retention_table():
        archive_rows={r['hash']:r for r in db.rows('''SELECT a.hash,a.path,a.bytes,
          COALESCE(r.binary_state,'retained') binary_state
          FROM archives a LEFT JOIN archive_retention r ON r.hash=a.hash''')}
    else:
        archive_rows={r['hash']:{**r,'binary_state':'retained'}
                      for r in db.rows('SELECT hash,path,bytes FROM archives')}
    unknown=requested-set(archive_rows)
    if unknown:raise ValueError('Unknown source hash '+sorted(unknown)[0])
    metadata_only=sorted(h for h in requested if archive_rows[h]['binary_state']!='retained')
    if metadata_only:raise ValueError('Source binary is intentionally metadata-only: '+metadata_only[0])
    missing=set()
    for h in requested:
        row=archive_rows[h];p=(db.DATA/row['path']).resolve()
        if not p.is_relative_to(db.DATA.resolve()):raise ValueError('Unsafe archived source path')
        if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=h:missing.add(h)
    if not missing:return 0
    repo=repository()
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);manifest=_current_release_manifest(repo,tmp)
        if int(manifest.get('format',1))<2:
            raise ValueError('Selective source restore requires split checkpoint format')
        by_asset={}
        for pack in manifest.get('source_packs',[]):
            overlap=missing.intersection(pack.get('hashes',[]))
            if overlap:by_asset[pack['asset']]=(pack,overlap)
        covered=set().union(*(v[1] for v in by_asset.values())) if by_asset else set()
        if covered!=missing:raise ValueError('Split checkpoint does not cover every requested source hash')
        written=0
        for asset,(meta,subset) in by_asset.items():
            archive=download_asset(repo,asset,tmp)
            if meta.get('bytes') is not None and archive.stat().st_size!=meta['bytes']:
                raise ValueError('Source pack size check failed: '+asset)
            written+=_extract_source_hashes(archive,subset,db.DATA);archive.unlink()
    return written


def materialize_all_source_packs():
    return materialize_hashes([r['hash'] for r in retained_archive_rows('hash')])


def _checkpoint_summary(manifest):
    if int(manifest.get('format',1))>=2:
        return {'format':2,'created_at':manifest.get('created_at'),
                'database':manifest['database'],'source_packs':manifest.get('source_packs',[])}
    return {'format':1,'created_at':manifest.get('created_at'),'asset':manifest['asset'],
            'sha256':manifest['sha256'],'bytes':manifest['bytes']}


def gh(*args,check=True):
    return subprocess.run(['gh',*args],text=True,capture_output=True,check=check)


def repository():
    r=os.environ.get('GITHUB_REPOSITORY','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',r):raise ValueError('GITHUB_REPOSITORY must be owner/repository')
    return r


def release(repo):
    # A successful list distinguishes an absent release from a network/permission
    # failure. A download failure must never silently restore an old seed.
    rows=json.loads(gh('api',f'repos/{repo}/releases','--paginate','--slurp').stdout)
    return next((r for page in rows for r in page if r['tag_name']==TAG),None)


def download_asset(repo,name,folder):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('Invalid release asset name')
    gh('release','download',TAG,'--repo',repo,'--pattern',name,'--dir',str(folder))
    return Path(folder)/name


def restore_seed(seed,destination):
    seed=Path(seed);manifest=json.loads((seed/'manifest.json').read_text())
    with tempfile.TemporaryDirectory() as tmp:
        combined=Path(tmp)/'seed.zip'
        with combined.open('wb') as out:
            for part in manifest['parts']:
                p=seed/part['file']
                if p.parent.resolve()!=seed.resolve() or digest(p)!=part['sha256']:raise ValueError('Seed part failed its checksum')
                with p.open('rb') as f:shutil.copyfileobj(f,out)
        if digest(combined)!=manifest['sha256']:raise ValueError('Seed archive checksum failed')
        unpack(combined,destination)


def restore(seed):
    repo=repository();r=release(repo)
    if r is None:
        restore_seed(seed,db.DATA);print('Restored the bundled historical starting archive');return
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);pointer=download_asset(repo,'latest.json',tmp)
        manifest=json.loads(pointer.read_text());fmt=int(manifest.get('format',1))
        if fmt<2:
            state=download_asset(repo,manifest['asset'],tmp)
            if state.stat().st_size!=manifest['bytes'] or digest(state)!=manifest['sha256']:
                raise ValueError('Release archive checksum failed; history was not reset')
            unpack(state,db.DATA);print('Restored '+manifest['asset']);return
        database=download_asset(repo,manifest['database']['asset'],tmp)
        if os.environ.get('SMALLCAP_DATABASE_ONLY_RESTORE')=='1':
            _restore_database_only(database,db.DATA,manifest['database'])
            print(f"Restored database checkpoint {manifest['database']['asset']}; source packs will be materialized on demand")
            return
        packs=[download_asset(repo,p['asset'],tmp) for p in manifest.get('source_packs',[])]
        _restore_split_assets(database,packs,db.DATA,manifest['database'],manifest.get('source_packs',[]))
    print(f"Restored split checkpoint {manifest['database']['asset']} with {len(packs)} source packs")


def publish_split():
    repo=repository();r=release(repo)
    if r is None:
        gh('release','create',TAG,'--repo',repo,'--target',os.environ.get('GITHUB_SHA','main'),
           '--title','Smallcap Ledger historical archive',
           '--notes','Split durable history: latest SQLite checkpoint plus reusable source-file packs. latest.json identifies the active verified set.','--prerelease')
        r=json.loads(gh('api',f'repos/{repo}/releases/tags/{TAG}').stdout)
    if r.get('immutable'):raise ValueError('The tracker-history release is immutable; a writable archive location is required')
    assets={a['name']:a for a in r['assets']}
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);previous=None
        if 'latest.json' in assets:
            old=download_asset(repo,'latest.json',tmp);previous=json.loads(old.read_text());old.unlink()
        rows=retained_archive_rows('first_seen,hash')
        previous_packs=list((previous or {}).get('source_packs',[])) if int((previous or {}).get('format',1))>=2 else []
        covered={h for p in previous_packs for h in p.get('hashes',[])}
        all_hashes={row['hash'] for row in db.rows('SELECT hash FROM archives')}
        retained_hashes={row['hash'] for row in rows}
        if covered-all_hashes:
            raise ValueError('Current database no longer references source files retained by the previous checkpoint')
        # A future approved metadata-only migration must build replacement packs
        # atomically. Never keep an active immutable pack that still carries
        # logically metadata-only members by accident.
        retired_in_active_packs=covered-retained_hashes
        if retired_in_active_packs:
            raise ValueError('Metadata-only retention state requires an approved source-pack repack before publish')
        new_rows=[row for row in rows if row['hash'] not in covered]
        plans=source_pack_plan(new_rows)
        # Existing format-2 source packs are immutable and reused verbatim.
        # Only hashes not covered by the previous checkpoint create new assets.
        pack_records=previous_packs.copy()
        for plan in plans:
            name=plan['asset']
            if name in assets:
                # A prior migration attempt may have uploaded immutable packs
                # before failing later. Verify and reuse them on retry.
                existing=download_asset(repo,name,tmp)
                verify_source_pack_zip(existing,plan)
                pack_records.append({'asset':name,'bucket':plan['bucket'],'part':plan['part'],
                                     'raw_bytes':plan['raw_bytes'],'members':len(plan['members']),
                                     'hashes':[row['hash'] for row in plan['members']],
                                     'bytes':existing.stat().st_size})
                existing.unlink()
                continue
            target=tmp/name;record=pack_source_pack(target,plan)
            gh('release','upload',TAG,str(target),'--repo',repo);pack_records.append(record)
        run=os.environ.get('GITHUB_RUN_ID',db.now().replace(':','').replace('+',''))
        attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1')
        database_asset=f'database-{run}-{attempt}.zip'
        database=pack_database(tmp/database_asset)
        gh('release','upload',TAG,str(tmp/database_asset),'--repo',repo)
        manifest={'format':FORMAT,'created_at':db.now(),'database':database,'source_packs':pack_records,
                  'source_pack_raw_limit':SOURCE_PACK_RAW_LIMIT,
                  'previous':_checkpoint_summary(previous) if previous else None}
        pointer=tmp/'latest.json';pointer.write_text(json.dumps(manifest,indent=2)+'\n')
        gh('release','upload',TAG,str(pointer),'--repo',repo,'--clobber')
        keep={'latest.json',database_asset,*[p['asset'] for p in pack_records]}
        if manifest['previous']:
            old=manifest['previous']
            if old['format']==1:keep.add(old['asset'])
            else:
                keep.add(old['database']['asset']);keep.update(p['asset'] for p in old.get('source_packs',[]))
        for asset in r['assets']:
            name=asset['name']
            managed=(re.fullmatch(r'database-[A-Za-z0-9_.-]+\.zip',name) or
                     re.fullmatch(r'sources-[A-Za-z0-9_.-]+\.zip',name))
            if managed and name not in keep:
                gh('release','delete-asset',TAG,name,'--repo',repo,'--yes')
    print(f"Saved split checkpoint {database_asset} with {len(pack_records)} reusable source packs")



def publish_legacy():
    """Original cumulative ZIP publisher retained for staged migration."""
    repo=repository();r=release(repo)
    if r is None:
        gh('release','create',TAG,'--repo',repo,'--target',os.environ.get('GITHUB_SHA','main'),
           '--title','Smallcap Ledger historical archive',
           '--notes','Cumulative SQLite records and original source files. Download latest.json to identify the current checkpoint.','--prerelease')
        r=json.loads(gh('api',f'repos/{repo}/releases/tags/{TAG}').stdout)
    if r.get('immutable'):raise ValueError('The tracker-history release is immutable; a writable archive location is required')
    with tempfile.TemporaryDirectory() as tmp:
        asset='state-'+os.environ.get('GITHUB_RUN_ID',db.now().replace(':','').replace('+',''))+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')+'.zip'
        target=Path(tmp)/asset;manifest=pack(target)
        previous=None
        if any(a['name']=='latest.json' for a in r['assets']):
            old=download_asset(repo,'latest.json',tmp);old_manifest=json.loads(old.read_text());old.unlink()
            if int(old_manifest.get('format',1))<2:previous=old_manifest.get('asset')
        gh('release','upload',TAG,str(target),'--repo',repo)
        manifest['previous_asset']=previous
        pointer=Path(tmp)/'latest.json';pointer.write_text(json.dumps(manifest,indent=2)+'\n')
        gh('release','upload',TAG,str(pointer),'--repo',repo,'--clobber')
        keep={asset,previous}
        for a in r['assets']:
            if re.fullmatch(r'state-[A-Za-z0-9_.-]+\.zip',a['name']) and a['name'] not in keep:
                gh('release','delete-asset',TAG,a['name'],'--repo',repo,'--yes')
    print('Saved cumulative archive '+asset)


def publish():
    # Format 2 is deliberately opt-in for the migration run. Until enabled,
    # production keeps using the proven cumulative checkpoint format.
    if os.environ.get('SMALLCAP_ARCHIVE_FORMAT')=='2':publish_split()
    else:publish_legacy()

def seed(target,part_mb=20):
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive=Path(tmp)/'state.zip';manifest=pack(archive);manifest.pop('asset');manifest['parts']=[]
        with archive.open('rb') as f:
            i=1
            while block:=f.read(part_mb*1024*1024):
                p=target/f'history.part{i:03d}';p.write_bytes(block)
                manifest['parts'].append({'file':p.name,'bytes':len(block),'sha256':digest(p)});i+=1
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'seed':str(target),'bytes':manifest['bytes'],'parts':len(manifest['parts'])}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['restore','publish','seed','pack','unpack','restore-seed']);p.add_argument('--path',type=Path);p.add_argument('--seed',type=Path,default=ROOT/'bootstrap');p.add_argument('--destination',type=Path,default=db.DATA);a=p.parse_args()
    if a.command=='restore':restore(a.seed)
    elif a.command=='publish':publish()
    elif a.command=='seed':seed(a.seed)
    elif a.command=='pack':print(json.dumps(pack(a.path or ROOT/'state.zip'),indent=2))
    elif a.command=='unpack':unpack(a.path,a.destination)
    else:restore_seed(a.seed,a.destination)
