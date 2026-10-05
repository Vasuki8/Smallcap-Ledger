"""Portfolio change identity regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures
from tracker.app import holdings


class PortfolioHoldingIdentityTests(unittest.TestCase):
    def test_same_name_without_isin_stays_distinct_across_asset_classes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init()
            family='Identity Small Cap Fund'
            first=[
                {'name':'Alpha Instrument','isin':None,'sector':'Banks','weight':60,'quantity':100,'asset_type':'Equity'},
                {'name':'Alpha Instrument','isin':None,'sector':'Sovereign','weight':40,'quantity':200,'asset_type':'Debt'},
            ]
            second=[
                {'name':'Alpha Instrument','isin':None,'sector':'Banks','weight':55,'quantity':110,'asset_type':'Equity'},
                {'name':'Alpha Instrument','isin':None,'sector':'Sovereign','weight':45,'quantity':190,'asset_type':'Debt'},
            ]
            disclosures.portfolio(family,'2026-08-31',first,True,'https://example.com/aug','aug')
            sid=disclosures.portfolio(family,'2026-09-30',second,True,'https://example.com/sep','sep')
            result=holdings(sid)
            by_type={row['asset_type']:row for row in result['holdings']}
            self.assertEqual(by_type['Equity']['previous_weight'],60)
            self.assertEqual(by_type['Equity']['weight_change'],-5)
            self.assertEqual(by_type['Equity']['previous_quantity'],100)
            self.assertEqual(by_type['Equity']['share_change'],10)
            self.assertEqual(by_type['Debt']['previous_weight'],40)
            self.assertEqual(by_type['Debt']['weight_change'],5)
            self.assertEqual(by_type['Debt']['previous_quantity'],200)
            self.assertEqual(by_type['Debt']['share_change'],-10)


if __name__=='__main__':
    unittest.main()
