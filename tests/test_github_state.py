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

    def test_checkpoint_summary_supports_legacy_and_split(self):
        legacy={'format':1,'asset':'state.zip','sha256':'abc','bytes':123,'created_at':'now'}
        split={'format':2,'created_at':'now','database':{'asset':'database.zip'},'source_packs':[{'asset':'sources.zip'}]}
        self.assertEqual(github_state._checkpoint_summary(legacy)['asset'],'state.zip')
        self.assertEqual(github_state._checkpoint_summary(split)['database']['asset'],'database.zip')


if __name__=='__main__':
    unittest.main()
