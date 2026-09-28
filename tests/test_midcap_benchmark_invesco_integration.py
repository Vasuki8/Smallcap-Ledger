"""Invesco source wiring and provenance in the existing non-public batch."""
import unittest
from unittest.mock import patch
from tracker import midcap_benchmark_batch2 as batch2
from tracker import midcap_benchmark_invesco as invesco
from tracker.midcap_benchmark_readiness import reconcile
from test_midcap_benchmark_invesco import FAMILY, NOW, COVER, detail, pdf_bytes


class InvescoBenchmarkIntegrationTests(unittest.TestCase):
    def collect(self, amc=invesco.AMC, body=None):
        self.calls = []
        payload = body if body is not None else pdf_bytes([COVER, detail()])
        def fetch(url, **kwargs):
            self.calls.append((url, kwargs)); return payload, None, 'application/pdf'
        with patch.object(batch2.db, 'rows', return_value=[{'family': FAMILY, 'amc': amc}]), \
             patch.object(batch2.db, 'connect', side_effect=AssertionError('No financial writes')), \
             patch.object(invesco, '_clock', return_value=NOW):
            return batch2.collect(fetch_fn=fetch)

    def test_existing_batch_collects_invesco_without_new_producing_artifact(self):
        result = self.collect()
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(result['results'][0]['family'], FAMILY)
        self.assertEqual(result['results'][0]['primary_benchmark'], 'BSE 150 Midcap TRI')
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.calls[0][1]['archive'])
        self.assertEqual(result['targets'], len(batch2.SOURCES) + 1)
        self.assertFalse(result['public_export_enabled'])
        self.assertEqual(result['production_writes'], 0)

    def test_wrong_staged_amc_is_rejected_before_source_fetch(self):
        result = self.collect(amc='Other AMC')
        self.assertFalse(self.calls)
        self.assertFalse(result['results'])
        errors = [x for x in result['errors'] if x['family'] == FAMILY]
        self.assertEqual(len(errors), 1)
        self.assertIn('ownership', errors[0]['error'])

    def test_bad_source_stays_explicit_gap(self):
        result = self.collect(body=b'<html>generic page</html>')
        self.assertFalse(result['results'])
        self.assertTrue(any(x['family'] == FAMILY for x in result['errors']))

    def test_combined_readiness_keeps_original_proof_and_no_series_claim(self):
        result = self.collect()
        self.assertEqual(len(result['results']), 1)
        item = result['results'][0]
        combined = reconcile({FAMILY: invesco.AMC}, result)
        row = combined['families_detail'][0]
        self.assertEqual(combined['benchmark_identity'], 1)
        self.assertEqual(row['source_evidence'], item)
        self.assertFalse(row['source_evidence']['benchmark_series_verified'])
        self.assertIsNone(row['source_evidence']['benchmark_effective_as_of'])
        row['source_evidence']['reported_benchmarks'].append('not publisher wording')
        self.assertEqual(item['reported_benchmarks'], ['BSE 150 Midcap TRI'])
        self.assertFalse(combined['public_export_enabled'])

if __name__ == '__main__': unittest.main()
