"""Financial and archive invariants. All fixtures are synthetic and isolated."""
import os
import tempfile
import unittest
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import patch

_temp=tempfile.TemporaryDirectory()
os.environ['SMALLCAP_DATA_DIR']=_temp.name
os.environ['SMALLCAP_NO_SCHEDULER']='1'
from tracker import db,analytics,providers,disclosures
from tracker.app import app
from fastapi.testclient import TestClient


class TrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()
        with db.connect() as c:
            c.executemany('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',[
                (1,'Test Small Cap Direct Growth','Test Small Cap Fund','Test AMC','Direct','Growth','https://example.com/amfi'),
                (2,'Test Small Cap Direct IDCW','Test Small Cap Fund','Test AMC','Direct','IDCW','https://example.com/amfi')])
        cls.client=TestClient(app)

    def test_current_and_legacy_amfi_formats(self):
        prefix='Open Ended Schemes(Equity Scheme - Small Cap Fund)\nTest Mutual Fund\n'
        current='Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n'+prefix+'123;INF123456789;INF123456788;Test Small Cap Fund;Direct Plan;IDCW;12.500;04-Sep-2026'
        old='Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date\n'+prefix+'123;INF123456789;-;Test Small Cap Fund - Direct Plan - Growth;12.500;04-Sep-2026'
        a,b=providers.parse_amfi(current)[0],providers.parse_amfi(old)[0]
        self.assertEqual(a['option'],'IDCW');self.assertEqual(a['reinvestment_isin'],'INF123456788')
        self.assertEqual(a['family'],b['family']);self.assertEqual(b['plan'],'Direct');self.assertEqual(b['option'],'Growth')
        self.assertFalse(providers.parse_amfi(current.replace('Small Cap Fund)','Mid Cap Fund)')))

    def test_official_nav_precedence_and_revisions(self):
        db.save_nav(1,[('2020-01-01',100)],'https://api.mfapi.in/mf/1')
        db.save_nav(1,[('2020-01-01',101)],providers.AMFI_NAV)
        db.save_nav(1,[('2020-01-01',99)],'https://api.mfapi.in/mf/1')
        self.assertEqual(db.one("SELECT value FROM nav WHERE code=1 AND date='2020-01-01'")['value'],101)
        self.assertEqual(db.one("SELECT COUNT(*) n FROM nav_observations WHERE code=1 AND date='2020-01-01'")['n'],3)

    def test_published_option_and_plan_variants(self):
        for value in ('Growth','Growth Option','Regular Growth','Growth\t'):
            self.assertEqual(providers.option_type(value),'Growth')
        for value in ('IDCW','Income Distribution cum Capital Withdrawal','Reinvestment/Payout','Dividend'):
            self.assertEqual(providers.option_type(value),'IDCW')
        self.assertEqual(providers.option_type('Bonus Option'),'Bonus')
        self.assertEqual(providers.plan_type('','ICICI Smallcap Fund - Institutional Growth'),'Institutional')
        self.assertEqual(providers.plan_type('','HSBC Small Cap Fund'),'Unspecified')

    def test_date_matched_comparison_no_forward_fill(self):
        result=analytics.aligned([['2024-01-01',10],['2024-01-02',12],['2024-01-03',15]], [['2024-01-01',200],['2024-01-03',220]])
        self.assertEqual(len(result),2);self.assertEqual(result[0],["2024-01-01",100,100])
        self.assertAlmostEqual(result[-1][1],150);self.assertAlmostEqual(result[-1][2],110)

    def test_excel_fund_identity_and_percentage_storage(self):
        import io,openpyxl
        book=openpyxl.Workbook();wrong=book.active;wrong.title='Other Small Cap'
        wrong.append(['Test Nifty Smallcap 250 Index Fund (An open ended index scheme)'])
        wrong.append(['Portfolio as on July 31,2026'])
        wrong.append(['ISIN','Name of the Instrument','Industry','% to NAV'])
        wrong.append(['INF123456789','Test Small Cap Fund','',.8])
        sheet=book.create_sheet('SC')
        sheet.append(['Test Small Cap Fund (An open-ended equity scheme predominantly investing in small cap stocks)'])
        sheet.append(['Portfolio as on July 31,2026'])
        sheet.append(['ISIN','Name of the Instrument','Industry','% to NAV'])
        sheet.append(['','Equity & equity related','',''])
        sheet.append(['INE123456789','Alpha','Banks',.0189]);sheet['D5'].number_format='0.00%'
        sheet.append(['INE123456788','Beta','Finance',2.0])
        out=io.BytesIO();book.save(out);book.close();body=out.getvalue();h=db.archive(body)
        self.assertEqual(disclosures.spreadsheet(body,'Test Small Cap Fund','https://example.com/workbook.xlsx',h),2)
        p=db.one('SELECT * FROM portfolios WHERE hash=?',(h,));self.assertEqual(p['as_of'],'2026-07-31')
        positions=db.rows('SELECT * FROM holdings WHERE snapshot_id=? ORDER BY name',(p['id'],))
        self.assertAlmostEqual(positions[0]['weight'],1.89);self.assertAlmostEqual(positions[1]['weight'],2.0)
        self.assertEqual(positions[0]['asset_type'],'Equity')

    def test_pdf_fund_heading_and_report_dates(self):
        from types import SimpleNamespace
        text='Test Small Cap Fund\nSmall cap Fund\nDetails as on May 31, 2026\nType of Scheme\nAn open-ended equity scheme predominantly investing in small cap stocks.\nFund Size\nMonth End: Rs. 74000 Cr\nNAV as on May 29, 2026\nBase Expense Ratio\nRegular 1.14\nDirect 0.54\nPortfolio as on May 31, 2026\nAlpha 1.77\nCash 98.23\nSIP results'
        unrelated='Other Multi Asset Fund\nType of Scheme\nAn open ended fund of funds scheme\nDetails as on May 31, 2026\nMonth End: Rs. 2500 Cr\nPortfolio as on May 31, 2026\nTest Small Cap Fund\n1.50\nBase Expense Ratio\nDirect 0.08'
        pages=[SimpleNamespace(extract_text=lambda:text),SimpleNamespace(extract_text=lambda:unrelated)]
        h=db.archive(b'synthetic PDF fixture')
        with patch('pypdf.PdfReader',return_value=SimpleNamespace(is_encrypted=False,pages=pages)):
            disclosures.factsheet_pdf(b'fixture','Test Small Cap Fund','https://example.com/factsheet.pdf',h)
        facts=db.rows('SELECT metric,as_of,value FROM metrics WHERE hash=?',(h,))
        self.assertEqual([float(x['value']) for x in facts if x['metric']=='aum'],[74000])
        self.assertTrue(all(x['as_of']=='2026-05-31' for x in facts))
        self.assertNotIn('0.08',[x['value'] for x in facts])

    def test_summary_rejects_a_different_smallcap_scheme(self):
        body=b'<Summary><Fund_Name>Test Nifty Smallcap 250 Index Fund</Fund_Name><Benchmark_Tier_1>Nifty Smallcap 250 TRI</Benchmark_Tier_1></Summary>'
        h=db.archive(body,'application/xml')
        disclosures.summary_xml(body,'Test Small Cap Fund','https://example.com/summary.xml',h)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM metrics WHERE hash=?',(h,))['n'],0)

    def test_cagr_and_drawdown(self):
        start=date(2020,1,1)
        points=[[(start+timedelta(days=i)).isoformat(),100*1.1**(i/365.25)] for i in range(1462)]
        stats=analytics.performance(points)
        self.assertAlmostEqual(stats['returns']['3Y']['value'],10,8)
        self.assertAlmostEqual(stats['max_drawdown'],0)
        self.assertEqual(analytics.performance([['2020-01-01',100],['2020-01-02',70],['2020-01-03',90]])['max_drawdown'],-30.000000000000004)

    def test_idcw_reinvestment(self):
        events=[{'ex_date':'2024-01-02','amount':10,'reinvestment_nav':95}]
        points=analytics.reinvested([['2024-01-01',100],['2024-01-02',95]],events,'2024-01-01','2024-01-02')
        self.assertAlmostEqual(points[-1][1],105)

    def test_idcw_no_total_return_without_coverage(self):
        db.save_nav(2,[('2024-01-01',100),('2024-01-02',90)],providers.AMFI_NAV)
        r=self.client.get('/api/funds/2/performance').json()
        self.assertFalse(r['can_total_return']);self.assertEqual(r['comparison'],[]);self.assertIsNone(r['sip'])

    def test_flat_nav_sip_has_zero_profit(self):
        result=analytics.sip([['2024-01-01',100],['2024-02-01',100],['2024-03-01',100],['2024-03-31',100]],1000)
        self.assertEqual(result['invested'],3000);self.assertAlmostEqual(result['gain'],0)
        self.assertAlmostEqual(result['xirr'],0,8)

    def test_official_aum_parser_uses_reported_date_and_scheme_identity(self):
        from tracker import amc_metrics
        url=amc_metrics.PAGES[0][2]
        content=b'<h1>Axis Small Cap Fund</h1><div>AUM (In Cr.) \xe2\x82\xb9 31,448.32 As On Aug 31, 2026</div><div>Other fund AUM 99,000</div>'
        h=db.archive(content,'text/html')
        self.assertEqual(amc_metrics.parse_page(content,'Axis Small Cap Fund',url,h),1)
        r=db.one('SELECT * FROM metrics WHERE hash=?',(h,))
        self.assertEqual(r['as_of'],'2026-08-31');self.assertAlmostEqual(float(r['value']),31448.32)
        self.assertEqual(amc_metrics.parse_page(content,'Axis Small Cap Fund',url.replace('axis-small-cap','axis-large-cap'),h),0)
        self.assertEqual(amc_metrics.parse_page(content.replace(b'Axis Small Cap Fund',b'Axis Large Cap Fund'),'Axis Small Cap Fund',url,h),0)

    def test_amfi_fee_components_are_not_conflated(self):
        from tracker.amfi_metrics import save_fees
        source='https://www.amfiindia.com/api/fixture';h=db.archive(b'fee fixture')
        record={'Scheme_Name':'Test Small Cap Fund','SchemeCat_Desc':'Equity Scheme - Small Cap Fund','TER_Date':'2024-01-31T00:00:00','D_TER':'0.99','D_BER':'0.50','D_BrokerageCost':'0.00','D_StatutoryLevies':'','R_TER':'1.65'}
        count,_,_=save_fees([record],source,h)
        values={r['metric']:float(r['value']) for r in db.rows("SELECT * FROM metrics WHERE hash=? AND plan='Direct'",(h,))}
        self.assertEqual(values,{'ter':.99,'base_expense_ratio':.5,'brokerage':0})
        self.assertEqual(count,4)

    def test_expense_pagination_respects_server_page_cap(self):
        from tracker.amfi_metrics import fees
        import json
        first={'data':[{'Scheme_Name':'Not in this category'}]*100,'meta':{'page':1,'pageSize':100,'pageCount':2,'total':101}}
        last={'data':[{'Scheme_Name':'Not in this category'}],'meta':{'page':2,'pageSize':100,'pageCount':2,'total':101}}
        with patch('tracker.amfi_metrics.fetch',side_effect=[(json.dumps(first).encode(),'a','application/json'),(json.dumps(last).encode(),'b','application/json')]) as mock:
            fees(months=1)
            self.assertEqual(mock.call_count,2)
            self.assertIn('page=2',mock.call_args.args[0])

    def test_only_amc_publication_domains_are_accepted(self):
        self.assertTrue(disclosures.official_publication_url('https://files.hdfcfund.com/factsheet.pdf','HDFC'))
        self.assertFalse(disclosures.official_publication_url('https://news.example.com/hdfc-market-outlook','HDFC'))
        self.assertFalse(disclosures.official_publication_url('https://hdfcfund.com.evil.example/news','HDFC'))

    def test_github_archive_roundtrip_and_traversal_rejection(self):
        from scripts.github_state import pack,unpack
        import zipfile
        db.save_nav(1,[('2024-04-01',125)],providers.AMFI_NAV)
        h=db.archive(b'original official publication','application/pdf')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);archive=tmp/'state.zip';manifest=pack(archive)
            self.assertGreater(manifest['bytes'],0)
            restored=tmp/'restored';unpack(archive,restored)
            self.assertEqual((restored/'archive'/h[:2]/h).read_bytes(),b'original official publication')
            malicious=tmp/'bad.zip'
            with zipfile.ZipFile(malicious,'w') as z:z.writestr('../outside.txt','bad')
            with self.assertRaises(ValueError):unpack(malicious,tmp/'unsafe')
            self.assertFalse((tmp/'outside.txt').exists())

    def test_github_import_rejects_loss_of_existing_history(self):
        from scripts.github_state import pack,unpack
        from scripts.import_archive import check_superset
        import sqlite3
        db.save_nav(1,[('2024-05-01',126)],providers.AMFI_NAV)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);archive=tmp/'copy.zip';pack(archive);incoming=tmp/'incoming';unpack(archive,incoming)
            check_superset(db.DATA,incoming)
            with sqlite3.connect(incoming/'ledger.sqlite3') as c:c.execute("DELETE FROM nav WHERE date='2024-05-01'")
            with self.assertRaisesRegex(ValueError,'historical nav'):check_superset(db.DATA,incoming)

    def test_static_and_python_financial_calculations_agree(self):
        import json,math,subprocess
        start=date(2019,1,1)
        points=[[(start+timedelta(days=i)).isoformat(),100*1.08**(i/365.25)*(1+.1*math.sin(i/80))] for i in range(2000) if i%7 not in (5,6) and not 200<i<218]
        benchmark=[[d,v*2*(1+.04*math.sin(i/150))] for i,(d,v) in enumerate(points) if i%5]
        events=[{'ex_date':points[100][0],'amount':2,'reinvestment_nav':points[100][1]}]
        code="const a=require('./dist/analytics.js');const f=JSON.parse(require('fs').readFileSync(0,'utf8'));process.stdout.write(JSON.stringify({stats:a.performance(f.points),aligned:a.aligned(f.points,f.benchmark),sip:a.sip(f.points,1000),reinvested:a.reinvested(f.points,f.events,f.points[0][0],f.points.at(-1)[0])}));"
        r=subprocess.run(['node','-e',code],input=json.dumps({'points':points,'benchmark':benchmark,'events':events}),cwd=db.ROOT,text=True,capture_output=True,check=True)
        actual=json.loads(r.stdout);expected={'stats':analytics.performance(points),'aligned':analytics.aligned(points,benchmark),'sip':analytics.sip(points,1000),'reinvested':analytics.reinvested(points,events,points[0][0],points[-1][0])}
        def compare(a,b):
            if isinstance(b,dict):
                self.assertEqual(set(a),set(b))
                for k in b:compare(a[k],b[k])
            elif isinstance(b,(list,tuple)):
                self.assertEqual(len(a),len(b))
                for x,y in zip(a,b):compare(x,y)
            elif isinstance(b,(int,float)) and not isinstance(b,bool):self.assertAlmostEqual(a,b,places=7)
            else:self.assertEqual(a,b)
        compare(actual,expected)
        result=subprocess.run(['node','-e',"const a=require('./dist/analytics.js');console.log(JSON.stringify(a.response({option:'IDCW'},[['2024-01-01',100],['2024-02-01',95]],{data:[['2024-01-01',100],['2024-02-01',110]]})));"],cwd=db.ROOT,text=True,capture_output=True,check=True)
        idcw=json.loads(result.stdout);self.assertFalse(idcw['can_total_return']);self.assertEqual(idcw['comparison'],[]);self.assertIsNone(idcw['sip'])

    def test_partial_portfolio_is_not_a_sale_signal(self):
        h1=db.archive(b'first portfolio','text/csv');h2=db.archive(b'second portfolio','text/csv')
        disclosures.portfolio('Test Small Cap Fund','2024-01-31',[{'name':'Alpha','weight':4},{'name':'Beta','weight':3}],False,'https://example.com/p1',h1)
        sid=disclosures.portfolio('Test Small Cap Fund','2024-02-29',[{'name':'Alpha','weight':5}],False,'https://example.com/p2',h2)
        r=self.client.get('/api/portfolios/'+str(sid)).json()
        beta=next(x for x in r['changes'] if x['name']=='Beta')
        self.assertEqual(beta['type'],'Left disclosed list')

    def test_rejected_metric_import_does_not_partially_write(self):
        before=db.one('SELECT COUNT(*) n FROM metrics')['n']
        r=self.client.post('/api/import',headers={'X-Smallcap-Client':'local'},data={'kind':'metrics','code':'1','source':'https://example.com/record'},files={'file':('test.csv',b'metric,plan,as_of,value\naum,All,2024-01-31,150\nter,Direct,2024-01-31,650\n','text/csv')})
        self.assertEqual(r.status_code,400);self.assertEqual(db.one('SELECT COUNT(*) n FROM metrics')['n'],before)

    def test_local_request_boundary(self):
        self.assertEqual(self.client.post('/api/settings',json={'auto_update':False}).status_code,403)
        self.assertEqual(self.client.get('/api/status',headers={'Host':'evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/settings',headers={'X-Smallcap-Client':'local','Origin':'https://evil.example'},json={'auto_update':False}).status_code,403)

    def test_archive_round_trip_and_backup(self):
        original=b'The original source bytes';h=db.archive(original,'text/plain')
        self.assertEqual(self.client.get('/api/archive/'+h).content,original)
        self.assertEqual(db.archive(original,'text/plain'),h)
        import zipfile,io
        r=self.client.get('/api/export/backup');self.assertEqual(r.status_code,200)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            self.assertIn('data/ledger.sqlite3',z.namelist());self.assertIn('RESTORE.txt',z.namelist())

    def test_health_and_static_assets(self):
        self.assertEqual(self.client.get('/api/health').json()['app'],'smallcap-ledger')
        for path in ['/','/app.js','/style.css','/favicon.svg']:
            self.assertEqual(self.client.get(path).status_code,200)

if __name__=='__main__':unittest.main()
