"""Regression checks for source identity, dates, units and preserved history."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
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

    def test_pgim_pdf_allows_reconciled_page_when_generic_owner_order_is_reversed(self):
        from tracker import disclosures
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:'PGIM reversed-title fixture')
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        full={'day':'2026-07-31','positions':[
            {'name':'Example Holdings Limited','isin':None,'sector':'Test','weight':97.0,'asset_type':'Equity'},
            {'name':'Cash & Current Assets','isin':None,'sector':None,'weight':3.0,'asset_type':'Cash and net current assets'}]}
        with patch('pypdf.PdfReader',return_value=reader), \
             patch('tracker.report_parser.owns_page',return_value=False), \
             patch('tracker.report_parser.pgim_complete_portfolio',return_value=full):
            self.assertEqual(disclosures.factsheet_pdf(b'%PDF','Pgim India Small Cap Fund','https://www.pgimindia.com/test.pdf','hash'),2)
        self.assertEqual(db.one("SELECT complete FROM portfolios WHERE family='Pgim India Small Cap Fund'")['complete'],1)

    def test_pgim_complete_portfolio_reconciles_equity_debt_and_cash(self):
        from tracker.report_parser import pgim_complete_portfolio
        issuers='\n'.join([f'Example Holdings {i} Limited {97.26/20:.3f}' for i in range(1,21)])
        text=f'''Details as on July 31, 2026
Issuer % to Net Assets Rating
Aerospace & Defense 97.26
{issuers}
Equity Holdings Total 97.26
Government Bond And Treasury Bill 0.15
Treasury Bill 0.15
364 Days Tbill Red - 2026 0.15 SOVEREIGN
Cash & Current Assets 2.59
Total 100.00
SMALL CAP FUND
PGIM INDIA
Small Cap Fund - An open-ended equity scheme predominantly investing in small cap stocks'''
        r=pgim_complete_portfolio(text)
        self.assertIsNotNone(r)
        self.assertEqual(r['day'],'2026-07-31')
        self.assertEqual(r['positions'][-2]['asset_type'],'Debt')
        self.assertEqual(r['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertAlmostEqual(sum(x['weight'] for x in r['positions']),100,places=2)

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

    def test_reviewed_observation_has_no_fabricated_pdf_hash(self):
        from tracker import reviewed_reports
        r=reviewed_reports.reports()[0]
        with db.connect() as c:c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(1,?,?,?,?,?,?)',(r['family'],r['family'],r['amc'],'Direct','Growth','test'))
        reviewed_reports.apply();reviewed_reports.apply()
        fact=db.one("SELECT * FROM metrics WHERE metric='aum'")
        self.assertEqual(fact['as_of'],r['as_of']);self.assertEqual(fact['hash'],'')
        self.assertIn('Reviewed official report',reviewed_reports.annotate(fact)['source_note'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions')['n'],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM metrics WHERE metric='aum'")['n'],1)

    def test_baroda_monthly_average_cannot_become_month_end(self):
        f='Baroda Bnp Paribas Small Cap Fund';u='https://www.barodabnpparibasmf.in/efactsheet/Jul2026/Innerpages/Small-cap.html'
        html='<title>BBNPP Small Cap Fund</title><p>Monthly AAUM## As on July 31, 2026 : ₹ 1,278.20 Crores</p>'
        self.assertEqual(extract(html,f,u,'h'),1)
        self.assertEqual(db.one('SELECT metric FROM metrics')['metric'],'average_aum')
        self.assertEqual(extract(html.replace('Small Cap','Mid Cap'),f,u,'bad'),0)

    def test_canara_html_portfolio_reconciles_treps_and_cash(self):
        from tracker.amc_metrics import parse_page
        f='Canara Robeco Small Cap Fund'
        u='https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/SMALL-CAP.html'
        html='''<html><h2>CANARA ROBECO SMALL CAP FUND</h2><p>(as on August 31, 2026)</p>
        <p>Month end Assets Under Management (AUM) ₹ 14,475.59 Crores</p>
        <p>BENCHMARK Nifty Smallcap 250 Index TRI</p><table>
        <tr><th></th><th>Name of the Instruments/Issuer</th><th>Market Cap</th><th>% to NAV</th></tr>
        <tr><td></td><td>Equities</td><td></td><td>97.03%</td></tr>
        <tr><td></td><td>Banks</td><td></td><td>60.00%</td></tr>
        <tr><td></td><td>RBL Bank Ltd</td><td>S</td><td>60.00%</td></tr>
        <tr><td></td><td>Consumer Durables</td><td></td><td>37.03%</td></tr>
        <tr><td></td><td>Example Consumer Ltd</td><td>M</td><td>37.03%</td></tr>
        <tr><td></td><td>Money Market Instruments</td><td></td><td>2.88%</td></tr>
        <tr><td></td><td>TREPS</td><td></td><td>2.88%</td></tr>
        <tr><td></td><td>Net Current Assets</td><td></td><td>0.09%</td></tr>
        <tr><td></td><td>Grand Total ( Net Asset)</td><td></td><td>100.00%</td></tr></table></html>'''
        self.assertEqual(parse_page(html,f,u,'canara'),4)
        snap=db.one('SELECT as_of,complete FROM portfolios WHERE family=?',(f,))
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1})
        rows=db.rows('SELECT name,sector,weight,asset_type FROM holdings ORDER BY id')
        self.assertEqual([x['asset_type'] for x in rows],['Equity','Equity','Money market','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in rows),100)
        self.assertEqual(db.one("SELECT value FROM metrics WHERE metric='benchmark'")['value'],'Nifty Smallcap 250 Index TRI')

    def test_iti_html_portfolio_reconciles_derivatives_funds_and_cash(self):
        from tracker.amc_metrics import parse_page
        f='Iti Small Cap Fund';u='https://www.itiamc.com/digitalfactsheet/July2026/innerpages/Small-Cap.html'
        html='''<html><h1>ITI Small Cap Fund</h1><p>Portfolio Details AUM (in Rs. Cr): 3,454.00</p>
        <p>NAV as on July 31, 2026</p><table>
        <tr><th></th><th>Name of the Instrument</th><th>% to NAV</th><th>% to NAV Derivatives</th></tr>
        <tr><td></td><td>Equity &amp; Equity Related Total</td><td>95.65</td><td>2.11</td></tr>
        <tr><td></td><td>Consumer Durables</td><td>95.65</td><td>1.14</td></tr>
        <tr><td></td><td>Example Holdings Limited</td><td>95.65</td><td></td></tr>
        <tr><td></td><td>Example Derivative Limited</td><td></td><td>1.14</td></tr>
        <tr><td></td><td>Example Futures Limited</td><td></td><td>0.97</td></tr>
        <tr><td></td><td>Mutual Fund Units</td><td>0.27</td><td></td></tr>
        <tr><td></td><td>ITI Dynamic Bond Fund -Direct Plan -Growth Option</td><td>0.16</td><td></td></tr>
        <tr><td></td><td>ITI Banking &amp; PSU Debt Fund -Direct Plan -Growth Option</td><td>0.11</td><td></td></tr>
        <tr><td></td><td>Short Term Debt &amp; Net Current Assets</td><td>1.97</td><td></td></tr></table></html>'''
        self.assertEqual(parse_page(html,f,u,'iti'),7)
        snap=db.one('SELECT as_of,complete FROM portfolios WHERE family=?',(f,))
        self.assertEqual(snap,{'as_of':'2026-07-31','complete':1})
        rows=db.rows('SELECT name,asset_type,weight FROM holdings ORDER BY id')
        self.assertEqual([x['asset_type'] for x in rows],['Equity','Derivative','Derivative','Fund units','Fund units','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in rows),100)

    def test_mahindra_full_html_portfolio_reconciles(self):
        from tracker.amc_metrics import parse_page
        f='Mahindra Manulife Small Cap Fund'
        u='https://www.mahindramanulife.com/digital-factsheet/august-2026/Equity-funds/Small-Cap-Fund.html'
        html='''<html><h1>Mahindra Manulife Small Cap Fund</h1>
        <p>Monthly AUM as on August 31, 2026 (Rs. in Cr.): 5,100.00</p>
        <p>Base Expense Ratio as on August 31, 2026: Regular Plan: 1.50% Direct Plan: 0.47%</p>
        <p>Benchmark: BSE 250 Small Cap TRI</p>
        <table><tr><th></th><th>Company / Issuer</th><th>% of Net Assets</th></tr>
        <tr><td></td><td><b>Financial Services</b></td><td>60.00%</td></tr>
        <tr><td></td><td>State Bank of India</td><td>30.00%</td></tr>
        <tr><td></td><td>Example Finance Limited</td><td>30.00%</td></tr>
        <tr><td></td><td><b>Healthcare</b></td><td>35.00%</td></tr>
        <tr><td></td><td>Example Pharma Limited</td><td>35.00%</td></tr>
        <tr><td></td><td><b>Equity and Equity Related Total</b></td><td>95.00%</td></tr>
        <tr><td></td><td><b>Cash &amp; Other Receivables</b></td><td>5.00%</td></tr>
        <tr><td></td><td><b>Grand Total</b></td><td>100.00%</td></tr></table></html>'''
        self.assertEqual(parse_page(html,f,u,'mh'),5)
        snap=db.one('SELECT as_of,complete FROM portfolios WHERE family=?',(f,))
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1})
        hold=db.rows('SELECT name,sector,weight,asset_type FROM holdings ORDER BY id')
        self.assertEqual([x['name'] for x in hold],['State Bank of India','Example Finance Limited','Example Pharma Limited','Cash & Other Receivables'])
        self.assertEqual(hold[0]['sector'],'Financial Services')
        self.assertEqual(hold[-1]['asset_type'],'Cash and net current assets')
        self.assertEqual(db.one("SELECT value FROM metrics WHERE metric='benchmark'")['value'],'BSE 250 Small Cap TRI')

    def test_axis_dated_unqualified_expense_is_not_ter(self):
        from tracker.amc_metrics import parse_page
        f='Axis Small Cap Fund';u='https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct'
        html='<h1>Axis Small Cap Fund</h1><p>AUM (In Cr.) ₹ 31,448.32 As On Aug 31, 2026</p><p>Expense Ratio 0.71% As On Sep 05, 2026</p>'
        parse_page(html,f,u,'h')
        self.assertEqual(db.one("SELECT metric,plan,as_of FROM metrics WHERE metric!='aum'"),{'metric':'expense_ratio','plan':'Direct','as_of':'2026-09-05'})

    def test_baroda_treps_row_reconciles_complete_portfolio(self):
        rows=[
            [None,'Baroda BNP Paribas Small Cap Fund',None,None,None,None,None],
            [None,'Monthly Portfolio Statement as on August 31, 2026',None,None,None,None,None],
            [None,'Name of the Instrument','ISIN','Industry','Quantity','Market/Fair Value (Rs. in Lakhs)','% to Net Assets'],
            ['EQ01','Alpha Limited','INE123456789','Banks',100,9659,0.9659],
            [None,'Sub Total',None,None,None,9659,0.9659],
            [None,'Total',None,None,None,9659,0.9659],
            [None,'Reverse Repo / TREPS',None,None,None,None,None],
            ['TRP_010926','Clearing Corporation of India Ltd',None,' ',None,209,0.0209],
            [None,'Sub Total',None,None,None,209,0.0209],
            [None,'Total',None,None,None,209,0.0209],
            [None,'Net Receivables / (Payables)',None,None,None,132,0.0132],
            [None,'GRAND TOTAL',None,None,None,10000,1.0],
        ]
        fmt=[['General']*7 for _ in rows]
        for i in (3,4,5,7,8,9,10,11):fmt[i][6]='0.00%'
        parsed=parse_sheet(rows,fmt,'Baroda Bnp Paribas Small Cap Fund')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['aum'],100)
        self.assertEqual([x['asset_type'] for x in parsed['positions']],[
            'Equity','Money market','Cash and net current assets'])
        self.assertEqual(parsed['positions'][1]['name'],'Clearing Corporation of India Ltd')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100)

    def test_named_repo_is_limited_to_its_verified_scheme_layout(self):
        rows,fmt=self.sheet();rows[0]=['Motilal Oswal Small Cap Fund']
        rows[5]=['CBLO','TRP_030826','','',600,.06]
        rows.insert(5,['','Money Market Instruments','','','','']);fmt.insert(5,['General']*6)
        self.assertTrue(parse_sheet(rows,fmt,'Motilal Oswal Small Cap Fund')['complete'])
        rows[0]=['Test Small Cap Fund']
        self.assertFalse(parse_sheet(rows,fmt,'Test Small Cap Fund')['complete'])

    def test_uti_omnibus_scheme_boundary_and_small_weight_gap(self):
        from tracker.structured_reports import uti_rows
        rows=[['SCHEME: UTI Small Cap Fund'],['PROVISIONAL PORTFOLIO AS OF 31/08/2026 (Market value in Lacs)'],['NAME OF THE INSTRUMENT','INDUSTRY','QUANTITY','MARKET-VALUE','% TO NAV',None,None,'ISIN'],['EQ - Alpha Ltd','Banks',10,950,95,None,None,'INE123456789'],['EQ - Tiny Ltd','Banks',1,.001,'*',None,None,'INE123456788'],['TOTAL : UTI Small Cap Fund',None,None,1000]]
        r=uti_rows(rows);self.assertEqual(r['aum'],10);self.assertEqual(r['day'],'2026-08-31');self.assertEqual(len(r['positions']),1)
        rows[-1]=['SCHEME: UTI Mid Cap Fund']
        self.assertIsNone(uti_rows(rows))

    def test_unknown_nav_plan_does_not_inherit_direct_fee(self):
        from tracker.app import metrics_for,available_expenses
        db.metric('HSBC Small Cap Fund','Direct','base_expense_ratio','2026-07-31',.65,'% p.a.','official')
        s={'family':'HSBC Small Cap Fund','plan':'Unspecified'}
        self.assertNotIn('base_expense_ratio',metrics_for(s))
        self.assertEqual(available_expenses(s)[0]['plan'],'Direct')


if __name__=='__main__':unittest.main()
