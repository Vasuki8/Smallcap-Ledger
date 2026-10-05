"""Volatility must not annualize a multi-day missing-NAV jump as one daily return."""
from datetime import date, timedelta
import json
import math
import subprocess
import unittest
from pathlib import Path

from tracker import analytics

ROOT=Path(__file__).resolve().parents[1]


class VolatilityGapTests(unittest.TestCase):
    def series_with_four_day_gap(self):
        points=[]
        current=date(2026,1,1)
        value=100.0
        for i in range(40):
            if i==20:
                current+=timedelta(days=4)
                value*=1.50
            elif i:
                current+=timedelta(days=1)
                value*=1.01
            points.append([current.isoformat(),value])
        return points

    def test_python_volatility_excludes_four_day_jump(self):
        result=analytics.performance(self.series_with_four_day_gap())
        self.assertIsNotNone(result['volatility'])
        self.assertAlmostEqual(result['volatility'],0.0,places=8)

    def test_static_and_python_volatility_gap_rule_match(self):
        points=self.series_with_four_day_gap()
        script="const a=require('./dist/analytics.js');const p=JSON.parse(require('fs').readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(a.performance(p)));"
        run=subprocess.run(['node','-e',script],input=json.dumps(points),cwd=ROOT,text=True,capture_output=True,check=True)
        static=json.loads(run.stdout)
        python=analytics.performance(points)
        self.assertAlmostEqual(static['volatility'],python['volatility'],places=10)

    def test_three_day_interval_remains_eligible_for_weekend_spacing(self):
        points=[]
        current=date(2026,1,1)
        value=100.0
        for i in range(35):
            if i:
                current+=timedelta(days=3 if i==20 else 1)
                value*=1.01
            points.append([current.isoformat(),value])
        result=analytics.performance(points)
        self.assertIsNotNone(result['volatility'])
        self.assertAlmostEqual(result['volatility'],0.0,places=8)


if __name__=='__main__':
    unittest.main()
