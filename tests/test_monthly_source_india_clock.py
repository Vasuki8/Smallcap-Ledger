"""Monthly AMC source discovery must use the India reporting calendar."""
from datetime import date
import unittest
from unittest.mock import patch

from tracker import amc_reports


class MonthlySourceIndiaClockTests(unittest.TestCase):
    def test_default_month_uses_india_today_at_utc_boundary(self):
        with patch("tracker.amc_reports.india_today",return_value=date(2026,10,1)):
            rows=list(amc_reports.monthly_sources())
        urls=[url for _amc,url,_label in rows]
        self.assertTrue(any("/2026/october/" in url for url in urls))
        self.assertTrue(any("October_2026" in url for url in urls))
        self.assertFalse(any("/2026/july/" in url for url in urls))

    def test_explicit_today_remains_deterministic_override(self):
        rows=list(amc_reports.monthly_sources(today=date(2026,9,30)))
        urls=[url for _amc,url,_label in rows]
        self.assertTrue(any("/2026/september/" in url for url in urls))
        self.assertTrue(any("/2026/july/" in url for url in urls))


if __name__=="__main__":
    unittest.main()
