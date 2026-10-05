"""Selected performance range regressions for backend and static analytics."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, providers
from tracker.app import performance

ROOT=Path(__file__).resolve().parents[1]


class PerformanceSelectedRangeTests(unittest.TestCase):
    def test_backend_comparison_stats_do_not_reach_before_selected_start(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            family='Range Test Small Cap Fund';code=88001
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (code,family+' Direct Growth',family,'Range Test AMC','Direct','Growth','test'))
            points=[
                ('2022-01-03',75),('2023-01-02',82),('2024-01-02',90),
                ('2025-01-02',100),('2026-01-02',110),
            ]
            db.save_nav(code,points,providers.AMFI_NAV)
            db.save_benchmark(providers.BENCHMARK,[(d,v*2) for d,v in points],providers.NIFTY_PAGE)
            db.metric(family,'All','benchmark','2026-01-02','Nifty Smallcap 250 TRI','Reported',
                      'https://example.com/range-benchmark','range-benchmark')
            result=performance(code,start='2025-01-02',end='2026-01-02')
            self.assertIsNotNone(result['comparison_stats']['fund']['1Y'])
            self.assertIsNone(result['comparison_stats']['fund']['3Y'])
            self.assertIsNone(result['comparison_stats']['benchmark']['3Y'])

    def test_static_comparison_stats_do_not_reach_before_selected_start(self):
        script=r"""
const a=require('./dist/analytics.js');
const nav=[
 ['2022-01-03',75],['2023-01-02',82],['2024-01-02',90],
 ['2025-01-02',100],['2026-01-02',110]
];
const bench={name:'Nifty Smallcap 250 TRI',source:'https://www.niftyindices.com/reports/historical-data',
 data:nav.map(([d,v])=>[d,v*2])};
const fund={option:'Growth',metrics:{benchmark:{value:'Nifty Smallcap 250 TRI',as_of:'2026-01-02',
 source:'https://example.com/id',unit:'Reported'}},distribution_coverage:null};
process.stdout.write(JSON.stringify(a.response(fund,nav,{'Nifty Smallcap 250 TRI':bench},
 {start:'2025-01-02',end:'2026-01-02'})));
"""
        run=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True,check=True)
        result=json.loads(run.stdout)
        self.assertIsNotNone(result['comparison_stats']['fund']['1Y'])
        self.assertIsNone(result['comparison_stats']['fund']['3Y'])
        self.assertIsNone(result['comparison_stats']['benchmark']['3Y'])


if __name__=='__main__':
    unittest.main()
