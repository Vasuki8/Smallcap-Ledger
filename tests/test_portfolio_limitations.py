"""Portfolio limitation metadata is explicit, conservative, and non-numeric."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures, coverage
from tracker.portfolio_limits import retained_limitation


class PortfolioLimitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,'DATA',Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def add_scheme(self,code,family,amc):
        with db.connect() as c:
            c.execute(
                """INSERT INTO schemes(
                  code,name,family,amc,plan,option,category_source)
                  VALUES(?,?,?,?,?,?,?)""",
                (code,family+' Direct Growth',family,amc,'Direct','Growth','test'))

    def test_verified_partial_sources_have_canonical_codes(self):
        cases=[
            ('Axis Small Cap Fund',
             'https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct',
             'undisclosed_constituents'),
            ('ICICI Prudential Small Cap Fund',
             'https://www.icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf',
             'undisclosed_constituents'),
            ('Edelweiss Small Cap Fund',
             'https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026.pdf',
             'named_holdings_only'),
            ('Bajaj Finserv Small Cap Fund',
             'https://media.bajajamc.com/wp-content/uploads/2026/02/Bajaj-Finserv-Small-Cap-Fund_August-2026.pdf',
             'named_holdings_only'),
            ('Bandhan Small Cap Fund',
             'https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/bandhan-small-cap-fund-31-august-2026.xlsx',
             'non_numeric_weight'),
            ('Sundaram Small Cap Fund',
             'https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx',
             'non_numeric_weight'),
            ('UTI Small Cap Fund',
             'https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip?VersionId=test',
             'non_numeric_weight'),
        ]
        for family,source,code in cases:
            with self.subTest(family=family):
                limitation=retained_limitation(family,source,False)
                self.assertEqual(limitation['code'],code)
                self.assertTrue(limitation['detail'])
                self.assertIsNone(retained_limitation(family,source,True))

    def test_partial_snapshot_persists_and_api_exposes_limitation(self):
        family='Edelweiss Small Cap Fund'
        self.add_scheme(101,family,'Edelweiss Mutual Fund')
        source=('https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/'
                'FACTSHEETS/Edelweiss_Factsheet_September_2026.pdf')
        sid=disclosures.portfolio(
            family,'2026-08-31',[{'name':'Alpha Limited','weight':3.0}],
            False,source,'edel-hash')
        stored=db.one('SELECT limitation_code,limitation_detail FROM portfolios WHERE id=?',(sid,))
        self.assertEqual(stored['limitation_code'],'named_holdings_only')
        self.assertTrue(stored['limitation_detail'])

        from tracker.app import holdings,fund
        payload=holdings(sid)
        self.assertEqual(payload['limitation']['code'],'named_holdings_only')
        detail=fund(101)
        self.assertEqual(detail['portfolio_limitation']['code'],'named_holdings_only')
        self.assertEqual(detail['portfolios'][0]['limitation']['code'],'named_holdings_only')

    def test_complete_snapshot_has_no_partial_limitation(self):
        family='Complete Small Cap Fund'
        self.add_scheme(102,family,'Complete AMC')
        sid=disclosures.portfolio(
            family,'2026-08-31',[{'name':'Alpha Limited','weight':100.0}],
            True,'https://example.com/full.xlsx','complete-hash')
        row=db.one('SELECT limitation_code,limitation_detail FROM portfolios WHERE id=?',(sid,))
        self.assertEqual(row,{'limitation_code':None,'limitation_detail':None})
        from tracker.app import holdings
        self.assertIsNone(holdings(sid)['limitation'])
        with self.assertRaisesRegex(ValueError,'Complete portfolio'):
            disclosures.portfolio(
                family,'2026-07-31',[{'name':'Alpha Limited','weight':100.0}],
                True,'https://example.com/full-july.xlsx','complete-july',
                limitation_code='named_holdings_only',limitation_detail='not allowed')

    def test_unknown_partial_is_explicitly_unclassified(self):
        family='Unknown Partial Small Cap Fund'
        self.add_scheme(103,family,'Unknown AMC')
        sid=disclosures.portfolio(
            family,'2026-08-31',[{'name':'Alpha Limited','weight':10.0}],
            False,'https://example.com/top-holdings.pdf','unknown-partial')
        row=db.one('SELECT limitation_code FROM portfolios WHERE id=?',(sid,))
        self.assertEqual(row['limitation_code'],'partial_unclassified')

    def test_migration_backfills_existing_partial_snapshot(self):
        family='Sundaram Small Cap Fund'
        self.add_scheme(104,family,'Sundaram Mutual Fund')
        source='https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx'
        with db.connect() as c:
            c.execute("""INSERT INTO portfolios(
              family,as_of,complete,source,hash,limitation_code,limitation_detail,observed_at)
              VALUES(?,?,?,?,?,?,?,?)""",
              (family,'2026-08-31',0,source,'old-hash',None,None,db.now()))
        db.migrate_portfolio_limitations()
        row=db.one("SELECT limitation_code,limitation_detail FROM portfolios WHERE hash='old-hash'")
        self.assertEqual(row['limitation_code'],'non_numeric_weight')
        self.assertIn('less than 0.01%',row['limitation_detail'])

    def test_coverage_exposes_union_transport_limitation_without_snapshot(self):
        family='Union Small Cap Fund'
        self.add_scheme(105,family,'Union Mutual Fund')
        with db.connect() as c:
            c.execute("""INSERT INTO source_pages(
              amc_match,url,label,kind,enabled,last_checked,status,detail)
              VALUES(?,?,?,?,?,?,?,?)""",
              ('Union','https://www.unionmf.com/','Fund house','disclosure',1,
               db.now(),'Gap','[Errno 111] Connection refused'))
        row=next(x for x in coverage.report()['funds'] if x['family']==family)
        self.assertIsNone(row['portfolio'])
        self.assertEqual(row['portfolio_limitation']['code'],'upstream_transport_unavailable')
        self.assertIn('Connection refused',row['portfolio_limitation']['detail'])


if __name__=='__main__':
    unittest.main()
