"""Bounded retry cadence regressions for local update jobs."""
import unittest

from tracker.sync import retry_interval


class PartialRetryTests(unittest.TestCase):
    def test_error_retries_within_thirty_minutes(self):
        self.assertEqual(retry_interval('error',12*3600),1800)

    def test_partial_retries_within_two_hours(self):
        self.assertEqual(retry_interval('partial',12*3600),2*3600)

    def test_partial_never_slows_an_already_faster_schedule(self):
        self.assertEqual(retry_interval('partial',3600),3600)

    def test_healthy_job_keeps_normal_interval(self):
        self.assertEqual(retry_interval('ok',12*3600),12*3600)


if __name__=='__main__':
    unittest.main()
