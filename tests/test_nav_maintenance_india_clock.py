"""NAV history maintenance cutoff must use the India reporting calendar."""
from datetime import date
import unittest
from unittest.mock import patch

from tracker.sync import nav_maintenance_cutoff


class NavMaintenanceIndiaClockTests(unittest.TestCase):
    def test_default_cutoff_uses_india_today(self):
        with patch("tracker.sync.india_today",return_value=date(2026,10,1)):
            self.assertEqual(nav_maintenance_cutoff(),"2026-09-01")

    def test_explicit_date_remains_deterministic(self):
        self.assertEqual(nav_maintenance_cutoff(date(2026,9,30)),"2026-08-31")


if __name__=="__main__":
    unittest.main()
