"""Durable, verified cumulative archives for a stateless GitHub Actions runner.

Each checkpoint contains all retained observations and all original source files.
The pointer is switched only after the new immutable ZIP asset is uploaded.
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


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def verify_data(folder):
    folder=Path(folder)
    with sqlite3.connect(f'file:{(folder/"ledger.sqlite3").as_posix()}?mode=ro',uri=True) as c:
        if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Archive database is damaged')
        if not c.execute('SELECT COUNT(*) FROM schemes').fetchone()[0]:raise ValueError('Archive contains no schemes')
        if not c.execute('SELECT COUNT(*) FROM nav').fetchone()[0]:raise ValueError('Archive contains no NAV history')
        for h,path,size in c.execute('SELECT hash,path,bytes FROM archives'):
            p=(folder/path).resolve()
            if not p.is_relative_to(folder.resolve()) or not p.is_file():raise ValueError('Missing archive file '+h)
            if p.stat().st_size!=size or digest(p)!=h:raise ValueError('Source-file checksum failed: '+h)


def pack(target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/'ledger.sqlite3'
        with db.connect() as source,sqlite3.connect(snapshot) as dest:source.backup(dest)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(snapshot,'data/ledger.sqlite3')
            for r in db.rows('SELECT hash,path FROM archives ORDER BY hash'):
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
        pointer=download_asset(repo,'latest.json',tmp)
        manifest=json.loads(pointer.read_text())
        state=download_asset(repo,manifest['asset'],tmp)
        if state.stat().st_size!=manifest['bytes'] or digest(state)!=manifest['sha256']:raise ValueError('Release archive checksum failed; history was not reset')
        unpack(state,db.DATA)
    print('Restored '+manifest['asset'])


def publish():
    repo=repository();r=release(repo)
    if r is None:
        gh('release','create',TAG,'--repo',repo,'--target',os.environ.get('GITHUB_SHA','main'),'--title','Smallcap Ledger historical archive','--notes','Cumulative SQLite records and original source files. Download latest.json to identify the current checkpoint. Every checkpoint retains all collected historical observations.','--prerelease')
        r=json.loads(gh('api',f'repos/{repo}/releases/tags/{TAG}').stdout)
    if r.get('immutable'):raise ValueError('The tracker-history release is immutable; a writable archive location is required')
    with tempfile.TemporaryDirectory() as tmp:
        asset='state-'+os.environ.get('GITHUB_RUN_ID',db.now().replace(':','').replace('+',''))+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')+'.zip'
        target=Path(tmp)/asset;manifest=pack(target)
        previous=None
        if any(a['name']=='latest.json' for a in r['assets']):
            old=download_asset(repo,'latest.json',tmp);previous=json.loads(old.read_text())['asset'];old.unlink()
        # Never overwrite the sole valid checkpoint. Retain the previous one too.
        gh('release','upload',TAG,str(target),'--repo',repo)
        manifest['previous_asset']=previous
        pointer=Path(tmp)/'latest.json';pointer.write_text(json.dumps(manifest,indent=2)+'\n')
        gh('release','upload',TAG,str(pointer),'--repo',repo,'--clobber')
        keep={asset,previous}
        for a in r['assets']:
            if re.fullmatch(r'state-[A-Za-z0-9_.-]+\.zip',a['name']) and a['name'] not in keep:
                gh('release','delete-asset',TAG,a['name'],'--repo',repo,'--yes')
    print('Saved cumulative archive '+asset)


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
