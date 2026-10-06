"""Publication health gate regressions."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers
from scripts.check_publication_health import evaluate


class PublicationHealthGateTests(unittest.TestCase):
    boundary="2026-10-05T18:30:00Z"
    today=date(2026,10,6)

    def seed(self, *, statuses=None, latest="2026-10-03", include_documents=True):
        statuses=statuses or {}
        with db.connect() as c:
            c.executemany(
                'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                [
                    (9001,'Gate Small Cap Direct Growth','Gate Small Cap Fund','Gate AMC','Direct','Growth','test'),
                    (9002,'Gate Small Cap Regular Growth','Gate Small Cap Fund','Gate AMC','Regular','Growth','test'),
                ],
            )
        for code,value in ((9001,100),(9002,99)):
            db.save_nav(code,[(latest,value)],providers.AMFI_NAV)
        db.save_benchmark(providers.BENCHMARK,[(latest,1234)],providers.NIFTY_PAGE)
        db.metric('Gate Small Cap Fund','All','aum',latest,1000,'INR crore','https://example.com/aum')
        db.metric('Gate Small Cap Fund','Direct','ter',latest,0.7,'% p.a.','https://example.com/ter')
        kinds=['nav','benchmark','metrics']+(['documents'] if include_documents else [])
        with db.connect() as c:
            for i,kind in enumerate(kinds):
                status=statuses.get(kind,'ok')
                c.execute(
                    "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                    (kind,f"2026-10-05T18:30:{10+i:02d}+00:00",f"2026-10-05T18:31:{10+i:02d}+00:00",status,kind+' result'),
                )

    def test_complete_current_run_is_publishable(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed()
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'ok')
            self.assertEqual(result['blockers'],[])

    def test_safe_partial_metrics_is_explicitly_degraded_not_blocked(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(statuses={'metrics':'partial'})
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'degraded')
            self.assertEqual(result['blockers'],[])
            self.assertIn('metrics_job_partial',result['degraded'])

    def test_fresh_retained_benchmark_allows_degraded_publish_after_refresh_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(statuses={'benchmark':'error'},latest='2026-10-05')
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'degraded')
            self.assertEqual(result['blockers'],[])
            self.assertIn(
                'benchmark_job_error_using_fresh_retained_data',
                result['degraded'],
            )

    def test_stale_retained_benchmark_still_blocks_after_refresh_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(latest='2026-10-05')
            with db.connect() as c:
                c.execute("DELETE FROM benchmark WHERE name=?",(providers.BENCHMARK,))
                c.execute(
                    "INSERT INTO benchmark(name,date,value,source,observed_at) VALUES(?,?,?,?,?)",
                    (providers.BENCHMARK,'2026-09-20',1234,providers.NIFTY_PAGE,db.now()),
                )
                c.execute(
                    "UPDATE jobs SET status='error',detail='read timed out' WHERE kind='benchmark'"
                )
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'blocked')
            self.assertIn('benchmark_job_error',result['blockers'])
            self.assertIn('primary_benchmark_stale_or_invalid',result['blockers'])

    def test_error_job_blocks_publication(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(statuses={'nav':'error'})
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'blocked')
            self.assertIn('nav_job_error',result['blockers'])

    def test_job_from_before_current_run_does_not_satisfy_gate(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(include_documents=False)
            with db.connect() as c:
                c.execute(
                    "INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)",
                    ('documents','2026-10-05T18:00:00+00:00','2026-10-05T18:01:00+00:00','ok','old'),
                )
            result=evaluate(self.boundary,today=self.today)
            self.assertIn('documents_job_missing',result['blockers'])

    def test_one_fresh_aum_cannot_hide_another_funds_stale_aum(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(latest='2026-10-05')
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (9010,'Stale Small Cap Direct Growth','Stale Small Cap Fund',
                     'Stale AMC','Direct','Growth','test'),
                )
            db.save_nav(9010,[('2026-10-05',50)],providers.AMFI_NAV)
            db.metric(
                'Stale Small Cap Fund','All','aum','2026-08-01',500,
                'INR crore','https://example.com/stale-aum',
            )
            db.metric(
                'Stale Small Cap Fund','Direct','ter','2026-10-05',0.8,
                '% p.a.','https://example.com/stale-ter',
            )
            result=evaluate(self.boundary,today=self.today)
            self.assertEqual(result['status'],'blocked')
            self.assertNotIn('aum_stale_or_invalid',result['blockers'])
            self.assertIn('aum_fund_dates_stale_or_invalid',result['blockers'])
            self.assertEqual(result['data']['aum_latest_date'],'2026-10-05')
            self.assertEqual(result['data']['aum_earliest_date'],'2026-08-01')
            self.assertEqual(result['data']['aum_oldest_age_days'],66)

    def test_retained_only_mode_uses_data_health_without_current_job_requirement(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(statuses={'documents':'error'},latest='2026-10-05')
            result=evaluate("",today=self.today,require_current_jobs=False)
            self.assertEqual(result['mode'],'retained_only')
            self.assertEqual(result['blockers'],[])
            self.assertEqual(result['status'],'degraded')
            self.assertIn('retained_only_latest_documents_job_error',result['degraded'])

    def test_retained_only_mode_still_blocks_stale_data(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(latest='2026-09-20',include_documents=False)
            result=evaluate("",today=self.today,require_current_jobs=False)
            self.assertEqual(result['mode'],'retained_only')
            self.assertEqual(result['status'],'blocked')
            self.assertNotIn('documents_job_missing',result['blockers'])
            self.assertIn('latest_nav_stale_or_invalid',result['blockers'])
            self.assertIn('primary_benchmark_stale_or_invalid',result['blockers'])
            self.assertIn('aum_stale_or_invalid',result['blockers'])

    def test_stale_nav_and_aum_block_even_when_jobs_are_green(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();self.seed(latest='2026-09-20')
            result=evaluate(self.boundary,today=self.today)
            self.assertIn('latest_nav_stale_or_invalid',result['blockers'])
            self.assertIn('aum_stale_or_invalid',result['blockers'])


if __name__=='__main__':
    unittest.main()
