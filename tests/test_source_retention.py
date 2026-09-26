"""Retention proposals must err toward preserving original evidence."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from scripts import audit_source_retention as audit


def item(**changes):
    x = {'hash': 'a'*64, 'path': 'archive/aa/'+'a'*64, 'bytes': 100,
         'evidence_reasons': [], 'urls': ['https://example.com/downloads'],
         'kind': 'html', 'latest_for_urls': [], 'fragile_urls': [],
         'latest_error_urls': [], 'pending_extractions': [], 'superseded_for_all_urls': True}
    x.update(changes)
    return x


class RetentionRuleTests(unittest.TestCase):
    def test_superseded_discovery_html_is_only_a_candidate(self):
        self.assertEqual(audit.classify(item())[0], 'link_only_candidate')

    def test_current_source_is_kept(self):
        self.assertEqual(audit.classify(item(latest_for_urls=['https://example.com/downloads']))[0], 'retain_latest_or_review')

    def test_missing_url_is_kept(self):
        self.assertEqual(audit.classify(item(urls=[]))[0], 'retain_latest_or_review')

    def test_nonportable_url_is_kept(self):
        self.assertEqual(audit.classify(item(urls=['file:///tmp/original']))[0], 'retain_latest_or_review')

    def test_financial_evidence_wins_over_candidate(self):
        self.assertEqual(audit.classify(item(evidence_reasons=['metric_hash']))[0], 'retain_evidence')

    def test_one_protected_use_protects_shared_hash(self):
        self.assertEqual(audit.classify(item(urls=['https://a.com/old', 'https://b.com/new'], latest_for_urls=['https://b.com/new']))[0], 'retain_latest_or_review')

    def test_unknown_or_publication_file_is_kept(self):
        self.assertEqual(audit.classify(item(kind='publication_or_data_file'))[0], 'retain_latest_or_review')

    def test_transport_blocked_source_is_kept(self):
        self.assertEqual(audit.classify(item(fragile_urls=['https://www.edelweissmf.com/']))[0], 'retain_latest_or_review')

    def test_latest_failed_fetch_is_kept(self):
        self.assertEqual(audit.classify(item(latest_error_urls=['https://example.com/']))[0], 'retain_latest_or_review')

    def test_failed_extraction_is_kept(self):
        self.assertEqual(audit.classify(item(pending_extractions=['old-parser']))[0], 'retain_latest_or_review')

    def test_no_newer_response_is_kept(self):
        self.assertEqual(audit.classify(item(superseded_for_all_urls=False))[0], 'retain_latest_or_review')

    def test_json_request_identity_is_not_inferred_from_url(self):
        self.assertEqual(audit.classify(item(kind='json'))[0], 'retain_latest_or_review')

    def test_plain_text_data_is_not_assumed_to_be_discovery(self):
        self.assertEqual(audit.classify(item(kind='text'))[0], 'retain_latest_or_review')

    def test_file_extension_overrides_misleading_media_type(self):
        self.assertEqual(audit.response_kind('text/html', ['https://example.com/report.pdf?v=1']), 'publication_or_data_file')

    def test_existing_and_legacy_rollback_assets_remain_distinct(self):
        old = {'format': 1, 'asset': 'state-old.zip'}
        self.assertEqual(audit.reference_assets(old), {'state-old.zip'})
        current = {'format': 2, 'database': {'asset': 'db.zip'}, 'source_packs': [{'asset': 'sources.zip'}]}
        self.assertEqual(audit.reference_assets(current), {'db.zip', 'sources.zip'})


class RetentionDependencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / 'ledger.sqlite3'
        self.c = sqlite3.connect(self.path)
        self.c.executescript('''
          CREATE TABLE archives(hash TEXT PRIMARY KEY,path TEXT,bytes INTEGER,media_type TEXT,first_seen TEXT);
          CREATE TABLE archive_retention(hash TEXT PRIMARY KEY,classification TEXT,binary_state TEXT,reason TEXT,reviewed_at TEXT,updated_at TEXT);
          CREATE TABLE fetches(id INTEGER PRIMARY KEY,url TEXT,fetched_at TEXT,status TEXT,hash TEXT,detail TEXT);
          CREATE TABLE metrics(family TEXT,source TEXT,hash TEXT,as_of TEXT);
          CREATE TABLE portfolios(family TEXT,source TEXT,hash TEXT,as_of TEXT);
          CREATE TABLE documents(id INTEGER PRIMARY KEY,family TEXT,url TEXT,title TEXT,published_at TEXT,kind TEXT);
          CREATE TABLE document_versions(document_id INTEGER,hash TEXT,observed_at TEXT);
          CREATE TABLE document_extractions(family TEXT,hash TEXT,parser_version TEXT,url TEXT,status TEXT,records INTEGER);
          CREATE TABLE nav_observations(source TEXT);
          CREATE TABLE source_pages(url TEXT,status TEXT);
          CREATE TABLE settings(key TEXT,value TEXT);
        ''')
        self.url = 'https://example.com/downloads'
        self.old = 'a'*64
        self.new = 'b'*64
        for h, when in ((self.old, '2026-09-01'), (self.new, '2026-09-24')):
            self.c.execute('INSERT INTO archives VALUES(?,?,?,?,?)', (h, 'archive/'+h[:2]+'/'+h, 100, 'text/html', when))
            self.c.execute('INSERT INTO archive_retention VALUES(?,?,?,?,?,?)',
                           (h,'unclassified','retained',None,None,when))
            self.c.execute('INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)', (self.url, when, 'ok', h))
        self.c.commit()

    def tearDown(self):
        self.c.close()
        self.tmp.cleanup()

    def collect(self):
        return audit.collect(self.c, self.root)[0]

    def test_old_page_candidate_new_page_kept_and_input_unmodified(self):
        before = audit.sha256(self.path)
        result = self.collect()
        self.assertEqual(result[self.old]['classification'], 'link_only_candidate')
        self.assertEqual(result[self.new]['classification'], 'retain_latest_or_review')
        self.assertEqual(before, audit.sha256(self.path))

    def test_nav_source_without_hash_protects_all_response_versions(self):
        self.c.execute('INSERT INTO nav_observations VALUES(?)', (self.url,))
        result = self.collect()
        self.assertTrue(all(x['classification']=='retain_evidence' for x in result.values()))

    def test_successful_old_extraction_protects_pruned_portfolio_evidence(self):
        self.c.execute('INSERT INTO document_extractions VALUES(?,?,?,?,?,?)', ('Fund', self.old, 'v1', self.url, 'parsed', 20))
        self.assertEqual(self.collect()[self.old]['classification'], 'retain_evidence')

    def test_unknown_hash_dependency_is_protected(self):
        self.c.execute('CREATE TABLE future_audit(source_hash TEXT)')
        self.c.execute('INSERT INTO future_audit VALUES(?)', (self.old,))
        self.assertEqual(self.collect()[self.old]['classification'], 'retain_evidence')

    def test_code_literal_hash_is_protected(self):
        (self.root/'tracker').mkdir()
        (self.root/'tracker'/'replay.py').write_text('SOURCE_HASH='+repr(self.old))
        self.assertEqual(self.collect()[self.old]['classification'], 'retain_evidence')

    def test_retention_metadata_table_does_not_self_protect_candidates(self):
        self.c.execute("UPDATE archive_retention SET classification='link_only_candidate' WHERE hash=?",(self.old,))
        self.c.commit()
        result=self.collect()
        self.assertEqual(result[self.old]['classification'],'link_only_candidate')
        self.assertNotIn('database_literal_hash_dependency:archive_retention.hash',
                         result[self.old]['evidence_reasons'])

    def test_collect_exposes_binary_state_without_changing_classification_rules(self):
        self.c.execute("""UPDATE archive_retention SET
          classification='link_only_candidate',binary_state='metadata_only'
          WHERE hash=?""",(self.old,))
        self.c.commit()
        result=self.collect()
        self.assertEqual(result[self.old]['binary_state'],'metadata_only')
        self.assertEqual(result[self.old]['stored_classification'],'link_only_candidate')
        self.assertEqual(result[self.old]['classification'],'link_only_candidate')

    def test_generated_migration_artifacts_do_not_self_protect_hashes(self):
        (self.root/'docs').mkdir()
        for name in (
            'RETENTION-PROPOSED-MANIFEST.json',
            'RETENTION-MIGRATION-CANDIDATES.json',
            'RETENTION-REPLACEMENT-SIMULATION.md',
        ):
            (self.root/'docs'/name).write_text('generated review hash '+self.old)
        result=self.collect()
        self.assertEqual(result[self.old]['classification'],'link_only_candidate')
        self.assertFalse(any(
            'RETENTION-' in reason for reason in result[self.old]['evidence_reasons']))

    def test_generated_inventory_does_not_self_protect_every_hash(self):
        (self.root/'docs').mkdir()
        (self.root/'docs'/'SOURCE-RETENTION-INVENTORY.json').write_text(repr(self.old))
        self.assertEqual(self.collect()[self.old]['classification'], 'link_only_candidate')

    def test_tied_fetch_times_do_not_establish_supersession(self):
        self.c.execute('UPDATE fetches SET fetched_at=?', ('2026-09-24',))
        self.assertTrue(all(x['classification']=='retain_latest_or_review' for x in self.collect().values()))

    def test_latest_error_protects_old_versions(self):
        self.c.execute('INSERT INTO fetches(url,fetched_at,status,detail) VALUES(?,?,?,?)', (self.url, '2026-09-25', 'error', '403 Forbidden'))
        self.assertEqual(self.collect()[self.old]['classification'], 'retain_latest_or_review')

    def test_current_document_version_is_retained_despite_newer_unattached_fetch(self):
        self.c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)', (1, 'Fund', self.url, 'Downloads', None, 'source page'))
        self.c.execute('INSERT INTO document_versions VALUES(?,?,?)', (1, self.old, '2026-09-01'))
        result = self.collect()
        self.assertEqual(result[self.old]['classification'], 'retain_latest_or_review')
        self.assertEqual(result[self.old]['latest_document_ids'], [1])

    def test_old_document_version_can_be_candidate_after_new_version_attached(self):
        self.c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)', (1, 'Fund', self.url, 'Downloads', None, 'source page'))
        self.c.execute('INSERT INTO document_versions VALUES(?,?,?)', (1, self.old, '2026-09-01'))
        self.c.execute('INSERT INTO document_versions VALUES(?,?,?)', (1, self.new, '2026-09-24'))
        result = self.collect()
        self.assertEqual(result[self.old]['classification'], 'link_only_candidate')
        self.assertEqual(result[self.new]['classification'], 'retain_latest_or_review')

    def test_source_hash_missing_from_archive_is_reported(self):
        self.c.execute('INSERT INTO metrics VALUES(?,?,?,?)', ('Fund', self.url, 'c'*64, '2026-09-24'))
        self.assertEqual(audit.collect(self.c, self.root)[1], ['c'*64])



class RetentionMetadataPreparationTests(unittest.TestCase):
    def test_prepare_repairs_generated_artifact_false_promotion_and_classifies_new_hash(self):
        import json
        from tracker import db
        from scripts import prepare_retention_metadata as prep
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous_data=db.DATA;previous_inventory=prep.INVENTORY
            db.DATA=root
            try:
                db.init()
                old_candidate=db.archive(b'old reviewed candidate','text/html')
                new_hash=db.archive(b'new current source page','text/html')
                inventory=root/'inventory.json'
                inventory.write_text(json.dumps([
                    {'hash':old_candidate,'classification':'link_only_candidate'},
                ]))
                prep.INVENTORY=inventory
                # Simulate the bug created by generated migration artifacts.
                with db.connect() as cx:
                    cx.execute("""UPDATE archive_retention SET
                      classification='retain_evidence',
                      reason=? WHERE hash=?""",(
                      prep.SCAN_REASON_PREFIX+
                      'code_or_handoff_literal_hash:docs/RETENTION-PROPOSED-MANIFEST.json',
                      old_candidate))
                current_items={
                    old_candidate:{
                        'classification':'link_only_candidate',
                        'reasons':['superseded_html_or_script_response'],
                        'primary_url':'https://example.com/old',
                        'host':'example.com','kind':'html','evidence_reasons':[],
                        'latest_for_urls':[],'urls':['https://example.com/old'],
                    },
                    new_hash:{
                        'classification':'retain_latest_or_review',
                        'reasons':['latest_saved_response_for_at_least_one_url'],
                        'primary_url':'https://example.com/current',
                        'host':'example.com','kind':'html','evidence_reasons':[],
                        'latest_for_urls':['https://example.com/current'],
                        'urls':['https://example.com/current'],
                    },
                }
                manifest={'format':2,'created_at':'now'}
                delta=root/'delta.json';delta_md=root/'delta.md';candidate=root/'candidates.json'
                with patch.object(prep.retention_audit,'collect',return_value=(current_items,[])), \
                     patch.object(prep,'active_manifest_hashes',
                                  return_value=(manifest,{old_candidate,new_hash})):
                    report=prep.prepare(
                        apply=True,delta_path=delta,delta_markdown=delta_md,
                        candidate_delta=candidate)
                self.assertEqual(db.archive_retention(old_candidate)['classification'],
                                 'link_only_candidate')
                self.assertEqual(db.archive_retention(new_hash)['classification'],
                                 'retain_latest_or_review')
                self.assertEqual(db.archive_retention(old_candidate)['binary_state'],'retained')
                self.assertEqual(db.archive_retention(new_hash)['binary_state'],'retained')
                self.assertEqual(report['post_audit_hashes_reviewed'],1)
                delta_payload=json.loads(delta.read_text())
                self.assertEqual(delta_payload['new_hashes_reviewed'],1)
                self.assertEqual(delta_payload['classifications'],
                                 {'retain_latest_or_review':1})
                self.assertEqual(json.loads(candidate.read_text())['count'],0)
                self.assertTrue(delta_md.is_file())
            finally:
                prep.INVENTORY=previous_inventory
                db.DATA=previous_data

    def test_prepare_applies_reviewed_classes_without_changing_binary_state(self):
        import json
        from tracker import db
        from scripts import prepare_retention_metadata as prep
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous_data=db.DATA;previous_inventory=prep.INVENTORY
            db.DATA=root
            try:
                db.init()
                protected=db.archive(b'protected evidence','application/pdf')
                candidate=db.archive(b'old discovery shell','text/html')
                inventory=root/'inventory.json'
                inventory.write_text(json.dumps([
                    {'hash':protected,'classification':'retain_evidence'},
                    {'hash':candidate,'classification':'link_only_candidate'},
                ]))
                prep.INVENTORY=inventory
                manifest={'format':2,'created_at':'now'}
                current_items={
                    protected:{'classification':'retain_evidence','reasons':['synthetic protected evidence']},
                    candidate:{'classification':'link_only_candidate','reasons':['synthetic superseded discovery response']},
                }
                report_path=root/'report.json'
                with patch.object(prep.retention_audit,'collect',return_value=(current_items,[])), \
                     patch.object(prep,'active_manifest_hashes',return_value=(manifest,{protected,candidate})):
                    report=prep.prepare(apply=True,report_path=report_path)
                self.assertEqual(report['files_actually_deleted'],0)
                self.assertEqual(report['bytes_actually_deleted'],0)
                self.assertEqual(report['binary_states'],{'retained':2})
                self.assertTrue(report['protected_archive_metadata_unchanged'])
                self.assertTrue(report['non_retention_table_fingerprints_unchanged'])
                self.assertFalse(report['deletion_enabled'])
                self.assertEqual(db.archive_retention(protected)['classification'],'retain_evidence')
                self.assertEqual(db.archive_retention(candidate)['classification'],'link_only_candidate')
                self.assertEqual(db.archive_retention(candidate)['binary_state'],'retained')
                self.assertTrue(db.archive_binary_path(candidate).is_file())
                self.assertTrue(report_path.is_file())

                # A newer current fetch/review must never be downgraded by the
                # older inventory when preparation runs again.
                db.set_archive_retention(
                    candidate,classification='retain_latest_or_review',
                    reason='became current',reviewed_at='2026-09-25')
                with patch.object(prep.retention_audit,'collect',return_value=(current_items,[])), \
                     patch.object(prep,'active_manifest_hashes',return_value=(manifest,{protected,candidate})):
                    prep.prepare(apply=True)
                self.assertEqual(db.archive_retention(candidate)['classification'],
                                 'retain_latest_or_review')
            finally:
                prep.INVENTORY=previous_inventory
                db.DATA=previous_data


if __name__ == '__main__': unittest.main()
