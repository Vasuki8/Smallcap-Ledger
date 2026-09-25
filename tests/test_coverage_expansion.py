"""Regression checks for source identity, dates, units and preserved history."""
import json
import sqlite3
import tempfile
import unittest
from datetime import date
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

    def test_franklin_html_preserves_equity_share_quantity(self):
        table=BeautifulSoup('''<table>
        <tr><th>Company Name</th><th>No. of shares</th><th>Market Value</th><th>% of assets</th></tr>
        <tr><td>Banks</td><td></td><td></td><td></td></tr>
        <tr><td>Alpha Limited</td><td>1,250</td><td>60</td><td>60</td></tr>
        <tr><td>Beta Limited</td><td>2,500</td><td>40</td><td>40</td></tr>
        <tr><td>Total Asset</td><td></td><td>100</td><td>100</td></tr>
        </table>''','html.parser').table
        positions=franklin_positions(table)
        self.assertEqual([x['quantity'] for x in positions],[1250,2500])

    def test_franklin_dated_page_retains_explicit_benchmark(self):
        f='Franklin India Small Cap Fund';u=URLS[f]
        html='''<html><table><tr><td><span>Franklin India Small Cap Fund</span> As on July 31, 2026</td></tr></table>
        <p>BENCHMARK: Nifty Smallcap 250</p></html>'''
        self.assertEqual(extract(html,f,u,'franklin-benchmark'),1)
        self.assertEqual(db.one("SELECT value,as_of,unit FROM metrics WHERE metric='benchmark'"),
                         {'value':'Nifty Smallcap 250','as_of':'2026-07-31','unit':'Reported'})

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

    def test_sundaram_censored_weight_stays_partial_but_keeps_all_numeric_rows(self):
        import io,openpyxl
        from tracker import disclosures
        wb=openpyxl.Workbook();ws=wb.active;ws.title='SMILE'
        rows=[
            ['SUNDARAM MUTUAL FUND','','','','','',''],
            ['','Sundaram Small Cap Fund','','','','',''],
            ['','Monthly Portfolio Statement for the month ended 31 August 2026','','','','',''],
            ['SL No','ISIN Code','Name of the instrument','Rating / Industry','Quantity','Mkt Value Rs. in Lacs','% of Net Asset'],
            [1,'INE123456789','Alpha Industries Ltd','Industrial Products',100,95000,95.0],
            [None,None,'(c) Privately Placed / Unlisted',None,None,None,None],
            [1,'INE551A01022','Hindustan Dorr Oliver Ltd @','Engineering Services',375961,0.000001,'#'],
            [None,None,'(d) ReverseRepo / TREPS',None,None,None,None],
            [1,None,'TREPS',None,None,5000,5.0],
            [None,None,'Margin Money For Derivatives',None,None,10,0.01],
            [None,None,'Cash and Other Net Current Assets',None,None,-10,-0.01],
            [None,None,'Grand Total',None,None,100000,100.0],
            [None,None,'# percentage to NAV of security is less than 0.01% - Wherever applicable',None,None,None,None],
            [None,None,'@ The Equity shares of Hindustan Dorr-Oliver Limited were delisted and written off.',None,None,None,None],
        ]
        for row in rows:ws.append(row)
        bio=io.BytesIO();wb.save(bio);wb.close()
        source='https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx'
        # Simulate the previously retained equity-only partial using the exact
        # same source hash; v126 must enrich it in place rather than duplicate it.
        disclosures.portfolio('Sundaram Small Cap Fund','2026-08-31',[
            {'name':'Alpha Industries Ltd','isin':'INE123456789','sector':'Industrial Products',
             'weight':95.0,'quantity':100,'asset_type':'Equity'}],
            False,source,'sundaram-censored')
        count=disclosures.spreadsheet(
            bio.getvalue(),'Sundaram Small Cap Fund',source,'sundaram-censored')
        self.assertEqual(count,4)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions,SUM(h.weight) weight
          FROM portfolios p JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family='Sundaram Small Cap Fund' GROUP BY p.id""")
        self.assertEqual(snap['as_of'],'2026-08-31')
        self.assertEqual(snap['complete'],0)
        self.assertEqual(snap['positions'],4)
        self.assertAlmostEqual(snap['weight'],100.0,places=6)
        self.assertIsNone(db.one("""SELECT h.id FROM holdings h JOIN portfolios p ON p.id=h.snapshot_id
          WHERE p.family='Sundaram Small Cap Fund' AND h.name='Hindustan Dorr Oliver Ltd @'"""))
        metric=db.one("""SELECT value,as_of FROM metrics
          WHERE family='Sundaram Small Cap Fund' AND metric='aum'""")
        self.assertEqual(metric,{'value':'1000.0','as_of':'2026-08-31'})

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

    def test_pdf_parser_persists_validated_benchmark_without_generic_page_owner(self):
        from tracker import disclosures
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:'LIC parser benchmark fixture')
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        parsed={'day':'2026-07-31','benchmark':'Nifty Smallcap 250 - TRI','positions':[
            {'name':'Example Holdings Limited','isin':None,'sector':'Test','weight':95.0,'asset_type':'Equity'},
            {'name':'Cash & Other Receivables','isin':None,'sector':None,'weight':5.0,'asset_type':'Cash and net current assets'}]}
        with patch('pypdf.PdfReader',return_value=reader), \
             patch('tracker.report_parser.owns_page',return_value=False), \
             patch('tracker.report_parser.lic_complete_portfolio',return_value=parsed):
            count=disclosures.factsheet_pdf(b'%PDF','LIC Mf Small Cap Fund',
                                            'https://www.licmf.com/factsheet.pdf','lic-benchmark')
        self.assertEqual(count,3)
        self.assertEqual(db.one("SELECT value,as_of,source,hash FROM metrics WHERE metric='benchmark'"),
                         {'value':'Nifty Smallcap 250 - TRI','as_of':'2026-07-31',
                          'source':'https://www.licmf.com/factsheet.pdf','hash':'lic-benchmark'})

    def test_lic_august_layout_reconciles_without_scheme_name_prefix(self):
        from tracker.report_parser import lic_complete_portfolio
        holdings=[]
        for sector in range(2):
            holdings.append(f'Sector {sector+1} 45.00%')
            for issuer in range(10):
                holdings.append(f'Company {sector+1}-{issuer+1} Ltd. 4.50%')
        text='''Scheme Type: An open-ended equity scheme predominantly investing in small cap stocks
Inception/Allotment Date: June 21, 2017
First Tier Benchmark: Nifty Smallcap 250 - TRI
PORTFOLIO as on 31/08/2026
Company % of NAV
Equity Holdings
'''+ '\n'.join(holdings) + '''
Equity Holdings Total 90.00%
Cash & Other Receivables Total 10.00%
Grand Total 100.00% Top 10 holdings'''
        parsed=lic_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual(len(parsed['positions']),21)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertIsNone(lic_complete_portfolio(text.replace(
            'predominantly investing in small cap stocks','predominantly investing in mid cap stocks',1)))
        self.assertIsNone(lic_complete_portfolio(text.replace('Grand Total 100.00%','Grand Total 99.00%',1)))

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
        html='<h1>PGIM India Small Cap Fund</h1><p>AUM as on 31 Aug 2026 ₹1,793.27 Cr</p><p>Benchmark Nifty Smallcap 250 - TRI</p><p>Expense Ratio (08 Sep 2026) 0.93%</p>'
        self.assertEqual(extract(html,f,u,'h'),2)
        facts={r['metric']:dict(r) for r in db.rows('SELECT metric,value,as_of,unit FROM metrics')}
        self.assertEqual(facts['aum'],{'metric':'aum','value':'1793.27','as_of':'2026-08-31','unit':'INR crore'})
        self.assertEqual(facts['benchmark'],{'metric':'benchmark','value':'Nifty Smallcap 250 - TRI','as_of':'2026-08-31','unit':'Reported'})
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

    def test_absl_derivative_margin_row_is_reconciled_as_cash_asset(self):
        rows,fmt=self.sheet()
        rows[0]=['Aditya Birla Sun Life Small Cap Fund']
        rows[3]=['INE123456789','Alpha Ltd','Banks',100,9500,.95]
        rows[5]=['','TREPS','','',200,.02]
        rows.insert(6,['','Margin amount for Derivative positions','','',200,.02]);fmt.insert(6,['General']*6)
        fmt[6][5]='0.00%'
        rows[7]=['','Net Current Assets','','',100,.01]
        rows[8]=['','Grand Total','','',10000,1]
        parsed=parse_sheet(rows,fmt,'Aditya Birla Sun Life Small Cap Fund')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        margin=next(x for x in parsed['positions'] if x['name']=='Margin amount for Derivative positions')
        self.assertEqual(margin['asset_type'],'Cash and net current assets')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)

    def test_dsp_repo_and_cash_margin_rows_can_reconcile_complete_workbook(self):
        rows,fmt=self.sheet()
        rows[0]=['DSP Small Cap Fund']
        rows[3]=['INE123456789','Alpha Ltd','Banks',100,8743,.8743]
        rows[5]=['','TREPS / Reverse Repo Investments','','',1000,.10]
        rows.insert(6,['','Cash Margin','','',257,.0257]);fmt.insert(6,['General']*6)
        fmt[6][5]='0.00%'
        rows[7]=['','Grand Total','','',10000,1.0]
        parsed=parse_sheet(rows,fmt,'DSP Small Cap Fund')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        self.assertEqual([x['asset_type'] for x in parsed['positions']],[
            'Equity','Money market','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)

    def test_quant_derivative_expiry_and_nca_rows_reconcile(self):
        rows=[
            [None,None,'Quant Small Cap Fund',None,None,None,None,None],
            [None,None,'Monthly Portfolio as on 31 August 2026',None,None,None,None,None],
            ['SR','ISIN','NAME OF THE INSTRUMENT','RATING','INDUSTRY','QUANTITY','MARKET VALUE(Rs.in Lakhs)','% to NAV'],
            [1,'INE123456789','Alpha Limited','N.A.','Banks',100,9000,.90],
            [None,'','DERIVATIVES','','','','',''],
            [None,'','(a) Index / Stock Futures','','','','',''],
            [105,'KPITTECH290926','KPIT Technologies Limited 29/09/2026','N.A.','IT - Software',-10,-50,-.005],
            [120,'','NCA-NET CURRENT ASSETS','N.A.','N.A.','',1050,.105],
            [None,'','Grand Total','','','',10000,1.0],
        ]
        fmt=[['General']*8 for _ in rows]
        for i in (3,6,7,8):fmt[i][7]='0.00%'
        parsed=parse_sheet(rows,fmt,'Quant Small Cap Fund')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        deriv=next(x for x in parsed['positions'] if x['name'].startswith('KPIT Technologies'))
        self.assertEqual(deriv['asset_type'],'Derivative')
        self.assertEqual(deriv['isin'],None)
        cash=next(x for x in parsed['positions'] if x['name']=='NCA-NET CURRENT ASSETS')
        self.assertEqual(cash['asset_type'],'Cash and net current assets')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        rows[6][1]='KPITTECH'
        self.assertFalse(parse_sheet(rows,fmt,'Quant Small Cap Fund')['complete'])

    def test_missing_grand_total_does_not_establish_aum(self):
        rows,fmt=self.sheet();r=parse_sheet(rows[:-1],fmt[:-1],'Test Small Cap Fund')
        self.assertIsNone(r['aum']);self.assertFalse(r['complete'])

    def test_wealth_scheme_code_prefix_is_narrow(self):
        rows,fmt=self.sheet();rows[0]=['WCSC-THE WEALTH COMPANY SMALL CAP FUND']
        self.assertTrue(parse_sheet(rows,fmt,'The Wealth Company Small Cap Fund')['complete'])
        self.assertIsNone(parse_sheet(rows,fmt,'Test Small Cap Fund'))

    def test_franklin_august_five_column_debt_and_margin_reconciles(self):
        from tracker.structured_reports import franklin_positions
        table=BeautifulSoup('''<table>
        <tr><td>Company Name</td><td>No. of shares</td><td>Market Value Rs Lakhs</td><td>% of assets</td></tr>
        <tr><td>Banks</td><td></td><td></td><td></td><td></td></tr>
        <tr><td>Alpha Limited</td><td>100</td><td>9696</td><td>96.96</td><td>-0.63</td></tr>
        <tr><td>Total Equity Holdings</td><td></td><td>9696</td><td>96.96</td><td>-0.63</td></tr>
        <tr><td>Company Name</td><td></td><td>Company Ratings</td><td>Market Value (including accrued interest, if any) (Rs. in Lakhs)</td><td>% of Assets</td></tr>
        <tr><td>182 DTB (19-NOV-2026)</td><td></td><td>SOVEREIGN</td><td>17</td><td>0.17</td></tr>
        <tr><td>Total Debt Holdings</td><td></td><td></td><td>17</td><td>0.17</td></tr>
        <tr><td>Total Holdings</td><td></td><td></td><td>9713</td><td>97.13</td></tr>
        <tr><td>Margin on Derivatives</td><td></td><td></td><td>21</td><td>0.21</td></tr>
        <tr><td>Call,cash and other current asset</td><td></td><td></td><td>266</td><td>2.66</td></tr>
        <tr><td>Total Asset</td><td></td><td></td><td>10000</td><td>100.00</td></tr>
        <tr><td></td><td>* Top 10 holdings</td></tr>
        </table>''','html.parser').table
        rows=franklin_positions(table)
        self.assertEqual(len(rows),4)
        self.assertEqual([x['asset_type'] for x in rows],[
            'Equity','Debt','Cash and net current assets','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in rows),100,places=2)
        self.assertEqual(rows[0]['quantity'],100)
        broken=BeautifulSoup(str(table).replace('2.66','2.56'),'html.parser').table
        self.assertEqual(franklin_positions(broken),[])

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
            c.execute("""INSERT INTO holdings(id,snapshot_id,isin,name,sector,weight,quantity,asset_type)
              VALUES(9,7,'INE123456789','Alpha Ltd','Banks',95,NULL,'Equity')""")
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

    def test_reviewed_benchmark_identity_has_source_note_without_fake_hash(self):
        from tracker import reviewed_reports
        r=next(x for x in reviewed_reports.reports()
               if any(f['metric']=='benchmark' for f in x['facts']))
        with db.connect() as conn:
            conn.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(1,?,?,?,?,?,?)',
                         (r['family'],r['family'],r['amc'],'Direct','Growth','test'))
        reviewed_reports.apply();reviewed_reports.apply()
        fact=db.one("SELECT * FROM metrics WHERE family=? AND metric='benchmark'",(r['family'],))
        expected=next(x for x in r['facts'] if x['metric']=='benchmark')
        self.assertEqual(fact['value'],expected['value'])
        self.assertEqual(fact['as_of'],r['as_of'])
        self.assertEqual(fact['hash'],'')
        annotated=reviewed_reports.annotate(fact)
        self.assertIn('Reviewed official report',annotated['source_note'])
        self.assertEqual(annotated['reviewed_at'],r['reviewed_at'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions')['n'],0)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM metrics WHERE metric='benchmark'")['n'],1)

    def test_baroda_monthly_average_cannot_become_month_end(self):
        f='Baroda Bnp Paribas Small Cap Fund';u='https://www.barodabnpparibasmf.in/efactsheet/Jul2026/Innerpages/Small-cap.html'
        html='<title>BBNPP Small Cap Fund</title><p>Monthly AAUM## As on July 31, 2026 : ₹ 1,278.20 Crores</p><p>Benchmark Index (AMFI Tier 1) Nifty Small Cap 250 TRI</p>'
        self.assertEqual(extract(html,f,u,'h'),2)
        facts={r['metric']:dict(r) for r in db.rows('SELECT metric,value,as_of FROM metrics')}
        self.assertEqual(facts['average_aum']['as_of'],'2026-07-31')
        self.assertEqual(facts['benchmark'],{'metric':'benchmark','value':'Nifty Smallcap 250 TRI','as_of':'2026-07-31'})
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
        self.assertEqual(parse_page(html,f,u,'canara'),5)
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

    def test_pgim_ccil_money_market_row_reconciles_complete_workbook(self):
        rows=[
            ['PGIM INDIA SMALL CAP FUND'],['Monthly Portfolio as on 31 August 2026'],
            ['','Name of Instrument','ISIN','Industry/Rating','Quantity','Market/Fair Value (INR Lacs)','% to Net Assets'],
            ['', 'Alpha Limited','INE123456789','Banks',100,34800.00,19.40],
            ['', 'Beta Limited','INE123456788','Banks',100,34800.00,19.40],
            ['', 'Gamma Limited','INE123456787','Banks',100,34800.00,19.40],
            ['', 'Delta Limited','INE123456786','Banks',100,34800.00,19.40],
            ['', 'Epsilon Limited','INE123456785','Banks',100,35511.89,19.83],
            ['', 'Sub Total','','','',174711.89,97.43],
            ['', 'Government Securities','','','','',''],
            ['', '91 Days Tbill','IN002026X123','SOVEREIGN',100,247.97,0.14],
            ['', 'Sub Total','','','',247.97,0.14],
            ['', 'Money Market Instruments','','','','',''],
            ['', 'Clearing Corporation of India Ltd.','','','',6794.77,3.79],
            ['', 'Sub Total','','','',6794.77,3.79],
            ['', 'Net Receivables / (Payables)','','','',-2375.38,-1.36],
            ['', 'GRAND TOTAL','','','',179131.28,100.0],
        ]
        # Keep the synthetic market values internally reconciled to the published
        # percentage layout; the real workbook is additionally validated in production.
        rows[-1][5]=179379.25
        fmt=[['General']*7 for _ in rows]
        parsed=parse_sheet(rows,fmt,'Pgim India Small Cap Fund')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        repo=next(x for x in parsed['positions'] if x['name']=='Clearing Corporation of India Ltd.')
        self.assertEqual(repo['asset_type'],'Money market')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        rows[0]=['Test Small Cap Fund']
        self.assertFalse(parse_sheet(rows,fmt,'Test Small Cap Fund')['complete'])

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




    def test_bajaj_factsheet_reconciles_complete_portfolio(self):
        from tracker.report_parser import bajaj_complete_portfolio
        text='''Bajaj Finserv Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
PORTFOLIO (as on 31 August, 2026)
NAV as on 31 August, 2026
TOTAL EXPENSE RATIO (TER)
Regular Plan 2.10%
Direct Plan 0.44%
12.77%
87.23%
Alpha Industries Limited 50.00%
Beta Bank Limited 37.23%
Equities 87.23%
Reverse Repo / TREPS 10.50%
Cash & Cash Equivalent 2.27%
Grand Total 100.00%
Stock % of NAV Stock % of NAV
Industrial Products 50.00%
Banks 37.23%
Scheme Category: Small Cap Fund'''
        parsed=bajaj_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual([x['name'] for x in parsed['positions']],[
            'Alpha Industries Limited','Beta Bank Limited','Reverse Repo / TREPS','Cash & Cash Equivalent'])
        self.assertEqual([x['asset_type'] for x in parsed['positions']],[
            'Equity','Equity','Money market','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertIsNone(bajaj_complete_portfolio(text.replace('Small Cap Fund','Large Cap Fund',1)))
        self.assertIsNone(bajaj_complete_portfolio(text.replace('Grand Total 100.00%','Grand Total 99.00%')))

    def test_bajaj_top10_factsheet_preserves_other_equities_as_partial(self):
        from tracker.report_parser import bajaj_top10_portfolio
        summary='''Bajaj Finserv Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
Inception Date:
18th July 2025
Benchmark:
BSE 250 SmallCap TRI
Data as on 31st July 2026'''
        holdings='''Asset Allocation
Net Equities
Reverse Repo / TREPS & Net Current Assets
Equity Options
98.28%
1.68%
0.04%
Equity Holding
Name (Top 10 Holdings) (% to NAV)
Rubicon Research Limited
S.J.S. Enterprises Limited
Zydus Wellness Limited
Neuland Laboratories Limited
Welspun Corp Limited
Schaeffler India Limited
The Federal Bank Limited
Angel One Limited
Timken India Limited
Piramal Pharma Limited
Other Equities
Total Equities
4.09%
3.21%
3.02%
2.97%
2.71%
2.70%
2.50%
2.40%
2.38%
2.06%
70.24%
98.28%'''
        parsed=bajaj_top10_portfolio(summary,holdings)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-07-31')
        self.assertEqual(len(parsed['positions']),13)
        self.assertEqual(parsed['positions'][10]['name'],'Other Equities (AMC aggregate)')
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Derivative')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertIsNone(bajaj_top10_portfolio(summary,holdings.replace('70.24%','69.24%')))

    def test_bajaj_top10_factsheet_saves_partial_snapshot(self):
        from tracker import disclosures
        summary='''Bajaj Finserv Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
Inception Date: 18th July 2025
Benchmark: BSE 250 SmallCap TRI
Data as on 31st July 2026'''
        holdings='''Asset Allocation
Net Equities
Reverse Repo / TREPS & Net Current Assets
Equity Options
98.28%
1.68%
0.04%
Equity Holding
Name (Top 10 Holdings) (% to NAV)
Rubicon Research Limited
S.J.S. Enterprises Limited
Zydus Wellness Limited
Neuland Laboratories Limited
Welspun Corp Limited
Schaeffler India Limited
The Federal Bank Limited
Angel One Limited
Timken India Limited
Piramal Pharma Limited
Other Equities
Total Equities
4.09%
3.21%
3.02%
2.97%
2.71%
2.70%
2.50%
2.40%
2.38%
2.06%
70.24%
98.28%'''
        pages=[SimpleNamespace(extract_text=lambda *args,**kwargs:summary),
               SimpleNamespace(extract_text=lambda *args,**kwargs:holdings)]
        reader=SimpleNamespace(is_encrypted=False,pages=pages)
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Bajaj Finserv Small Cap Fund',
                                            'https://media.bajajamc.com/factsheet.pdf','bajaj-top10')
        self.assertGreaterEqual(count,13)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Bajaj Finserv Small Cap Fund' AND hash='bajaj-top10'")
        self.assertEqual(snap,{'as_of':'2026-07-31','complete':0})

    def test_jm_official_page_saves_dated_partial_holdings_and_benchmark(self):
        from tracker.amc_metrics import parse_page
        html=b'''<html><body><h1>JM Small Cap Fund</h1>
        <div>Benchmark Index Nifty Smallcap 250 TRI</div>
        <div>As on - 31st Aug, 2026</div>
        <h3>Holdings</h3>
        <div>Garware Hi-Tech Films Limited 4.60%</div>
        <div>Navin Fluorine International Limited 3.20%</div>
        <div>Acutaas Chemicals Limited 2.90%</div>
        <div>Five-Star Business Finance Limited 2.80%</div>
        <div>Fusion Finance Limited 2.70%</div>
        <button>See All Holdings</button>
        <div>Portfolio As on - 31st Aug, 2026 Current Allocation Equity 98.39 % Debt/Cash 1.61 %</div>
        </body></html>'''
        url='https://www.jmfinancialmf.com/products/Equity/JM-Small-Cap-Fund/J647/Direct-Plan-Growth-Option'
        saved=parse_page(html,'Jm Small Cap Fund',url,'jm-page')
        self.assertEqual(saved,5)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Jm Small Cap Fund' AND hash='jm-page'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0})
        bench=db.one("SELECT value,as_of FROM metrics WHERE family='Jm Small Cap Fund' AND metric='benchmark' AND hash='jm-page'")
        self.assertEqual(bench,{'value':'Nifty Smallcap 250 TRI','as_of':'2026-08-31'})

    def test_boi_official_page_accepts_flattened_top_holdings_without_heading_tag(self):
        from tracker.amc_metrics import parse_page
        html=b'''<html><head><title>BOI Mutual Fund</title></head><body>
        <div>Bank Of India SMALL CAP FUND</div>
        <div>An open ended equity scheme predominantly investing in small cap stocks</div>
        <div>The above Riskometer is based on the portfolio as on 30th June, 2026.</div>
        <div>Benchmark Riskometer : NIFTY Smallcap 250 Total Return Index(TRI)(Tier 1)</div>
        <section>Top 10 Portfolio Holdings Portfolio Details % to Net Assets
        TREPS / Reverse Repo Investments 6.2%
        Sky Gold And Diamonds Limited 2.8%
        City Union Bank Limited 2.5%
        Wockhardt Limited 2.4%
        Quality Power Electrical Eqp Ltd 2.3%
        Computer Age Management Services Limited 2.1%
        Arvind Limited 2.0%
        Shreeji Shipping Global Limited 2.0%
        Sterlite Technologies Limited 2.0%
        PG Electroplast Limited 1.9%
        Sector Allocation Data Not Available</section>
        </body></html>'''
        url='https://www.boimf.in/products/equity-funds/bank-of-india-small-cap-fund'
        saved=parse_page(html,'Bank Of India Small Cap Fund',url,'boi-flat')
        self.assertEqual(saved,10)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE hash='boi-flat'")
        self.assertEqual(snap,{'as_of':'2026-06-30','complete':0})
        types=db.rows("SELECT asset_type FROM holdings WHERE snapshot_id=(SELECT id FROM portfolios WHERE hash='boi-flat') ORDER BY id")
        self.assertEqual(types[0]['asset_type'],'Money market')

    def test_boi_official_fund_page_saves_dated_partial_top_holdings_and_benchmark(self):
        from tracker.amc_metrics import parse_page
        html=b'''<html><head><title>Bank of India Small Cap Fund</title></head><body>
        <h1>Bank of India Small Cap Fund</h1>
        <div>The above Riskometer is based on the scheme portfolio as on 30th June, 2026.</div>
        <div>Benchmark Riskometer : NIFTY Smallcap 250 TRI (Tier 1)</div>
        <h2>Top 10 Portfolio Holdings</h2>
        <table><tr><th>Portfolio Details</th><th>% to Net Assets</th></tr>
        <tr><td>TREPS / Reverse Repo Investments</td><td>6.2%</td></tr>
        <tr><td>Sky Gold And Diamonds Limited</td><td>2.8%</td></tr>
        <tr><td>City Union Bank Limited</td><td>2.5%</td></tr>
        <tr><td>Wockhardt Limited</td><td>2.4%</td></tr>
        <tr><td>Quality Power Electrical Eqp Ltd</td><td>2.3%</td></tr>
        <tr><td>Computer Age Management Services Limited</td><td>2.1%</td></tr>
        <tr><td>Arvind Limited</td><td>2.0%</td></tr>
        <tr><td>Shreeji Shipping Global Limited</td><td>2.0%</td></tr>
        <tr><td>Sterlite Technologies Limited</td><td>2.0%</td></tr>
        <tr><td>PG Electroplast Limited</td><td>1.9%</td></tr></table>
        </body></html>'''
        url='https://www.boimf.in/products/equity-funds/bank-of-india-small-cap-fund'
        saved=parse_page(html,'Bank Of India Small Cap Fund',url,'boi-page')
        self.assertEqual(saved,10)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Bank Of India Small Cap Fund' AND hash='boi-page'")
        self.assertEqual(snap,{'as_of':'2026-06-30','complete':0})
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings WHERE snapshot_id=(SELECT id FROM portfolios WHERE hash='boi-page')")['n'],10)
        bench=db.one("SELECT value,as_of FROM metrics WHERE family='Bank Of India Small Cap Fund' AND metric='benchmark' AND hash='boi-page'")
        self.assertEqual(bench,{'value':'NIFTY Smallcap 250 TRI','as_of':'2026-06-30'})

    def test_absl_complete_portfolio_reconciles_sector_totals_and_cash(self):
        from tracker.report_parser import absl_complete_portfolio
        lines=[
            'Aditya Birla Sun Life Small Cap Fund',
            'An open ended equity scheme predominantly investing in small cap stocks.',
            'Portfolio Holdings as on July 31, 2026',
            'Sector/Issuer Name % of Net AUM',
            'Equity & Equity Related',
        ]
        # Five sectors, eight securities each: 80% equity + 20% cash = 100%.
        for sector in range(5):
            lines.append(f'Sector {sector+1} 16.00 %')
            for holding in range(8):
                lines.append(f'Company {sector+1}-{holding+1} Ltd. 2.00 %')
        lines += ['Net Cash and Cash Equivalent 20.00 %','Grand Total 100.00 %']
        text='\n'.join(lines)
        parsed=absl_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-07-31')
        self.assertEqual(len(parsed['positions']),41)
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertIsNone(absl_complete_portfolio(text.replace('Sector 2 16.00 %','Sector 2 15.00 %')))

    def test_absl_factsheet_saves_reconciled_portfolio_as_complete(self):
        from tracker import disclosures
        lines=[
            'Aditya Birla Sun Life Small Cap Fund',
            'An open ended equity scheme predominantly investing in small cap stocks.',
            'Portfolio Holdings as on July 31, 2026',
            'Sector/Issuer Name % of Net AUM',
            'Equity & Equity Related',
        ]
        for sector in range(5):
            lines.append(f'Sector {sector+1} 16.00 %')
            for holding in range(8):
                lines.append(f'Company {sector+1}-{holding+1} Ltd. 2.00 %')
        lines += ['Net Cash and Cash Equivalent 20.00 %','Grand Total 100.00 %']
        text='\n'.join(lines)
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:text)
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Aditya Birla Sun Life Small Cap Fund',
                                            'https://mutualfund.adityabirlacapital.com/absl.pdf','absl-full')
        self.assertEqual(count,41)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Aditya Birla Sun Life Small Cap Fund' AND hash='absl-full'")
        self.assertEqual(snap,{'as_of':'2026-07-31','complete':1})

    def test_icici_partial_portfolio_reconciles_named_rows_and_disclosed_gap(self):
        from tracker.report_parser import icici_named_portfolio
        first=['ICICI Prudential Small Cap Fund',
               '(An open ended equity scheme predominantly investing in small cap stocks.)',
               'Date of inception:18-Oct-07.',
               'Nifty Smallcap 250 TRI (Benchmark)',
               'Portfolio as on August 31, 2026',
               'Equity Shares 97.50%']
        for sector in range(20):
            first.append(f'Sector {sector+1} 4.50%')
            for holding in range(3):
                name=('Issuer Without Suffix' if sector==2 and holding==2
                      else f'Company {sector+1}-{holding+1} Ltd')
                first.append(f'{name} 1.50%')
        second=['Small Cap Fund','Category','Portfolio as on August 31, 2026',
                'Company/Issuer Rating % to','NAV',
                'Equity less than 1% of corpus 7.50%',
                'Short Term Debt and net current assets 2.50%',
                'Total Net Assets 100.00%']
        parsed=icici_named_portfolio('\n'.join(first),'\n'.join(second))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual(len(parsed['positions']),60)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),90.0,places=2)
        self.assertTrue(any(x['name']=='Issuer Without Suffix' for x in parsed['positions']))
        self.assertIsNone(icici_named_portfolio(
            '\n'.join(first),'\n'.join(second).replace('7.50%','6.50%',1)))

    def test_icici_two_page_factsheet_saves_partial_and_benchmark(self):
        from tracker import disclosures
        first=['ICICI Prudential Small Cap Fund',
               '(An open ended equity scheme predominantly investing in small cap stocks.)',
               'Date of inception:18-Oct-07.',
               'Nifty Smallcap 250 TRI (Benchmark)',
               'Portfolio as on August 31, 2026',
               'Equity Shares 97.50%']
        for sector in range(20):
            first.append(f'Sector {sector+1} 4.50%')
            for holding in range(3):
                first.append(f'Company {sector+1}-{holding+1} Ltd 1.50%')
        second=['Small Cap Fund','Category','Portfolio as on August 31, 2026',
                'Company/Issuer Rating % to','NAV',
                'Equity less than 1% of corpus 7.50%',
                'Short Term Debt and net current assets 2.50%',
                'Total Net Assets 100.00%']
        pages=[SimpleNamespace(extract_text=lambda *args,**kwargs:'\n'.join(first)),
               SimpleNamespace(extract_text=lambda *args,**kwargs:'\n'.join(second))]
        reader=SimpleNamespace(is_encrypted=False,pages=pages)
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(
                b'%PDF','ICICI Prudential Small Cap Fund',
                'https://www.icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf',
                'icici-partial')
        self.assertGreaterEqual(count,60)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='ICICI Prudential Small Cap Fund' AND hash='icici-partial'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0})
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings WHERE snapshot_id=(SELECT id FROM portfolios WHERE hash='icici-partial')")['n'],60)
        benchmark=db.one("SELECT value,as_of FROM metrics WHERE family='ICICI Prudential Small Cap Fund' AND metric='benchmark' AND hash='icici-partial'")
        self.assertEqual(benchmark,{'value':'Nifty Smallcap 250 TRI','as_of':'2026-08-31'})

    def test_jm_top25_reconciles_both_real_pdf_orders(self):
        from tracker.report_parser import jm_top25_portfolio
        rows=[f'Company {i} Limited 2.00' for i in range(1,25)]
        rows.insert(14,'Jammu & Kashmir Bank 2.00')
        table='\n'.join(rows)
        base='''Jm Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
INCEPTION DATE 18th June, 2024
Details as on August 31, 2026
'''
        totals='''Other Equity Stocks 49.00
Total Equity Holdings 99.00
TREPS & Others * 1.00
Total Assets 100.00
'''
        heading='SCHEME PORTFOLIO (TOP 25 STOCKS)\n'
        header='Name of Instrument % to NAV\n'
        before=base+heading+header+table+'\n'+totals
        after=base+header+table+'\n'+totals+heading
        for text in (before,after):
            parsed=jm_top25_portfolio(text)
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed['day'],'2026-08-31')
            self.assertEqual(len(parsed['positions']),25)
            self.assertEqual(parsed['positions'][14]['name'],'Jammu & Kashmir Bank')
            self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),50.0,places=2)
        self.assertIsNone(jm_top25_portfolio(before.replace('Other Equity Stocks 49.00','Other Equity Stocks 48.00')))

    def test_jm_factsheet_saves_top25_as_partial_only(self):
        from tracker import disclosures
        text='''Jm Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
INCEPTION DATE 18th June, 2024
Details as on August 31, 2026
SCHEME PORTFOLIO (TOP 25 STOCKS)
Name of Instrument (Equity Shares) % to NAV
Company 1 Limited 2.00\nCompany 2 Limited 2.00\nCompany 3 Limited 2.00\nCompany 4 Limited 2.00\nCompany 5 Limited 2.00\nCompany 6 Limited 2.00\nCompany 7 Limited 2.00\nCompany 8 Limited 2.00\nCompany 9 Limited 2.00\nCompany 10 Limited 2.00\nCompany 11 Limited 2.00\nCompany 12 Limited 2.00\nCompany 13 Limited 2.00\nCompany 14 Limited 2.00\nCompany 15 Limited 2.00\nCompany 16 Limited 2.00\nCompany 17 Limited 2.00\nCompany 18 Limited 2.00\nCompany 19 Limited 2.00\nCompany 20 Limited 2.00\nCompany 21 Limited 2.00\nCompany 22 Limited 2.00\nCompany 23 Limited 2.00\nCompany 24 Limited 2.00\nCompany 25 Limited 2.00
Other Equity Stocks 49.00
Total Equity Holdings 99.00
TREPS & Others * 1.00
Total Assets 100.00'''
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:text)
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Jm Small Cap Fund',
                                            'https://www.jmfinancialmf.com/factsheet.pdf','jm-top25')
        self.assertGreaterEqual(count,25)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Jm Small Cap Fund' AND hash='jm-top25'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0})
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings WHERE snapshot_id=(SELECT id FROM portfolios WHERE hash='jm-top25')")['n'],25)

    def test_edelweiss_current_top10_reconciles_cross_page_total(self):
        from tracker.report_parser import edelweiss_top10_portfolio
        first='''Edelweiss Small Cap Fund
Type of Scheme: An open ended equity scheme predominantly investing in small cap stocks
NAV as on August 31, 2026
Portfolio Data
Top 10 Holdings % to Net
Assets
1 City Union Bank Limited 3.17%
2 Karur Vysya Bank Ltd 2.64%
3 Multi Commodity Exchange Of India Ltd 2.64%
4 PNB Housing Finance Ltd 2.34%
5 Avalon Technologies Ltd. 2.27%
6 Gabriel India Ltd 2.18%
7 KEI Industries Ltd 2.06%
8 Ajanta Pharma Ltd 1.94%
9 Fortis Healthcare Ltd 1.92%
10 Radico Khaitan Ltd 1.84%
Past Performance is not an indicator or guarantee of future results'''
        extra='''Additional Disclosure by AMC
Total no. of equity stocks : 95
Top 10 stocks : 23.00%
Data as on August 31, 2026
Edelweiss Small Cap Fund'''
        parsed=edelweiss_top10_portfolio(first,extra)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual(len(parsed['positions']),10)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),23.00,places=2)
        self.assertIsNone(edelweiss_top10_portfolio(first,extra.replace('23.00%','22.00%')))
        self.assertIsNone(edelweiss_top10_portfolio(first,extra.replace('August 31, 2026','July 31, 2026')))

    def test_edelweiss_current_three_page_factsheet_saves_partial(self):
        from tracker import disclosures
        first='''Edelweiss Small Cap Fund
Type of Scheme: An open ended equity scheme predominantly investing in small cap stocks
NAV as on August 31, 2026
AUM as on August 31, 2026 ` 7,259.07 Cr
Benchmark Nifty Smallcap 250 TRI
Portfolio Data
Top 10 Holdings % to Net
Assets
1 City Union Bank Limited 3.17%
2 Karur Vysya Bank Ltd 2.64%
3 Multi Commodity Exchange Of India Ltd 2.64%
4 PNB Housing Finance Ltd 2.34%
5 Avalon Technologies Ltd. 2.27%
6 Gabriel India Ltd 2.18%
7 KEI Industries Ltd 2.06%
8 Ajanta Pharma Ltd 1.94%
9 Fortis Healthcare Ltd 1.92%
10 Radico Khaitan Ltd 1.84%
Past Performance is not an indicator or guarantee of future results
Data as on August 31, 2026'''
        middle='''Major Changes w.r.t previous month
Data as on August 31, 2026
Edelweiss Small Cap Fund'''
        extra='''Additional Disclosure by AMC
Quantitative Indicators
Total no. of equity stocks : 95
Top 10 stocks : 23.00%
Data as on August 31, 2026
Edelweiss Small Cap Fund'''
        pages=[
            SimpleNamespace(extract_text=lambda *args,**kwargs:first),
            SimpleNamespace(extract_text=lambda *args,**kwargs:middle),
            SimpleNamespace(extract_text=lambda *args,**kwargs:extra),
        ]
        reader=SimpleNamespace(is_encrypted=False,pages=pages)
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(
                b'%PDF','Edelweiss Small Cap Fund',
                'https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026.pdf',
                'edel-current')
        self.assertGreaterEqual(count,10)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family='Edelweiss Small Cap Fund' AND p.hash='edel-current'
          GROUP BY p.id""")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0,'positions':10})

    def test_edelweiss_top30_reconciles_published_top10_total(self):
        from tracker.report_parser import edelweiss_top30_portfolio
        text='''Edelweiss Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
Data as on August 31, 2026
Top 30 Holdings
Top 10 stocks@ : 24.20%
Company Name Allocation
Alpha Industries Ltd 3.50%\nBeta Bank Ltd 3.40%\nGamma Pharma Ltd 2.70%\nDelta Systems Ltd 2.30%\nEpsilon Foods Ltd 2.10%\nZeta Finance Ltd 2.10%\nEta Motors Ltd 2.10%\nTheta Chemicals Ltd 2.00%\nIota Services Ltd 2.00%\nKappa Health Ltd 2.00%\nLambda Products Ltd 1.90%\nMu Technologies Ltd 1.90%\nNu Finance Ltd 1.80%\nXi Industries Ltd 1.80%\nOmicron Foods Ltd 1.80%\nPi Capital Ltd 1.70%\nRho Motors Ltd 1.70%\nSigma Labs Ltd 1.70%\nTau Services Ltd 1.60%\nUpsilon Systems Ltd 1.60%\nPhi Industries Ltd 1.60%\nChi Bank Ltd 1.50%\nPsi Pharma Ltd 1.50%\nOmega Foods Ltd 1.50%\nAster Finance Ltd 1.40%\nBirch Motors Ltd 1.40%\nCedar Systems Ltd 1.40%\nDune Industries Ltd 1.30%\nElm Services Ltd 1.30%\nFir Products Ltd 1.30%
EDELWEISS MUTUAL FUND | AUGUST 2026'''
        parsed=edelweiss_top30_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual(len(parsed['positions']),30)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions'][:10]),24.20,places=2)
        self.assertIsNone(edelweiss_top30_portfolio(text.replace('Top 10 stocks@ : 24.20%','Top 10 stocks@ : 19.99%')))

    def test_edelweiss_factsheet_saves_top30_as_partial_only(self):
        from tracker import disclosures
        text='''Edelweiss Small Cap Fund
An open ended equity scheme predominantly investing in small cap stocks
Data as on August 31, 2026
Top 30 Holdings
Top 10 stocks@ : 24.20%
Company Name Allocation
Alpha Industries Ltd 3.50%\nBeta Bank Ltd 3.40%\nGamma Pharma Ltd 2.70%\nDelta Systems Ltd 2.30%\nEpsilon Foods Ltd 2.10%\nZeta Finance Ltd 2.10%\nEta Motors Ltd 2.10%\nTheta Chemicals Ltd 2.00%\nIota Services Ltd 2.00%\nKappa Health Ltd 2.00%\nLambda Products Ltd 1.90%\nMu Technologies Ltd 1.90%\nNu Finance Ltd 1.80%\nXi Industries Ltd 1.80%\nOmicron Foods Ltd 1.80%\nPi Capital Ltd 1.70%\nRho Motors Ltd 1.70%\nSigma Labs Ltd 1.70%\nTau Services Ltd 1.60%\nUpsilon Systems Ltd 1.60%\nPhi Industries Ltd 1.60%\nChi Bank Ltd 1.50%\nPsi Pharma Ltd 1.50%\nOmega Foods Ltd 1.50%\nAster Finance Ltd 1.40%\nBirch Motors Ltd 1.40%\nCedar Systems Ltd 1.40%\nDune Industries Ltd 1.30%\nElm Services Ltd 1.30%\nFir Products Ltd 1.30%'''
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:text)
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Edelweiss Small Cap Fund',
                                            'https://www.edelweissmf.com/factsheet.pdf','edel-top30')
        self.assertGreaterEqual(count,30)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Edelweiss Small Cap Fund' AND hash='edel-top30'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0})
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings WHERE snapshot_id=(SELECT id FROM portfolios WHERE hash='edel-top30')")['n'],30)

    def test_boi_multicolumn_reconstructs_equity_tail_and_asset_classes(self):
        from tracker.report_parser import boi_multicolumn_complete_portfolio
        rows=[
            'Bank of India Small Cap Fund',
            '(An open ended equity scheme predominantly investing in small cap stocks)',
            'All data as on August 31, 2026 (Unless indicated otherwise)',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Tail Holding Limited 1.00',
            'Total 80.00',
            'GOVERNMENT BOND AND','TREASURY BILL','Treasury Bill',
            '364 Days Tbill (SOV) 5.00','Total 5.00',
            'MONEY MARKET INSTRUMENTS','Certificate of Deposit',
            'Alpha Bank Limited (CRISIL A1+) 2.50',
            'Beta Bank Limited (ICRA A1+) 2.50','Total 5.00',
            'CASH & CASH EQUIVALENT',
            'Net Receivables/Payables (0.05)',
            'TREPS / Reverse Repo Investments 10.05','Total 10.00',
            'GRAND TOTAL 100.00','PORTFOLIO DETAILS',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'EQUITY HOLDINGS',
        ]
        for sector in range(9):
            rows.append(f'SECTOR {sector+1} 5.00')
            for holding in range(5):
                rows.append(f'Company {sector+1}-{holding+1} Limited 1.00')
        rows.append('OTHERS 35.00')
        for holding in range(17):
            rows.append(f'Other Company {holding+1} Limited 2.00')
        rows += ['EQUITY INDUSTRY ALLOCATION','INVESTMENT OBJECTIVE']
        parsed=boi_multicolumn_complete_portfolio('\n'.join(rows))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertEqual(parsed['positions'][-1]['weight'],10.0)
        self.assertIsNone(boi_multicolumn_complete_portfolio(
            '\n'.join(rows).replace('Total 5.00','Total 4.00',1)))

    def test_boi_factsheet_prefers_real_multicolumn_parser(self):
        from tracker import disclosures
        rows=[
            'Bank of India Small Cap Fund',
            '(An open ended equity scheme predominantly investing in small cap stocks)',
            'All data as on August 31, 2026 (Unless indicated otherwise)',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Tail Holding Limited 1.00','Total 80.00',
            'GOVERNMENT BOND AND','TREASURY BILL','Treasury Bill',
            '364 Days Tbill (SOV) 5.00','Total 5.00',
            'MONEY MARKET INSTRUMENTS','Certificate of Deposit',
            'Alpha Bank Limited (CRISIL A1+) 5.00','Total 5.00',
            'CASH & CASH EQUIVALENT','TREPS / Reverse Repo Investments 10.00','Total 10.00',
            'GRAND TOTAL 100.00','PORTFOLIO DETAILS',
            'Portfolio Holdings % to Net','Industry/ Rating Assets',
            'Portfolio Holdings % to Net','Industry/ Rating Assets','EQUITY HOLDINGS',
        ]
        for sector in range(9):
            rows.append(f'SECTOR {sector+1} 5.00')
            for holding in range(5):
                rows.append(f'Company {sector+1}-{holding+1} Limited 1.00')
        rows.append('OTHERS 35.00')
        for holding in range(17):
            rows.append(f'Other Company {holding+1} Limited 2.00')
        rows += ['EQUITY INDUSTRY ALLOCATION','INVESTMENT OBJECTIVE']
        text='\n'.join(rows)
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:text)
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(
                b'%PDF','Bank Of India Small Cap Fund',
                'https://www.boimf.in/factsheet-august-2026.pdf','boi-real')
        self.assertGreater(count,30)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Bank Of India Small Cap Fund' AND hash='boi-real'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1})

    def test_groww_portfolio_reconciles_but_remains_partial_due_to_others_bucket(self):
        from tracker.report_parser import groww_reconciled_portfolio
        text='''GROWW Small Cap Fund
May 2026
The objective of the Scheme is to generate long term capital appreciation.
29th January, 2026
Benchmark
Nifty Smallcap 250 Index
Data as on 31st May 2026
Equity & Equity Related Holdings
TD Power Systems Limited Electrical Equipment 24.00%
Tamilnad Mercantile Bank Ltd. Banks 20.00%
Home First Finance Company India Limited Finance 14.00%
City Union Bank Limited Banks 8.00%
Apar Industries Ltd Electrical Equipment 7.00%
Ujjivan Small Finance Bank Limited Banks 5.00%
Azad Engineering Limited Electrical Equipment 4.00%
Prudent Corporate Advisory Services Ltd Capital Markets 0.50%
Navin Fluorine International Limited Chemicals & Petrochemicals 0.50%
Craftsman Automation Limited Auto Components 0.40%
SBFC Finance Limited Finance 0.40%
Creditaccess Grameen Limited Finance 0.40%
RBL Bank Limited Banks 0.40%
Galaxy Surfactants Limited Chemicals & Petrochemicals 0.30%
LG Balakrishnan & Bros Limited Auto Components 0.30%
Yatharth Hospital & Trauma Care Serv Ltd Healthcare Services 0.20%
Tenneco Clean Air India Limited Auto Components 0.20%
Sharda Motor Industries Limited Auto Components 0.20%
OnEMI Technology Solutions Limited IT - Software 0.20%
Fine Organic Industries Limited Chemicals & Petrochemicals 0.20%
Venus Pipes & Tubes Ltd Industrial Products 0.20%
Schneider Electric Infrastructure Ltd. Electrical Equipment 0.20%
J.Kumar Infraprojects Limited Construction 0.20%
Karur Vysya Bank Limited Banks 0.20%
Others 0.60%
Total 87.60%
Tri Party Repo (TREPs)
The Clearing Corporation of India Ltd. 10.40%
Total 10.40%
*TREPS/Reverse Repo/Net current assets 2.00%
Grand Total 100.00%
(An open ended equity scheme predominantly investing in small cap stocks)
Company Name Industry/ Rating % to NAV
Portfolio Holdings'''
        parsed=groww_reconciled_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-05-31')
        self.assertEqual(parsed['benchmark'],'Nifty Smallcap 250 Index')
        self.assertEqual(parsed['positions'][-2]['asset_type'],'Money market')
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertTrue(any(x['name']=='Others (AMC aggregate)' for x in parsed['positions']))
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertIsNone(groww_reconciled_portfolio(text.replace('Grand Total 100.00%','Grand Total 99.00%')))
        self.assertIsNone(groww_reconciled_portfolio(text.replace('GROWW Small Cap Fund','GROWW Mid Cap Fund',1)))


    def test_quant_top10_portfolio_reconciles_published_concentration(self):
        from tracker.report_parser import quant_top10_portfolio
        text='''quant Small Cap Fund
Investment Objective: The primary investment objective of the scheme is to seek to generate capital appreciation & provide long-term growth opportunities by investing in a portfolio of Small Cap companies.
INCEPTION DATE
29 Oc tober 1996
BENCHMARK INDEX:
NIFTY SMAL
LCAP 250 TRI
PORTFOLIO TOP HOLDING
LIST OF SECURITIES % T O NAV
Reliance Industries Ltd. 9.47
RBL Bank
Ltd. 5.77
Adani Power Ltd. 4.38
HFCL Ltd. 3.44
Sun TV Network Ltd. 2.92
Piramal Finance Ltd. 2.85
Anand Rathi Wealth Ltd. 2.81
Aster DM Healthcare Ltd. 2.61
Aurobindo Pharma Ltd. 2.31
Adani Green Energy Ltd. 2.20
Equity & Equity Related Instruments 95.21
Debt & Money Market Instruments
and Net Current Assets
4.79
Grand Total 100.00PORTFOLIO CONCENTRATION
Top Holding
10
20
30
% of Portfolio
38.76
57.81
72.33
As on April 30, 2026 14'''
        parsed=quant_top10_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-04-30')
        self.assertEqual(len(parsed['positions']),11)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions'][:10]),38.76,places=2)
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Debt, money market and net current assets')
        self.assertEqual(parsed['positions'][-1]['weight'],4.79)
        self.assertIsNone(quant_top10_portfolio(text.replace('% of Portfolio\n38.76','% of Portfolio\n39.76')))
        self.assertIsNone(quant_top10_portfolio(text.replace('Grand Total 100.00','Grand Total 99.00')))
        self.assertIsNone(quant_top10_portfolio(text.replace('quant Small Cap Fund','quant Mid Cap Fund',1)))


    def test_trustmf_named_portfolio_is_partial_and_dated(self):
        from tracker.report_parser import trustmf_named_portfolio
        text='''TRUSTMF Small Cap Fund
(An open-ended equity scheme predominantly investing in small cap stocks)
Date of Allotment
04th November 2024
Benchmark
NIFTY Smallcap 250 TRI
Portfolio as on June 30, 2025
Company/Issuer Industry % To Net Assets
Multi Commodity Exchange of India Limited^ Capital Markets 3.13
Karur Vysya Bank Limited^ Banks 2.75
PNB Housing Finance Limited^ Finance 2.58
Solar Industries India Limited^ Chemicals & Petrochemicals 2.35
Coforge Limited^ IT - Software 2.27
Apollo Micro Systems Limited^ Aerospace & Defense 2.06
Radico Khaitan Limited^ Beverages 1.99
Welspun Corp Limited^ Industrial Products 1.93
S.J.S. Enterprises Limited^ Auto Components 1.83
Nuvama Wealth Management Limited^ Capital Markets 1.83
Gabriel India Limited^ Auto Components 1.79
Shaily Engineering Plastics Limited^ Industrial Products 1.76
'''
        parsed=trustmf_named_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2025-06-30')
        self.assertGreaterEqual(len(parsed['positions']),10)
        self.assertEqual(parsed['positions'][0]['name'],'Multi Commodity Exchange of India Limited')
        self.assertIsNone(trustmf_named_portfolio(text.replace('TRUSTMF Small Cap Fund','TRUSTMF Flexi Cap Fund',1)))
        self.assertIsNone(trustmf_named_portfolio(text.replace('NIFTY Smallcap 250 TRI','NIFTY 500 TRI',1)))


    def test_trustmf_structured_workbook_reconciles_dated_treps(self):
        from tracker.portfolio_parser import parse_sheet
        rows=[
            ['TMFCB','TRUSTMF Small Cap Fund','','','','',''],
            ['', 'Monthly Portfolio Statement as on August 31, 2026','','','','',''],
            ['', 'Name of the Instrument','ISIN','Industry','Quantity','Market/Fair Value (Rs. in Lakhs)','% to Net Assets'],
            ['EQ01','Alpha Industries Limited','INE123456789','Industrial Products',100,95500,95.50],
            ['', 'Sub Total','','','',95500,95.50],
            ['', 'Total','','','',95500,95.50],
            ['', 'CBLO / Reverse Repo / TREPS','','','','',''],
            ['TRP_010926','TREPS 01-Sep-2026','','','',4500,4.50],
            ['', 'Sub Total','','','',4500,4.50],
            ['', 'Total','','','',4500,4.50],
            ['', 'GRAND TOTAL','','','',100000,100.00],
        ]
        formats=[['General']*7 for _ in rows]
        parsed=parse_sheet(rows,formats,'Trustmf Small Cap Fund')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        self.assertEqual(len(parsed['positions']),2)
        self.assertEqual(parsed['positions'][1]['name'],'TREPS 01-Sep-2026')
        self.assertEqual(parsed['positions'][1]['asset_type'],'Money market')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100.0,places=6)
        self.assertAlmostEqual(parsed['aum'],1000.0,places=6)

        bad=[row[:] for row in rows]
        bad[7][1]='TREPS undated'
        rejected=parse_sheet(bad,formats,'Trustmf Small Cap Fund')
        self.assertFalse(rejected['complete'])
        self.assertIn('TREPS undated',rejected['unknown_rows'])



    def test_union_complete_portfolio_reconciles_all_published_assets(self):
        from tracker.report_parser import union_complete_portfolio
        equities=[(f'Company {i} Ltd.',4.90) for i in range(1,20)]
        equities.append(('Bank of Maharashtra',5.57))
        rows='\n'.join(f'{name} {weight:.2f}%' for name,weight in equities)
        text=f'''(Small Cap Fund - An Open Ended Equity Scheme predominantly investing in Small Cap stocks)
Data as on July 31, 2026
Union
SMALL CAP FUND
Date of allotment
10 June 2014
Benchmark Index
BSE 250 SmallCap Index (TRI)
Industry/Company/Issuer % to Net Assets
Portfolio
BANKS 98.67%
{rows}
Equity Shares 98.67%
TREASURY BILLS 0.04%
91 DAY T-BILL 0.04%
Sovereign 0.04%
Triparty Repo, Cash, Cash Equivalents & 1.29%
Net Current Assets
Grand Total 100.00%
Union Mutual Fund - Registration No. MF/066/11/01
No. of Stocks 20 251'''
        parsed=union_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-07-31')
        self.assertEqual(len(parsed['positions']),22)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions'] if x['asset_type']=='Equity'),98.67,places=2)
        self.assertEqual(parsed['positions'][-2]['asset_type'],'Debt')
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertIsNone(union_complete_portfolio(text.replace('No. of Stocks 20','No. of Stocks 21')))
        self.assertIsNone(union_complete_portfolio(text.replace('Grand Total 100.00%','Grand Total 99.00%')))
        self.assertIsNone(union_complete_portfolio(text.replace('Union\nSMALL CAP FUND','Union\nMID CAP FUND',1)))


    def test_union_omnibus_portfolio_supports_long_futures_and_multiple_tbills(self):
        from tracker.report_parser import union_complete_portfolio
        equities='\n'.join([f'Company {i} Ltd. 4.80%' for i in range(1,20)]
                           +['Company 20 Ltd. 6.89%','Company 1 Ltd. (Futures) 0.97%'])
        text=f'''Union
SMALL CAP FUND
(Small Cap Fund - An Open Ended Equity Scheme predominantly investing in Small Cap stocks)
Factsheet as on March 31, 2026
Date of allotment
10 June 2014
Benchmark Index
BSE 250 SmallCap Index (TRI)
No. of Stocks 20 250
Industry/Company/Issuer % to Net Assets
Portfolio
TEST SECTOR 99.06%
{equities}
Equity Shares and Long Futures 99.06%
TREASURY BILLS 0.37%
Sovereign 0.37%
91 DAY T-BILL 0.30%
364 DAY T-BILL 0.07%
Triparty Repo, Cash, Cash Equivalents & 0.58%
Net Current Assets
Grand Total 100.00%
Investment Objective'''
        parsed=union_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-03-31')
        self.assertEqual(len([x for x in parsed['positions'] if x['asset_type']=='Equity']),21)
        self.assertEqual(len([x for x in parsed['positions'] if x['asset_type']=='Debt']),2)
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100.01,places=2)
        self.assertIsNone(union_complete_portfolio(text.replace('364 DAY T-BILL 0.07%','364 DAY T-BILL 0.03%')))
        self.assertIsNone(union_complete_portfolio(text.replace('No. of Stocks 20 250','No. of Stocks 21 250')))

    def test_wealth_company_page_retains_observed_benchmark_identity(self):
        from tracker.amc_metrics import parse_page
        f='The Wealth Company Small Cap Fund'
        u='https://www.wealthcompanyamc.in/our-nfos/nfo/the-wealth-company-small-cap-fund/'
        html='''<html><head><title>The Wealth Company Small Cap Fund</title></head><body>
        <h1>The Wealth Company Small Cap Fund</h1>
        <p>Type: An open ended equity scheme predominantly investing in small cap stocks</p>
        <p>Benchmark: NIFTY SmallCap 250 index (TRI)</p>
        <p>Benchmark Risk-o-meter NIFTY SmallCap 250 index (TRI)</p>
        </body></html>'''
        self.assertEqual(parse_page(html,f,u,'wealth-benchmark'),1)
        self.assertEqual(db.one("SELECT value,as_of,unit FROM metrics WHERE family=? AND metric='benchmark'",(f,)),
                         {'value':'NIFTY SmallCap 250 TRI','as_of':date.today().isoformat(),
                          'unit':'Observed on official fund page'})
        self.assertEqual(parse_page(html.replace('Small Cap Fund','Mid Cap Fund'),f,u,'wrong'),0)

    def test_invesco_complete_workbook_reconciles_triparty_repo(self):
        from tracker.portfolio_parser import parse_sheet
        rows=[
            ['ISCF','INVESCO MUTUAL FUND','','','','',''],
            ['', 'Monthly Portfolio Statement as on August 31, 2026','','','','',''],
            ['', 'Invesco India Small cap Fund','','','','',''],
            ['', '(An open ended equity scheme predominantly investing in small cap stocks)','','','','',''],
            ['Name of the Instrument','ISIN','Industry*','Quantity','Market/Fair Value (Rs. in Lakhs)','% to Net Assets','YTM'],
            ['Alpha Industries Limited','INE123456789','Industrial Products',100,94810,94.81,''],
            ['Sub Total','','','',94810,94.81,''],
            ['TREPS / Reverse Repo','','','','','',''],
            ['Triparty Repo','','','',5190,5.19,4.96],
            ['Sub Total','','','',5190,5.19,''],
            ['GRAND TOTAL','','','',100000,100.0,''],
        ]
        formats=[['General']*7 for _ in rows]
        parsed=parse_sheet(rows,formats,'Invesco India Small Cap Fund')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],[])
        self.assertEqual(len(parsed['positions']),2)
        self.assertEqual(parsed['positions'][1]['name'],'Triparty Repo')
        self.assertEqual(parsed['positions'][1]['asset_type'],'Money market')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100.0,places=6)
        self.assertAlmostEqual(parsed['aum'],1000.0,places=6)

    def test_invesco_live_page_retains_dated_benchmark(self):
        from tracker.amc_metrics import parse_page
        f='Invesco India Small Cap Fund'
        u='https://www.invescomutualfund.com/our-funds/fund/equity/invesco-india-small-cap-fund/scgp'
        html='''<html><body><h1>Invesco India Small Cap Fund</h1>
        <p>To generate capital appreciation by investing predominantly in stocks of smallcap companies.</p>
        <p>AUM as on 31 August 2026 ₹15,799.46 Cr</p>
        <p>Benchmark As per AMFI Tier I Benchmark i.e. BSE 250 Smallcap TRI</p>
        </body></html>'''
        self.assertEqual(parse_page(html,f,u,'invesco-live'),1)
        self.assertEqual(db.one("SELECT value,as_of FROM metrics WHERE family=? AND metric='benchmark'",(f,)),
                         {'value':'BSE 250 Smallcap TRI','as_of':'2026-08-31'})

    def test_samco_live_page_retains_dated_benchmark(self):
        from tracker.amc_metrics import parse_page
        f='Samco Small Cap Fund'
        u='https://www.samcomf.com/mutual-funds/samco-small-cap-fund-direct-growth/scdgg'
        html='''<html><body><h1>Samco Small Cap Fund</h1>
        <p>An open-ended equity scheme predominantly investing in small cap stocks</p>
        <p>Cumulative performance (as on 31/08/2026)</p>
        <p>Benchmark: Nifty Small Cap 250 TRI Additional Benchmark: Nifty 50 Total Returns Index</p>
        </body></html>'''
        self.assertEqual(parse_page(html,f,u,'samco-live'),1)
        self.assertEqual(db.one("SELECT value,as_of FROM metrics WHERE family=? AND metric='benchmark'",(f,)),
                         {'value':'Nifty Smallcap 250 TRI','as_of':'2026-08-31'})

    def test_tata_combined_page_stores_only_explicit_top10_as_partial(self):
        from tracker.amc_metrics import parse_page
        url='https://info.tatamutualfund.com/combined/TATA/Small-Cap-Fund.html'
        rows=''.join(f'<tr><td>{i}</td><td>Company {i} Limited</td><td>{3.0+i/10:.2f}%</td></tr>' for i in range(1,11))
        html=f'''<html><head><title>Tata Small Cap Fund</title></head><body>
        <h1>Tata Small Cap Fund</h1>
        <div>As on 31st August 2026</div>
        <div>Type of Scheme: An equity scheme with focus towards small cap stocks</div>
        <div>Benchmark Name Nifty Smallcap 250 TRI</div>
        <table><tr><th>Top 10 Holdings</th><th></th><th>% to Net Assets</th></tr>{rows}</table>
        </body></html>'''.encode()
        self.assertEqual(parse_page(html,'Tata Small Cap Fund',url,'tata-hash'),11)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Tata Small Cap Fund'")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':0})
        self.assertEqual(db.one("SELECT value,as_of FROM metrics WHERE family='Tata Small Cap Fund' AND metric='benchmark'"),
                         {'value':'Nifty Smallcap 250 TRI','as_of':'2026-08-31'})
        self.assertEqual(db.one("SELECT COUNT(*) n FROM holdings")['n'],10)
        self.assertEqual(parse_page(html.replace(b'Tata Small Cap Fund',b'Tata Mid Cap Fund'),
                                    'Tata Small Cap Fund',url,'wrong'),0)


    def test_tata_structured_workbook_reconciles_repo_cash_and_net_assets(self):
        from tracker.portfolio_parser import parse_sheet
        rows=[
            ['TATA SMALL CAP FUND','','','','','',''],
            ['Tata Small Cap Fund','','','','','',''],
            ['An open ended equity scheme predominantly investing in small cap stocks','','','','','',''],
            ['Portfolio as on 31-08-26','','','','','',''],
            ['NAME OF THE INSTRUMENT','YIELD ( IN % )','INDUSTRY','ISIN CODE','QUANTITY','MKT VAL(Rs. Lacs)','% to NAV'],
            ['Alpha Industries Ltd','NA','Industrial Products','INE659A01023',100,91700,91.7],
            ['NAME OF THE INSTRUMENT','YIELD ( IN % )','RATINGS','ISIN CODE','QUANTITY','MKT VAL(Rs. Lacs)','% to NAV'],
            ['I) REPO','','','','',3100,3.1],
            ['CASH / NET CURRENT ASSET','','','','',5200,5.2],
            ['NET ASSETS','','','','',100000,100],
        ]
        formats=[['']*7 for _ in rows]
        parsed=parse_sheet(rows,formats,'Tata Small Cap Fund')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertTrue(parsed['complete'])
        self.assertEqual(len(parsed['positions']),3)
        self.assertEqual([x['asset_type'] for x in parsed['positions']],
                         ['Equity','Money market','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100.0,places=6)
        self.assertAlmostEqual(parsed['aum'],1000.0,places=6)
        self.assertEqual(parsed['positions'][0]['quantity'],100)
        bad_identity=[row[:] for row in rows]
        bad_identity[1][0]='Tata Mid Cap Fund'
        bad_identity[0][0]='TATA MID CAP FUND'
        self.assertIsNone(parse_sheet(bad_identity,formats,'Tata Small Cap Fund'))
        bad_total=[row[:] for row in rows]
        bad_total[-1][-1]=99
        self.assertFalse(parse_sheet(bad_total,formats,'Tata Small Cap Fund')['complete'])


    def test_boi_complete_portfolio_reconciles_all_asset_sections(self):
        from tracker.report_parser import boi_complete_portfolio
        text='''Bank of India Small Cap Fund
(An open ended equity scheme predominantly investing in small cap stocks)
All data as on March 31, 2026 (Unless indicated otherwise)
Portfolio Holdings % to Net
Industry/ Rating Assets
FOOD PRODUCTS 3.00
Alpha Foods Limited 2.00
Beta Foods Limited 1.00
OTHERS 92.00
Gamma Industries Limited 50.00
Delta Industries Limited 42.00
Total 95.00
CASH & CASH EQUIVALENT
Net Receivables/Payables 2.00
TREPS / Reverse Repo Investments 0.00
Total 2.00
GOVERNMENT BOND AND
TREASURY BILL
364 Days Tbill (MD 07/01/2027) (SOV) 1.00
Total 1.00
MONEY MARKET INSTRUMENTS
Certificate of Deposit
Bank of Baroda (FITCH A1+) 1.20
Canara Bank (CRISIL A1+) 0.80
Total 2.00
GRAND TOTAL 100.00
PORTFOLIO DETAILS
EQUITY HOLDINGS
INVESTMENT OBJECTIVE'''
        result=boi_complete_portfolio(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['day'],'2026-03-31')
        self.assertAlmostEqual(sum(x['weight'] for x in result['positions']),100,places=2)
        self.assertEqual([x['asset_type'] for x in result['positions'][-4:]],[
            'Debt','Money market','Money market','Cash and net current assets'])
        bad=text.replace('OTHERS 92.00','OTHERS 91.00')
        self.assertIsNone(boi_complete_portfolio(bad))
        self.assertIsNone(boi_complete_portfolio(text.replace('Bank of India Small Cap Fund','Bank of India Mid Cap Fund',1)))

    def test_boi_pdf_falls_back_to_layout_text_for_complete_portfolio(self):
        from tracker import disclosures
        standard='''Bank of India Small Cap Fund
(An open ended equity scheme predominantly investing in small cap stocks)
All data as on March 31, 2026
LATEST AUM'''
        layout='''Bank of India Small Cap Fund
(An open ended equity scheme predominantly investing in small cap stocks)
All data as on March 31, 2026
Portfolio Holdings
FOOD PRODUCTS 3.00
Alpha Foods Limited 2.00
Beta Foods Limited 1.00
OTHERS 92.00
Gamma Industries Limited 50.00
Delta Industries Limited 42.00
Total 95.00
CASH & CASH EQUIVALENT
Net Receivables/Payables 2.00
Total 2.00
GOVERNMENT BOND AND
TREASURY BILL
364 Days Tbill (MD 07/01/2027) (SOV) 1.00
Total 1.00
MONEY MARKET INSTRUMENTS
Certificate of Deposit
Bank of Baroda (FITCH A1+) 2.00
Total 2.00
GRAND TOTAL 100.00
INVESTMENT OBJECTIVE'''
        class Page:
            def extract_text(self,*args,**kwargs):
                return layout if kwargs.get('extraction_mode')=='layout' else standard
        reader=SimpleNamespace(is_encrypted=False,pages=[Page()])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Bank Of India Small Cap Fund',
                                            'https://www.boimf.in/factsheet.pdf','boi-layout')
        self.assertGreater(count,0)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Bank Of India Small Cap Fund' AND hash='boi-layout'")
        self.assertEqual(snap,{'as_of':'2026-03-31','complete':1})

    def test_boi_factsheet_pdf_saves_complete_snapshot(self):
        from tracker import disclosures
        page_text='''Bank of India Small Cap Fund
(An open ended equity scheme predominantly investing in small cap stocks)
All data as on March 31, 2026
Portfolio Holdings % to Net
Industry/ Rating Assets
FOOD PRODUCTS 3.00
Alpha Foods Limited 2.00
Beta Foods Limited 1.00
OTHERS 92.00
Gamma Industries Limited 50.00
Delta Industries Limited 42.00
Total 95.00
CASH & CASH EQUIVALENT
Net Receivables/Payables 2.00
Total 2.00
GOVERNMENT BOND AND
TREASURY BILL
364 Days Tbill (MD 07/01/2027) (SOV) 1.00
Total 1.00
MONEY MARKET INSTRUMENTS
Certificate of Deposit
Bank of Baroda (FITCH A1+) 2.00
Total 2.00
GRAND TOTAL 100.00
INVESTMENT OBJECTIVE'''
        page=SimpleNamespace(extract_text=lambda *args,**kwargs:page_text)
        reader=SimpleNamespace(is_encrypted=False,pages=[page])
        with patch('pypdf.PdfReader',return_value=reader):
            count=disclosures.factsheet_pdf(b'%PDF','Bank Of India Small Cap Fund','https://www.boimf.in/factsheet.pdf','boi')
        self.assertGreater(count,0)
        snap=db.one("SELECT as_of,complete FROM portfolios WHERE family='Bank Of India Small Cap Fund'")
        self.assertEqual(snap,{'as_of':'2026-03-31','complete':1})

    def test_hsbc_complete_portfolio_reconciles_sector_and_cash_totals(self):
        from tracker.report_parser import hsbc_complete_portfolio
        text='''HSBC Small Cap Fund
Small Cap Fund - An open ended equity scheme predominantly investing in small cap stocks.
Investment Objective: To generate long term capital growth.
Fund Details
Date of Allotment 12-May-14
Benchmark: NIFTY Small Cap 250 TRI
Issuer Market Cap/
Ratings % to Net Assets
Industrial Products 60.00%
Alpha Limited Small Cap 20.00%
Beta Limited Mid Cap 20.00%
Gamma Limited Small Cap 20.00%
Banks 38.00%
Delta Bank Limited Small Cap 19.00%
Epsilon Bank Limited Mid Cap 19.00%
Cash Equivalent 2.00%
TREPS* 1.20%
Net Current Assets: 0.80%
Total Net Assets as on 31-July-2026 100.00%
*TREPS : Tri-Party Repo fully collateralized by G-Sec'''
        result=hsbc_complete_portfolio(text)
        self.assertEqual(result['day'],'2026-07-31')
        self.assertEqual(len(result['positions']),7)
        self.assertAlmostEqual(sum(x['weight'] for x in result['positions']),100,places=2)
        self.assertEqual(result['positions'][-2]['asset_type'],'Money market')
        self.assertEqual(result['positions'][-1]['asset_type'],'Cash and net current assets')
        bad=text.replace('Banks 38.00%','Banks 39.00%')
        self.assertIsNone(hsbc_complete_portfolio(bad))


    def test_hsbc_august_joined_market_cap_label_still_reconciles(self):
        from tracker.report_parser import hsbc_complete_portfolio
        text='''Additional Disclosure
Past Performance is not an indicator or guarantee of future results
HSBC Small Cap Fund
Portfolio
Issuer Market Cap/
Ratings % to Net Assets
Aerospace & Defense 0.86%
PARAS DEFENCE AND SPACE TECHNOLOGIES LTDSmall Cap 0.59%
Data Patterns (India) Limited Small Cap 0.27%
Industrial Products 98.12%
Alpha Industrial Limited Small Cap 19.624%
Beta Industrial Limited Small Cap 19.624%
Gamma Industrial Limited Small Cap 19.624%
Delta Industrial Limited Small Cap 19.624%
Epsilon Industrial Limited Small Cap 19.624%
Cash Equivalent 1.02%
TREPS* 1.09%
Net Current Assets: -0.07%
Total Net Assets as on 31-August-2026 100.00%
*TREPS : Tri-Party Repo fully collateralized by G-Sec'''
        parsed=hsbc_complete_portfolio(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertEqual(parsed['positions'][0]['name'],'PARAS DEFENCE AND SPACE TECHNOLOGIES LTD')
        self.assertFalse(__import__('tracker.report_parser',fromlist=['owns_page']).owns_page(text,'HSBC Small Cap Fund'))
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100,places=2)
        self.assertIsNone(hsbc_complete_portfolio(text.replace('Aerospace & Defense 0.86%','Aerospace & Defense 0.92%')))

    def test_axis_top_holdings_are_partial_and_reconcile_to_stated_total(self):
        from tracker.amc_metrics import parse_page
        f='Axis Small Cap Fund';u='https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct'
        html='''<html><h1>Axis Small Cap Fund</h1>
        <p>AUM (In Cr.) ₹ 31,448.32 As On Aug 31, 2026</p>
        <p>Expense Ratio 0.71% As On Sep 21, 2026</p>
        <p>Top 10 Stocks (%) 18.52 Top 5 Stocks (%) 10.79 Top 3 Stocks (%) 7.13</p>
        <table><tr><th>Stocks</th><th>% of holdings</th></tr>
        <tr><td>A Limited</td><td>2.43</td></tr><tr><td>B Limited</td><td>2.39</td></tr>
        <tr><td>C Limited</td><td>2.31</td></tr><tr><td>D Limited</td><td>1.91</td></tr>
        <tr><td>E Limited</td><td>1.75</td></tr><tr><td>F Limited</td><td>1.71</td></tr>
        <tr><td>G Limited</td><td>1.66</td></tr><tr><td>H Limited</td><td>1.52</td></tr>
        <tr><td>I Limited</td><td>1.44</td></tr><tr><td>J Limited</td><td>1.40</td></tr></table>
        <p>Updated as on: September 16, 2026</p></html>'''
        self.assertEqual(parse_page(html,f,u,'axis'),11)
        snap=db.one('SELECT as_of,complete FROM portfolios WHERE family=?',(f,))
        self.assertEqual(snap,{'as_of':'2026-09-16','complete':0})
        rows=db.rows('SELECT name,weight,asset_type FROM holdings ORDER BY id')
        self.assertEqual(len(rows),10);self.assertTrue(all(x['asset_type']=='Equity' for x in rows))
        self.assertAlmostEqual(sum(x['weight'] for x in rows),18.52,places=2)


    def test_kotak_monthly_factsheet_reconciles_complete_portfolio(self):
        from tracker.amc_metrics import parse_page
        f='Kotak Small Cap Fund';u='https://www.kotakmf.com/factsheet/August_2026/kotak/SMALL-CAP.html'
        html='''<html><title>Kotak Small Cap Fund Factsheet - August 2026</title><h2>KOTAK SMALL CAP FUND</h2>
        <table><tr><th>Issuer/Instrument</th><th></th><th>% to Net Assets</th></tr>
        <tr><td>Equity &amp; Equity related</td><td></td><td></td></tr>
        <tr><td>Healthcare Services</td><td></td><td>60.00</td></tr>
        <tr><td>Alpha Health Limited</td><td></td><td>40.00</td></tr>
        <tr><td>Beta Diagnostics Ltd.</td><td></td><td>20.00</td></tr>
        <tr><td>Finance</td><td></td><td>39.05</td></tr>
        <tr><td>Gamma Finance Limited</td><td></td><td>39.05</td></tr>
        <tr><td>Equity &amp; Equity related - Total</td><td></td><td>99.05</td></tr>
        <tr><td>Triparty Repo</td><td></td><td>1.05</td></tr>
        <tr><td>Net Current Assets/(Liabilities)</td><td></td><td>-0.10</td></tr>
        <tr><td>Grand Total</td><td></td><td>100.00</td></tr></table>
        <p>Net Asset Value (NAV) (as on August 31, 2026)</p><p>AUM Rs 19,678.75 crs</p>
        <p>Benchmark NIFTY Smallcap 250 TRI</p><p>Data as on 31st August, 2026 unless otherwise specified.</p></html>'''
        # A responsive duplicate that has the same headings but cannot reconcile
        # must not prevent a later valid table on the same official page.
        broken='''<table><tr><th>Issuer/Instrument</th><th>% to Net Assets</th></tr>
        <tr><td>Healthcare Services</td><td>14.27</td></tr>
        <tr><td>Equity &amp; Equity related - Total</td><td>99.05</td></tr>
        <tr><td>Triparty Repo</td><td>1.05</td></tr>
        <tr><td>Net Current Assets/(Liabilities)</td><td>-0.10</td></tr>
        <tr><td>Grand Total</td><td>100.00</td></tr></table>'''
        html=html.replace('<table>',broken+'<table>',1)
        self.assertEqual(parse_page(html,f,u,'kotak'),5)
        snap=db.one('SELECT as_of,complete FROM portfolios WHERE family=?',(f,))
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1})
        rows=db.rows('SELECT name,sector,weight,asset_type FROM holdings ORDER BY id')
        self.assertEqual([x['asset_type'] for x in rows],['Equity','Equity','Equity','Money market','Cash and net current assets'])
        self.assertEqual(rows[0]['sector'],'Healthcare Services')
        self.assertEqual(rows[2]['sector'],'Finance')
        self.assertAlmostEqual(sum(x['weight'] for x in rows),100,places=2)
        self.assertEqual(float(db.one("SELECT value FROM metrics WHERE metric='aum'")['value']),19678.75)

    def test_portfolio_gap_audit_distinguishes_facts_only_from_source_gap(self):
        from tracker import coverage,amc_reports
        with db.connect() as c:
            c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                      (101,'Gap Small Cap Fund','Gap Small Cap Fund','Gap Mutual Fund','Direct','Growth','test'))
            c.execute("""INSERT INTO documents(family,title,kind,scope,url,published_at,first_seen,last_seen,origin)
              VALUES(?,?,?,?,?,?,?,?,?)""",('Gap Small Cap Fund','August factsheet','factsheet','Fund',
              'https://gap.example/factsheet.pdf','2026-08-31',db.now(),db.now(),'AMC'))
            did=c.execute("SELECT id FROM documents WHERE family='Gap Small Cap Fund'").fetchone()[0]
        h=db.archive(b'gap factsheet fixture','application/pdf')
        with db.connect() as c:
            c.execute('INSERT INTO document_versions(document_id,hash,observed_at) VALUES(?,?,?)',(did,h,db.now()))
            c.execute("INSERT INTO source_pages(amc_match,url,label,last_checked,status,detail) VALUES(?,?,?,?,?,?)",
                      ('Gap','https://gap.example/downloads','Downloads',db.now(),'Checked','Page checked'))
        amc_reports.init()
        with db.connect() as c:
            c.execute('INSERT INTO document_extractions VALUES(?,?,?,?,?,?,?,?)',
                      ('Gap Small Cap Fund',h,amc_reports.PARSER_VERSION,'https://gap.example/factsheet.pdf',
                       'parsed',5,'5 dated facts; 0 holdings',db.now()))
        row=next(x for x in coverage.report()['funds'] if x['family']=='Gap Small Cap Fund')
        self.assertEqual(row['portfolio_gap']['reason'],'facts_only_no_portfolio')
        self.assertEqual(row['portfolio_gap']['document']['kind'],'factsheet')
        self.assertEqual(row['portfolio_gap']['extraction']['records'],5)

        with db.connect() as c:
            c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                      (102,'Unavailable Small Cap Fund','Unavailable Small Cap Fund','Unavailable Mutual Fund','Direct','Growth','test'))
            c.execute("INSERT INTO source_pages(amc_match,url,label,last_checked,status,detail) VALUES(?,?,?,?,?,?)",
                      ('Unavailable','https://unavailable.example/downloads','Downloads',db.now(),'Gap','Timed out'))
        row=next(x for x in coverage.report()['funds'] if x['family']=='Unavailable Small Cap Fund')
        self.assertEqual(row['portfolio_gap']['reason'],'source_unavailable')
        self.assertEqual(row['portfolio_gap']['source_page']['status'],'Gap')

    def test_coverage_fee_metric_prefers_direct_only_on_same_date(self):
        from tracker import coverage
        family='Tie Break Small Cap Fund'
        with db.connect() as c:
            c.execute(
                'INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                (999901,family,family,'Tie Break Mutual Fund','Direct','Growth','test'),
            )
        db.metric(family,'Regular','base_expense_ratio','2026-09-23',1.94,'% p.a.','official')
        db.metric(family,'Direct','base_expense_ratio','2026-09-23',0.42,'% p.a.','official')
        row=next(x for x in coverage.report()['funds'] if x['family']==family)
        self.assertEqual(row['base_expense_ratio']['plan'],'Direct')
        self.assertEqual(float(row['base_expense_ratio']['value']),0.42)

        # Reporting date remains the primary ordering rule: a genuinely newer
        # Regular observation must not be hidden by an older Direct one.
        db.metric(family,'Regular','base_expense_ratio','2026-09-24',1.90,'% p.a.','official')
        row=next(x for x in coverage.report()['funds'] if x['family']==family)
        self.assertEqual(row['base_expense_ratio']['plan'],'Regular')
        self.assertEqual(row['base_expense_ratio']['as_of'],'2026-09-24')

    def test_portfolio_freshness_target_has_new_month_grace(self):
        from datetime import date
        from tracker.coverage import expected_portfolio_as_of
        self.assertEqual(expected_portfolio_as_of(date(2026,9,22)),'2026-08-31')
        self.assertEqual(expected_portfolio_as_of(date(2026,9,5)),'2026-07-31')


if __name__=='__main__':unittest.main()
