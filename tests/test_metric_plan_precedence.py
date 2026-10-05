"""Fund-page metric selection must preserve plan identity for fee metrics."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.app import metrics_for


class MetricPlanPrecedenceTests(unittest.TestCase):
    def test_direct_fee_beats_newer_generic_fee(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            family='Plan Precedence Small Cap Fund'
            db.metric(family,'Direct','ter','2026-09-30',0.72,'% p.a.','https://example.com/direct')
            db.metric(family,'All','ter','2026-10-02',1.25,'% p.a.','https://example.com/generic')
            result=metrics_for({'family':family,'plan':'Direct'})
            self.assertEqual(result['ter']['plan'],'Direct')
            self.assertEqual(float(result['ter']['value']),0.72)

    def test_generic_fee_remains_fallback_when_plan_specific_missing(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            family='Fallback Small Cap Fund'
            db.metric(family,'All','ter','2026-10-02',1.25,'% p.a.','https://example.com/generic')
            result=metrics_for({'family':family,'plan':'Direct'})
            self.assertEqual(result['ter']['plan'],'All')
            self.assertEqual(float(result['ter']['value']),1.25)

    def test_non_fee_metric_keeps_newest_record_behavior(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            family='Fund Wide Small Cap Fund'
            db.metric(family,'Direct','risk','2026-09-30','High','Reported','https://example.com/direct')
            db.metric(family,'All','risk','2026-10-02','Very High','Reported','https://example.com/generic')
            result=metrics_for({'family':family,'plan':'Direct'})
            self.assertEqual(result['risk']['plan'],'All')
            self.assertEqual(result['risk']['value'],'Very High')


if __name__=='__main__':
    unittest.main()
