"""India-calendar freshness boundary regressions."""
from datetime import datetime, timezone, date
import unittest
from unittest.mock import patch

from tracker.clock import india_today
from tracker import coverage


class IndiaCalendarTests(unittest.TestCase):
    def test_india_today_crosses_calendar_day_before_utc(self):
        instant=datetime(2026,9,10,18,31,tzinfo=timezone.utc)
        self.assertEqual(india_today(instant),date(2026,9,11))

    def test_default_portfolio_grace_uses_india_date(self):
        with patch('tracker.coverage.india_today',return_value=date(2026,9,11)):
            self.assertEqual(coverage.expected_portfolio_as_of(),'2026-08-31')
        # UTC would still be September 10 at the 00:00 IST scheduling boundary,
        # which would incorrectly keep July as the expected month-end.
        self.assertEqual(coverage.expected_portfolio_as_of(date(2026,9,10)),'2026-07-31')


if __name__=='__main__':
    unittest.main()
