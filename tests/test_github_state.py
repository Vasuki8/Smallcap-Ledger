import hashlib
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import github_state


class SplitArchiveTests(unittest.TestCase):
    def test_source_pack_plan_is_deterministic_and_bounded(self):
        rows=[
            {'hash':'a'*64,'path':'archive/aa/'+'a'*64,'bytes':6,'first_seen':'2026-09-01T00:00:00+00:00'},
            {'hash':'b'*64,'path':'archive/bb/'+'b'*64,'bytes':6,'first_seen':'2026-09-02T00:00:00+00:00'},
            {'hash':'c'*64,'path':'archive/cc/'+'c'*64,'bytes':6,'first_seen':'2026-08-31T00:00:00+00:00'},
        ]
        first=github_state.source_pack_plan(rows,raw_limit=10)
        second=github_state.source_pack_plan(list(reversed(rows)),raw_limit=10)
        self.assertEqual(
            [(x['asset'],x['raw_bytes'],[m['hash'] for m in x['members']]) for x in first],
            [(x['asset'],x['raw_bytes'],[m['hash'] for m in x['members']]) for x in second],
        )
        self.assertTrue(all(x['raw_bytes']<=10 for x in first))
        self.assertEqual([x['bucket'] for x in first],['2026-08','2026-09','2026-09'])

    def test_split_restore_rebuilds_verified_data_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=b'official-source-bytes'
            h=hashlib.sha256(source).hexdigest()
            db_path=root/'ledger.sqlite3'
            with sqlite3.connect(db_path) as c:
                c.execute('CREATE TABLE schemes(code INTEGER PRIMARY KEY)')
                c.execute('CREATE TABLE nav(code INTEGER,date TEXT,value REAL)')
                c.execute('CREATE TABLE archives(hash TEXT,path TEXT,bytes INTEGER)')
                c.execute('INSERT INTO schemes VALUES(1)')
                c.execute("INSERT INTO nav VALUES(1,'2026-09-01',10.0)")
                c.execute('INSERT INTO archives VALUES(?,?,?)',(h,f'archive/{h[:2]}/{h}',len(source)))
            database_zip=root/'database.zip'
            with zipfile.ZipFile(database_zip,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(db_path,'data/ledger.sqlite3')
            source_zip=root/'sources.zip'
            payload=root/h;payload.write_bytes(source)
            with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(payload,f'data/archive/{h[:2]}/{h}')
            destination=root/'restored'
            github_state._restore_split_assets(
                database_zip,[source_zip],destination,
                {'bytes':database_zip.stat().st_size,'sha256':github_state.digest(database_zip)},
                [{'bytes':source_zip.stat().st_size}],
            )
            self.assertEqual((destination/f'archive/{h[:2]}/{h}').read_bytes(),source)
            with sqlite3.connect(destination/'ledger.sqlite3') as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM nav').fetchone()[0],1)

    def test_database_only_restore_skips_source_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            db_path=root/'ledger.sqlite3'
            with sqlite3.connect(db_path) as c:
                c.execute('CREATE TABLE schemes(code INTEGER PRIMARY KEY)')
                c.execute('CREATE TABLE nav(code INTEGER,date TEXT,value REAL)')
                c.execute('CREATE TABLE archives(hash TEXT,path TEXT,bytes INTEGER)')
                c.execute('INSERT INTO schemes VALUES(1)')
                c.execute("INSERT INTO nav VALUES(1,'2026-09-01',10.0)")
            database_zip=root/'database.zip'
            with zipfile.ZipFile(database_zip,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(db_path,'data/ledger.sqlite3')
            destination=root/'restored'
            github_state._restore_database_only(
                database_zip,destination,
                {'bytes':database_zip.stat().st_size,'sha256':github_state.digest(database_zip)},
            )
            self.assertTrue((destination/'ledger.sqlite3').is_file())
            self.assertFalse((destination/'archive').exists())

    def test_selective_source_extract_writes_only_requested_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            one=b'first-source';two=b'second-source'
            h1=hashlib.sha256(one).hexdigest();h2=hashlib.sha256(two).hexdigest()
            with sqlite3.connect(data/'ledger.sqlite3') as c:
                c.execute('CREATE TABLE archives(hash TEXT,path TEXT,bytes INTEGER)')
                c.executemany('INSERT INTO archives VALUES(?,?,?)',[
                    (h1,f'archive/{h1[:2]}/{h1}',len(one)),
                    (h2,f'archive/{h2[:2]}/{h2}',len(two)),
                ])
            pack=root/'pack.zip'
            p1=root/'one';p1.write_bytes(one)
            p2=root/'two';p2.write_bytes(two)
            with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(p1,f'data/archive/{h1[:2]}/{h1}')
                z.write(p2,f'data/archive/{h2[:2]}/{h2}')
            previous=github_state.db.DATA
            github_state.db.DATA=data
            try:
                self.assertEqual(github_state._extract_source_hashes(pack,[h2],data),1)
            finally:
                github_state.db.DATA=previous
            self.assertFalse((data/f'archive/{h1[:2]}/{h1}').exists())
            self.assertEqual((data/f'archive/{h2[:2]}/{h2}').read_bytes(),two)

    def test_existing_source_pack_can_be_verified_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            payload=b'retry-safe-source-pack'
            h=hashlib.sha256(payload).hexdigest()
            source=root/'source.bin';source.write_bytes(payload)
            archive=root/'pack.zip'
            row={'hash':h,'path':f'archive/{h[:2]}/{h}','bytes':len(payload),'first_seen':'2026-09-01T00:00:00+00:00'}
            plan=github_state.source_pack_plan([row])[0]
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(source,'data/'+row['path'])
            self.assertTrue(github_state.verify_source_pack_zip(archive,plan))

    def test_verify_data_requires_only_logically_retained_binaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            retained=b'protected-evidence';metadata=b'old-discovery-shell'
            h1=hashlib.sha256(retained).hexdigest();h2=hashlib.sha256(metadata).hexdigest()
            with sqlite3.connect(data/'ledger.sqlite3') as c:
                c.execute('CREATE TABLE schemes(code INTEGER PRIMARY KEY)')
                c.execute('CREATE TABLE nav(code INTEGER,date TEXT,value REAL)')
                c.execute('CREATE TABLE archives(hash TEXT PRIMARY KEY,path TEXT,bytes INTEGER)')
                c.execute('''CREATE TABLE archive_retention(
                    hash TEXT PRIMARY KEY,classification TEXT,binary_state TEXT,
                    reason TEXT,reviewed_at TEXT,updated_at TEXT)''')
                c.execute('INSERT INTO schemes VALUES(1)')
                c.execute("INSERT INTO nav VALUES(1,'2026-09-01',10.0)")
                c.executemany('INSERT INTO archives VALUES(?,?,?)',[
                    (h1,f'archive/{h1[:2]}/{h1}',len(retained)),
                    (h2,f'archive/{h2[:2]}/{h2}',len(metadata)),
                ])
                c.executemany('INSERT INTO archive_retention VALUES(?,?,?,?,?,?)',[
                    (h1,'retain_evidence','retained',None,None,'now'),
                    (h2,'link_only_candidate','metadata_only','reviewed',None,'now'),
                ])
            target=data/f'archive/{h1[:2]}/{h1}';target.parent.mkdir(parents=True);target.write_bytes(retained)
            github_state.verify_data(data)
            target.unlink()
            with self.assertRaisesRegex(ValueError,'Missing retained archive file'):
                github_state.verify_data(data)

    def test_selective_materialization_rejects_metadata_only_hash_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp);h='a'*64
            with sqlite3.connect(data/'ledger.sqlite3') as c:
                c.execute('CREATE TABLE archives(hash TEXT PRIMARY KEY,path TEXT,bytes INTEGER,first_seen TEXT)')
                c.execute('''CREATE TABLE archive_retention(
                    hash TEXT PRIMARY KEY,classification TEXT,binary_state TEXT,
                    reason TEXT,reviewed_at TEXT,updated_at TEXT)''')
                c.execute('INSERT INTO archives VALUES(?,?,?,?)',(h,f'archive/aa/{h}',100,'2026-09-01'))
                c.execute('INSERT INTO archive_retention VALUES(?,?,?,?,?,?)',
                          (h,'link_only_candidate','metadata_only','reviewed','2026-09-25','now'))
            previous=github_state.db.DATA;github_state.db.DATA=data
            try:
                with self.assertRaisesRegex(ValueError,'metadata-only'):
                    github_state.materialize_hashes([h])
            finally:
                github_state.db.DATA=previous

    def test_pack_planning_selects_only_retained_binary_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)
            h1='1'*64;h2='2'*64
            with sqlite3.connect(data/'ledger.sqlite3') as c:
                c.execute('CREATE TABLE archives(hash TEXT PRIMARY KEY,path TEXT,bytes INTEGER,first_seen TEXT)')
                c.execute('''CREATE TABLE archive_retention(
                    hash TEXT PRIMARY KEY,classification TEXT,binary_state TEXT,
                    reason TEXT,reviewed_at TEXT,updated_at TEXT)''')
                c.executemany('INSERT INTO archives VALUES(?,?,?,?)',[
                    (h1,f'archive/11/{h1}',10,'2026-09-01'),
                    (h2,f'archive/22/{h2}',20,'2026-09-02'),
                ])
                c.executemany('INSERT INTO archive_retention VALUES(?,?,?,?,?,?)',[
                    (h1,'retain_evidence','retained',None,None,'now'),
                    (h2,'link_only_candidate','metadata_only','reviewed','2026-09-25','now'),
                ])
            previous=github_state.db.DATA;github_state.db.DATA=data
            try:
                rows=github_state.retained_archive_rows('first_seen,hash')
            finally:
                github_state.db.DATA=previous
            self.assertEqual([x['hash'] for x in rows],[h1])

    def test_manifest_override_pins_isolated_restore_without_network(self):
        import json,os
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=root/'pinned.json'
            expected={'format':2,'created_at':'pinned','database':{'asset':'db.zip'},'source_packs':[]}
            manifest.write_text(json.dumps(expected))
            previous=os.environ.get('SMALLCAP_ARCHIVE_MANIFEST_PATH')
            os.environ['SMALLCAP_ARCHIVE_MANIFEST_PATH']=str(manifest)
            try:
                self.assertEqual(github_state._current_release_manifest('owner/repo',root),expected)
            finally:
                if previous is None:os.environ.pop('SMALLCAP_ARCHIVE_MANIFEST_PATH',None)
                else:os.environ['SMALLCAP_ARCHIVE_MANIFEST_PATH']=previous

    def test_checkpoint_summary_supports_legacy_and_split(self):
        legacy={'format':1,'asset':'state.zip','sha256':'abc','bytes':123,'created_at':'now'}
        split={'format':2,'created_at':'now','database':{'asset':'database.zip'},'source_packs':[{'asset':'sources.zip'}]}
        self.assertEqual(github_state._checkpoint_summary(legacy)['asset'],'state.zip')
        self.assertEqual(github_state._checkpoint_summary(split)['database']['asset'],'database.zip')


if __name__=='__main__':
    unittest.main()
