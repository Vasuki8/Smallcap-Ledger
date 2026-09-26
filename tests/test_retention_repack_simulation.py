import hashlib
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tracker import db
from scripts import simulate_retention_repack as sim


class RetentionRepackSimulationTests(unittest.TestCase):
    def test_repack_filters_only_candidates_and_verifies_retained_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            bodies=[b'candidate-old-page',b'protected-report',b'current-page']
            hashes=[hashlib.sha256(x).hexdigest() for x in bodies]
            rows={}
            old=root/'old.zip'
            with zipfile.ZipFile(old,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for h,body in zip(hashes,bodies):
                    path=f'archive/{h[:2]}/{h}'
                    rows[h]={'hash':h,'path':path,'bytes':len(body),'first_seen':'2026-09-01'}
                    z.writestr('data/'+path,body)
            pack={'asset':'sources-test.zip','hashes':hashes}
            new=root/'new.zip'
            retained,removed=sim.repack_filtered(old,new,pack,rows,{hashes[0]})
            self.assertEqual(removed,[hashes[0]])
            self.assertEqual(retained,hashes[1:])
            with zipfile.ZipFile(new) as z:
                names=set(z.namelist())
                self.assertNotIn('data/'+rows[hashes[0]]['path'],names)
                for h in retained:
                    body=z.read('data/'+rows[h]['path'])
                    self.assertEqual(hashlib.sha256(body).hexdigest(),h)

    def test_current_eligible_candidates_excludes_strengthened_reviewed_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous=db.DATA;db.DATA=root
            try:
                db.init()
                eligible=db.archive(b'old shell still superseded','text/html')
                strengthened=db.archive(b'old shell now current','text/html')
                db.set_archive_retention(
                    eligible,classification='link_only_candidate',
                    reason='reviewed old candidate',reviewed_at='2026-09-25')
                db.set_archive_retention(
                    strengthened,classification='retain_latest_or_review',
                    reason='refetched as current source',reviewed_at='2026-09-25')
                reviewed=[
                    {'hash':eligible,'classification':'link_only_candidate','compressed_payload_bytes':10},
                    {'hash':strengthened,'classification':'link_only_candidate','compressed_payload_bytes':20},
                ]
                current,excluded=sim.current_eligible_candidates(root/'ledger.sqlite3',reviewed)
                self.assertEqual([x['hash'] for x in current],[eligible])
                self.assertEqual([x['hash'] for x in excluded],[strengthened])
                self.assertEqual(excluded[0]['current_classification'],'retain_latest_or_review')
                self.assertEqual(excluded[0]['current_binary_state'],'retained')
            finally:
                db.DATA=previous

    def test_simulation_boundary_requires_696_historical_and_excludes_new_delta(self):
        reviewed=[{'hash':f'{i:064x}'} for i in range(700)]
        candidates=reviewed[:696]
        excluded=[
            {'hash':row['hash'],'current_classification':'retain_latest_or_review',
             'current_binary_state':'retained'}
            for row in reviewed[696:]
        ]
        delta=[{'hash':f'{1000+i:064x}'} for i in range(5)]
        proof=sim.validate_simulation_candidate_boundary(
            reviewed,candidates,excluded,delta)
        self.assertEqual(proof['historical_candidate_count'],696)
        self.assertEqual(proof['excluded_reviewed_candidate_count'],4)
        self.assertEqual(proof['post_audit_delta_candidate_count'],5)
        self.assertEqual(proof['post_audit_delta_overlap_count'],0)
        self.assertTrue(proof['post_audit_delta_excluded'])

        with self.assertRaisesRegex(ValueError,'Expected exactly 696'):
            sim.validate_simulation_candidate_boundary(
                reviewed,candidates[:-1],excluded+[{
                    'hash':candidates[-1]['hash'],
                    'current_classification':'retain_latest_or_review',
                    'current_binary_state':'retained'}],delta)
        with self.assertRaisesRegex(ValueError,'leaked'):
            sim.validate_simulation_candidate_boundary(
                reviewed,candidates,excluded,
                delta[:-1]+[{'hash':candidates[0]['hash']}])

    def test_simulated_database_changes_only_retention_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous=db.DATA;db.DATA=root
            try:
                db.init()
                keep=db.archive(b'protected','application/pdf')
                candidate=db.archive(b'old shell','text/html')
                db.set_archive_retention(keep,classification='retain_evidence',
                                         reason='protected',reviewed_at='2026-09-25')
                db.set_archive_retention(candidate,classification='link_only_candidate',
                                         reason='reviewed',reviewed_at='2026-09-25')
                target=root/'simulation.sqlite3'
                before=sim.db_fingerprints(root/'ledger.sqlite3')
                sim.simulate_database(target,[candidate])
                after=sim.db_fingerprints(target)
                self.assertEqual(before,after)
                with sqlite3.connect(target) as c:
                    self.assertEqual(c.execute(
                        'SELECT binary_state FROM archive_retention WHERE hash=?',
                        (candidate,)).fetchone()[0],'metadata_only')
                    self.assertEqual(c.execute(
                        'SELECT binary_state FROM archive_retention WHERE hash=?',
                        (keep,)).fetchone()[0],'retained')
                self.assertEqual(db.archive_retention(candidate)['binary_state'],'retained')
            finally:
                db.DATA=previous


if __name__=='__main__':
    unittest.main()
