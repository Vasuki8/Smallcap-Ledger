"""Regression checks for source identity, dates, units and preserved history."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
from tracker import db,disclosures,providers
from tracker.report_parser import page_facts
from tracker.portfolio_parser import parse_sheet
from tracker.structured_reports import extract,URLS,franklin_positions


class CoverageExpansionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,'DATA',Path(self.tmp.name));self.data_patch.start();db.init()
    def tearDown(self):
        self.data_patch.stop();self.tmp.cleanup()

    def test_abakkus_dedicated_details_page_not_another_fund(self):
        s='Abakkus Small Cap Fund Details\n₹2,794.20 Crores\nMonth End AUM\nPlans & Options\nRegular: 1.68%\nDirect: 0.51%\nBase Expense Ratio*\nSource: Internal. Data as on 31st August 2026.'
        facts=page_facts(s,'Abakkus Small Cap Fund')
        self.assertEqual([(f['metric'],f['value']) for f in facts],[('aum',2794.2),('base_expense_ratio',1.68),('base_expense_ratio',.51)])
        self.assertEqual({f['as_of'] for f in facts},{'2026-08-31'})
        self.assertEqual(page_facts(s.replace('Small Cap','Flexi Cap'),'Abakkus Small Cap Fund'),[])

    def test_boi_latest_and_average_distinct(self):
        f='Bank Of India Small Cap Fund'
        s=f+'\nAn open-ended equity scheme predominantly investing in small cap stocks\nAll data as on March 31, 2026\nAVERAGE AUM ` 1,823.40 Crs.\nLATEST AUM ` 1,770.44 Crs.'
        facts=page_facts(s,f)
        self.assertEqual({x['metric']:x['value'] for x in facts},{'aum':1770.44,'average_aum':1823.4})

    def test_aligned_pdf_columns_and_uti_expenses(self):
        from tracker.report_parser import layout_aum
        s='  AVERAGE AUM                         Other column\n  ` 2,706.77 Crs.\n  LATEST AUM\n  ` 2,819.49 Crs.'
        facts=layout_aum(s,'Bank Of India Small Cap Fund','2026-07-31')
        self.assertEqual([x['value'] for x in facts],[2706.77,2819.49])
        s='Fund Size Monthly Average : `          Crore5,271.45\nClosing AUM : `       Crore5,263.02'
        self.assertEqual([x['value'] for x in layout_aum(s,'UTI Small Cap Fund','2026-07-31')],[5271.45,5263.02])
        self.assertEqual(layout_aum(s,'UTI Small Cap Fund','2099-07-31'),[])
        s='UTI SMALL CAP FUND\nAn open ended equity scheme predominantly investing in Small cap stocks.\nPortfolio as on 31st July, 2026\nMonth-end Total Expense Ratio (%)*\nMinimum Investment Amount\nRegular : 2.00\nDirect : 0.86'
        self.assertEqual([(x['plan'],x['value']) for x in page_facts(s,'UTI Small Cap Fund')],[('Regular',2),('Direct',.86)])

    def test_sundaram_dates_are_not_interchangeable(self):
        f='Sundaram Small Cap Fund';u=URLS[f]
        row={'FUNDGROUP_ID':'SC','GROUP_NAME':f,'MONTHENDAUM':'3,922','AUM':'3,926','AUMASONDATE':'31-Jul-2026','REG_TOT_TER_DISP':'2.01 %','DP_TOT_TER_DISP':'0.97 %','TER_DATE_DISP':'07-Sep-2026','DIR_NAV_DT':'08-Sep-2026'}
        self.assertEqual(extract(json.dumps([row]),f,u,'hash'),4)
        rows=db.rows('SELECT metric,as_of,hash FROM metrics')
        self.assertEqual({r['as_of'] for r in rows if r['metric']=='ter'},{'2026-09-07'})
        self.assertEqual({r['as_of'] for r in rows if r['metric']=='aum'},{'2026-07-31'})
        self.assertTrue(all(r['hash']=='hash' for r in rows))
        row['GROUP_NAME']='Sundaram Mid Cap Fund'
        self.assertEqual(extract(json.dumps([row]),f,u,'bad'),0)

    def test_pgim_exact_heading_date_and_ambiguous_fee(self):
        f='Pgim India Small Cap Fund';u=URLS[f]
        html='<h1>PGIM India Small Cap Fund</h1><p>AUM as on 31 Aug 2026 ₹1,793.27 Cr</p><p>Expense Ratio (08 Sep 2026) 0.93%</p>'
        self.assertEqual(extract(html,f,u,'h'),1)
        self.assertEqual(db.one('SELECT metric,value,as_of FROM metrics'),{'metric':'aum','value':'1793.27','as_of':'2026-08-31'})
        self.assertIsNone(extract(html,f,u+'/wrong','h'))
        self.assertEqual(extract(html.replace('31 Aug 2026','31 Aug 2099'),f,u,'future'),0)

    def sheet(self):
        rows=[['Test Small Cap Fund'],['Portfolio as on 31 July 2026'],
          ['ISIN','Name of Instrument','Industry','Quantity','Market Value (Rs. in Lakhs)','% to Net Assets'],
          ['INE123456789','Alpha Ltd','Banks',100,9500,.95],
          ['', 'Sub Total','','',9500,.95],
          ['', 'TREPS','','',600,.06],
          ['', 'Net Receivable/Payable','','',-100,-.01],
          ['', 'Grand Total','','',10000,1]]
        formats=[['General']*len(r) for r in rows]
        for i in range(3,len(rows)):formats[i][5]='0.00%'
        return rows,formats

    def test_full_portfolio_cash_and_units_reconcile(self):
        rows,fmt=self.sheet();r=parse_sheet(rows,fmt,'Test Small Cap Fund')
        self.assertTrue(r['complete']);self.assertEqual(r['aum'],100)
        self.assertEqual([p['weight'] for p in r['positions']],[95,6,-1])
        self.assertEqual(r['positions'][1]['asset_type'],'Money market')
        self.assertEqual(disclosures.report_date('Monthly Portfolio Statement for the month ended 31 July2026'),'2026-07-31')

    def test_no_balancing_cash_or_unknown_aggregate(self):
        rows,fmt=self.sheet();rows[5][4]=500
        r=parse_sheet(rows,fmt,'Test Small Cap Fund');self.assertFalse(r['complete']);self.assertEqual(r['aum'],100)
        rows,fmt=self.sheet();rows[5][1]='Other undisclosed holdings'
        self.assertFalse(parse_sheet(rows,fmt,'Test Small Cap Fund')['complete'])
        rows[0]=['Test Nifty Smallcap 250 Index Fund']
        self.assertIsNone(parse_sheet(rows,fmt,'Test Small Cap Fund'))

    def test_missing_grand_total_does_not_establish_aum(self):
        rows,fmt=self.sheet();r=parse_sheet(rows[:-1],fmt[:-1],'Test Small Cap Fund')
        self.assertIsNone(r['aum']);self.assertFalse(r['complete'])

    def test_wealth_scheme_code_prefix_is_narrow(self):
        rows,fmt=self.sheet();rows[0]=['WCSC-THE WEALTH COMPANY SMALL CAP FUND']
        self.assertTrue(parse_sheet(rows,fmt,'The Wealth Company Small Cap Fund')['complete'])
        self.assertIsNone(parse_sheet(rows,fmt,'Test Small Cap Fund'))

    def test_franklin_full_table_retains_company_named_motherson(self):
        html='<table><tr><td>Company Name</td><td>No. of shares</td><td>Market Value Rs Lakhs</td><td>% of assets</td></tr><tr><td>Banks</td><td></td><td></td><td></td></tr><tr><td>Motherson Sumi Wiring India Ltd</td><td>100</td><td>90</td><td>90</td></tr><tr><td>Total Equity Holdings</td><td></td><td>90</td><td>90</td></tr><tr><td>Call,cash and other current asset</td><td></td><td>10</td><td>10</td></tr><tr><td>Total Asset</td><td></td><td>100</td><td>100</td></tr></table>'
        rows=franklin_positions(BeautifulSoup(html,'html.parser').table)
        self.assertEqual(len(rows),2);self.assertEqual(rows[1]['asset_type'],'Cash and net current assets')
        self.assertEqual(franklin_positions(BeautifulSoup(html.replace('Motherson Sumi Wiring India Ltd','Others'),'html.parser').table),[])

    def test_migration_preserves_partial_rows_and_references(self):
        with db.connect() as c:
            c.execute('DROP TABLE portfolios')
            c.execute('CREATE TABLE portfolios(id INTEGER PRIMARY KEY,family TEXT NOT NULL,as_of TEXT NOT NULL,complete INTEGER NOT NULL,source TEXT NOT NULL,hash TEXT NOT NULL,observed_at TEXT NOT NULL,UNIQUE(family,as_of,hash))')
            c.execute("INSERT INTO portfolios VALUES(7,'Test Small Cap Fund','2026-07-31',0,'source','hash','old')")
            c.execute("INSERT INTO holdings VALUES(9,7,'INE123456789','Alpha Ltd','Banks',95,'Equity')")
        old=db.rows('SELECT * FROM portfolios');hold=db.rows('SELECT * FROM holdings')
        db.init();db.init()
        sid=disclosures.portfolio('Test Small Cap Fund','2026-07-31',[{'name':'Alpha Ltd','weight':95},{'name':'Cash','weight':5}],True,'source','hash')
        self.assertNotEqual(sid,7)
        self.assertEqual(db.rows('SELECT * FROM portfolios WHERE id=7'),old)
        self.assertEqual(db.rows('SELECT * FROM holdings WHERE id=9'),hold)
        self.assertEqual(db.rows('PRAGMA foreign_key_check'),[])

    def test_json_transport_discovery_does_not_execute_code(self):
        row={'uploadDate':'2026-08-31','name':'Monthly - The Wealth Company Small Cap Fund','attachment':{'url':'/uploads/report.xlsx'}}
        frame=json.dumps([1,'prefix:'+json.dumps(row)])
        html='<script>self.__next_f.push('+frame+')</script>'
        links=providers.candidate_links(BeautifulSoup(html,'html.parser'),'https://www.wealthcompanyamc.in/literature-forms/')
        self.assertEqual(links,{'https://www.wealthcompanyamc.in/uploads/report.xlsx':row['name']})
        self.assertEqual(providers.classify('Abakkus Fund Spectrum','/uploads/report.pdf'),'factsheet')


if __name__=='__main__':unittest.main()
