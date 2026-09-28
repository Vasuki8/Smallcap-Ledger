"""Wire exact labeled sources into existing audit artifacts without changing launch thresholds."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from tracker import midcap_benchmark_labels as labels
from tracker import midcap_benchmark_batch2 as batch2
from tracker.midcap_benchmark_readiness import reconcile
from test_midcap_benchmark_labels import MIRAE, AXIS, NOW, mirae, axis

class LabeledBenchmarkIntegrationTests(unittest.TestCase):
    def source(self,family=MIRAE):
        content=mirae() if family==MIRAE else axis()
        return labels.inspect_family(family,labels.SOURCES[family],fetch_fn=lambda *a,**kw:(content.encode(),None,'text/html'),now=NOW)
    def test_original_proof_is_retained_in_combined_report(self):
        item=self.source(); r=reconcile({MIRAE:labels.AMCS[MIRAE]},{'results':[item]})
        row=r['families_detail'][0]
        self.assertEqual(row.get('source_sha256'),item['source_sha256'])
        self.assertEqual(row.get('source_evidence'),item)
    def test_combined_source_proof_is_not_a_mutable_alias(self):
        item=self.source(); original=deepcopy(item)
        row=reconcile({MIRAE:labels.AMCS[MIRAE]},{'results':[item]})['families_detail'][0]
        self.assertIsNotNone(row.get('source_evidence'))
        row['source_evidence']['reported_benchmarks'].append('not a publisher value')
        self.assertEqual(item,original)
    def test_the_two_registered_sources_are_added_to_existing_batch(self):
        self.assertTrue(set(labels.SOURCES)<=set(batch2.SOURCES))
    def test_batch_dispatches_to_label_parser_and_keeps_legacy_transport(self):
        staged=[{'family':family,'amc':labels.AMCS.get(family,'Legacy AMC')} for family in batch2.SOURCES]
        calls=[]
        def fetch(url,**kwargs):
            calls.append(url)
            html=mirae() if url==labels.SOURCES[MIRAE] else axis()
            return html.encode(),None,'text/html'
        def legacy(family,url,**kwargs):
            self.assertNotIn(family,labels.SOURCES)
            return {'family':family,'status':'recovered','primary_benchmark':'Legacy index'}
        with patch.object(batch2.db,'rows',return_value=staged),patch.object(batch2,'inspect_family',side_effect=legacy):
            r=batch2.collect(fetch_fn=fetch)
        by={x['family']:x for x in r['results']}
        self.assertIn(MIRAE,by);self.assertIn(AXIS,by)
        self.assertEqual(by[AXIS]['primary_benchmark'],'BSE Midcap 150 TRI')
        self.assertEqual(len(calls),2)
        self.assertFalse(r['public_export_enabled']);self.assertEqual(r['production_writes'],0)
    def test_wrong_amc_does_not_overwrite_source_ownership(self):
        staged=[{'family':MIRAE,'amc':'Wrong AMC'}]
        with patch.object(batch2.db,'rows',return_value=staged):
            r=batch2.collect(fetch_fn=lambda *a,**kw:(mirae().encode(),None,'text/html'))
        self.assertFalse(r['results'])
        self.assertTrue(any(x['family']==MIRAE and 'ownership' in x['error'] for x in r['errors']))
    def test_invalid_source_is_a_gap_not_an_inferred_benchmark(self):
        staged=[{'family':MIRAE,'amc':labels.AMCS[MIRAE]}]
        with patch.object(batch2.db,'rows',return_value=staged):
            r=batch2.collect(fetch_fn=lambda *a,**kw:(b'<html>Generic page</html>',None,'text/html'))
        self.assertFalse(r['results'])
        self.assertTrue(any(x['family']==MIRAE for x in r['errors']))
    def test_reconciliation_does_not_turn_identity_into_verified_series(self):
        item=self.source(); r=reconcile({MIRAE:labels.AMCS[MIRAE]},{'results':[item]})
        self.assertFalse(r['public_export_enabled'])
        self.assertEqual(r['benchmark_identity'],1)
        self.assertIsNotNone(r['families_detail'][0].get('source_evidence'))
        self.assertFalse(r['families_detail'][0]['source_evidence']['benchmark_series_verified'])

if __name__=='__main__':unittest.main()
