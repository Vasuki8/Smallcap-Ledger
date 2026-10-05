"""Pages deployment marker provenance regressions."""
import unittest
from datetime import datetime, timezone

from tracker.publication_provenance import PublicationBaseMoved
from scripts.record_deployment import assert_deployment_base, marker


class DeploymentMarkerTests(unittest.TestCase):
    build='1'*40
    status='2'*40

    def test_status_commit_must_be_child_of_tested_build_and_current_main(self):
        self.assertEqual(assert_deployment_base(self.build,self.status,self.build,self.status),self.status)
        with self.assertRaises(PublicationBaseMoved):
            assert_deployment_base(self.build,self.status,'3'*40,self.status)
        with self.assertRaises(PublicationBaseMoved):
            assert_deployment_base(self.build,self.status,self.build,'4'*40)

    def test_marker_identifies_exact_build_status_commit_and_deploy(self):
        now=datetime(2026,10,5,19,15,tzinfo=timezone.utc)
        result=marker(self.build,self.status,'https://vasuki8.github.io/Smallcap-Ledger/','12345',now=now)
        self.assertEqual(result,{
            'publication_state':'deployed',
            'deployed_at':'2026-10-05T19:15:00+00:00',
            'source_build_sha':self.build,
            'status_commit_sha':self.status,
            'page_url':'https://vasuki8.github.io/Smallcap-Ledger/',
            'workflow_run_id':'12345',
        })


if __name__=='__main__':
    unittest.main()
