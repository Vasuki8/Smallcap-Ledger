"""Core Indian reporting-date guard regressions."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tracker import db, providers
from tracker.app import app


class CoreIndiaDateTests(unittest.TestCase):
    def test_amfi_parser_uses_india_calendar_for_future_guard(self):
        text=(
            'Open Ended Schemes(Equity Scheme - Small Cap Fund)\n'
            'Test Mutual Fund\n'
            'Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n'
            '123;INF123456789;-;Test Small Cap Fund;Direct Plan;Growth;12.500;11-Sep-2026'
        )
        with patch('tracker.providers.india_today',return_value=date(2026,9,10)):
            self.assertEqual(providers.parse_amfi(text),[])
        with patch('tracker.providers.india_today',return_value=date(2026,9,11)):
            self.assertEqual(len(providers.parse_amfi(text)),1)

    def test_local_import_accepts_current_india_date(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            with db.connect() as c:
                c.execute(
                    'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                    (771,'Clock Small Cap Direct Growth','Clock Small Cap Fund','Clock AMC','Direct','Growth','test'))
            client=TestClient(app)
            csv=b'isin,name,sector,quantity,weight,asset_type\nINE000000001,Alpha,Banks,100,100,Equity\n'
            with patch('tracker.app.india_today',return_value=date(2026,9,11)):
                response=client.post(
                    '/api/import',
                    headers={'X-Smallcap-Client':'local'},
                    data={'kind':'portfolio','code':'771','source':'https://example.com/portfolio.csv',
                          'as_of':'2026-09-11','complete':'true'},
                    files={'file':('portfolio.csv',csv,'text/csv')},
                )
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(db.one("SELECT as_of FROM portfolios WHERE family='Clock Small Cap Fund'")['as_of'],'2026-09-11')


if __name__=='__main__':
    unittest.main()
