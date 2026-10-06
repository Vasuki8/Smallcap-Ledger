"""AMFI fee month completion must require retained matched evidence."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import amfi_metrics, db


class AmfiFeeMonthCompletionTests(unittest.TestCase):
    def test_empty_month_is_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            with patch("tracker.amfi_metrics.india_today",return_value=date(2026,10,6)), \
                 patch("tracker.amfi_metrics.fetch",
                       return_value=(json.dumps({"data":[]}).encode(),"empty-hash","application/json")), \
                 patch("tracker.amfi_metrics.save_fees",return_value=(0,set(),set())):
                amfi_metrics.fees(months=3)
            self.assertFalse(db.setting("amfi_fee_month_08-2026",False))
            self.assertFalse(db.setting("amfi_fee_month_09-2026",False))
            self.assertFalse(db.setting("amfi_fee_month_10-2026",False))

    def test_matched_month_is_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            body=json.dumps({"data":[{"schemeName":"Example"}]}).encode()
            with patch("tracker.amfi_metrics.india_today",return_value=date(2026,10,6)), \
                 patch("tracker.amfi_metrics.fetch",
                       return_value=(body,"matched-hash","application/json")), \
                 patch("tracker.amfi_metrics.save_fees",
                       return_value=(1,{"Example Small Cap Fund"},set())):
                amfi_metrics.fees(months=3)
            self.assertTrue(db.setting("amfi_fee_month_08-2026",False))
            self.assertTrue(db.setting("amfi_fee_month_09-2026",False))
            self.assertTrue(db.setting("amfi_fee_month_10-2026",False))


if __name__=="__main__":
    unittest.main()
