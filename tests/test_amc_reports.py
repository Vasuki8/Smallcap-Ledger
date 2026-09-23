import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tracker.report_parser import page_facts,owns_page,equity_positions,dated


class ReportParserTests(unittest.TestCase):
    def report(self,family,body):
        return family+'\nAn open-ended equity scheme predominantly investing in small cap stocks\n'+body

    def test_explicit_scheme_benchmark_labels_ignore_additional_benchmark(self):
        f='Test Small Cap Fund'
        text=self.report(f,'''Data as on August 31, 2026
#Benchmark Index: Nifty Smallcap 250 TRI Benchmark Riskometer Very High
Additional Benchmark Index: Nifty 50 TRI
Month End AUM: Rs. 100 Cr''')
        facts=page_facts(text,f)
        bench=[x for x in facts if x['metric']=='benchmark']
        self.assertEqual(bench,[{'metric':'benchmark','value':'Nifty Smallcap 250 TRI','plan':'All',
                                 'as_of':'2026-08-31','unit':'Reported'}])

    def test_benchmark_label_variants_cover_total_return_and_small_cap_spacing(self):
        f='Test Small Cap Fund'
        boi=self.report(f,'''Portfolio as on August 31, 2026
BENCHMARK^
NIFTY Smallcap 250 Total Return Index (TRI) (Tier 1)
Month End AUM: Rs. 100 Cr''')
        facts=page_facts(boi,f)
        self.assertEqual([x['value'] for x in facts if x['metric']=='benchmark'],
                         ['NIFTY Smallcap 250 Total Return Index (TRI)'])
        samco=self.report(f,'''Data as on August 31, 2026
Benchmark: Nifty Small Cap 250 TRI Additional Benchmark: Nifty 50 TRI
Month End AUM: Rs. 100 Cr''')
        facts=page_facts(samco,f)
        self.assertEqual([x['value'] for x in facts if x['metric']=='benchmark'],
                         ['Nifty Small Cap 250 TRI'])

    def test_scheme_benchmark_bse_label_is_trimmed_to_index_name(self):
        f='Test Small Cap Fund'
        text=self.report(f,'''Portfolio as on August 31, 2026
Scheme Benchmark - BSE 250 SmallCap Index (TRI) ^^ (Benchmark) is very high risk
Month End AUM: Rs. 100 Cr''')
        facts=page_facts(text,f)
        bench=next(x for x in facts if x['metric']=='benchmark')
        self.assertEqual(bench['value'],'BSE 250 SmallCap Index (TRI)')

    def test_month_end_not_average_or_nav_day(self):
        text=self.report('Test Small Cap Fund','Details as on May 31, 2026\nNAV as on May 29, 2026\nMonth End: Rs. 1200 Cr\nMonthly Average AUM 1190 Cr\nBase Expense Ratio\nRegular 1.20\nDirect 0.40')
        facts=page_facts(text,'Test Small Cap Fund')
        self.assertEqual({x['as_of'] for x in facts},{'2026-05-31'})
        self.assertEqual(next(x['value'] for x in facts if x['metric']=='aum'),1200)
        self.assertEqual(next(x['value'] for x in facts if x['metric']=='average_aum'),1190)
        self.assertNotIn('ter',[x['metric'] for x in facts])

    def test_canara_date_and_plan_columns(self):
        f='Canara Robeco Small Cap Fund'
        text=self.report(f,'#Month end AUM as on 31.07 .2026\nMonth end Assets Under Management (AUM)# ` 14,230.88 Crores\nBASE EXPENSE RATIO (BER)^:\nRegular Plan (%) 1.46\nDirect Plan (%) 0.44')
        facts=page_facts(text,f)
        self.assertEqual(facts[0]['as_of'],'2026-07-31')
        self.assertEqual(facts[0]['value'],14230.88)
        self.assertEqual([(x['plan'],x['value']) for x in facts[1:]],[('Regular',1.46),('Direct',.44)])

    def test_invesco_dated_aum_and_distinct_ber(self):
        f='Invesco India Small Cap Fund'
        text=self.report('Invesco India Smallcap Fund','AuM as on\n31st July, 2026: ₹ 14474.79 crores\nSCHEME BENCHMARK\nAs per AMFI Tier I Benchmark i.e. BSE 250 Small Cap Index TRI\nBase Expense Ratio\nRegular 1.45%\nDirect 0.41%')
        facts=page_facts(text,f)
        self.assertEqual(next(x['value'] for x in facts if x['metric']=='aum'),14474.79)
        self.assertEqual(next(x['value'] for x in facts if x['metric']=='benchmark'),'BSE 250 Smallcap TRI')
        self.assertEqual(len(facts),4)

    def test_combined_ber_ter_columns(self):
        f='Edelweiss Small Cap Fund'
        text=self.report(f,'Data as on July 31, 2026\nMonth End AUM (₹) : 6,825 Cr.\nBER / TER (Regular Plan) : 1.55%/1.94%\nBER / TER (Direct Plan) : 0.44%/0.65%')
        values={(x['metric'],x['plan']):x['value'] for x in page_facts(text,f)}
        self.assertEqual(values[('base_expense_ratio','Direct')],.44)
        self.assertEqual(values[('ter','Direct')],.65)

    def test_hsbc_parenthesized_short_date(self):
        f='HSBC Small Cap Fund'
        facts=page_facts(self.report(f,'AUM (as on 31.07.26) ₹ 17,783.74 Cr.'),f)
        self.assertEqual(facts[0]['value'],17783.74)
        self.assertEqual(facts[0]['as_of'],'2026-07-31')

    def test_quant_pdf_spaced_labels(self):
        f='Quant Small Cap Fund'
        facts=page_facts(self.report(f,'A UM (31 A ugust 2026): Rs. 35,557.21 Cr\nA A UM (31 A ugust 2026): Rs. 35,039.58 Cr'),f)
        self.assertEqual([(x['metric'],x['value']) for x in facts],[('aum',35557.21),('average_aum',35039.58)])

    def test_samco_separate_label_and_value_rows(self):
        f='Samco Small Cap Fund'
        facts=page_facts(self.report(f,'AUM as on 31-Aug-2026\nAAUM for Month of Aug-2026\n196.45 Crs\n184.94 Crs'),f)
        self.assertEqual([(x['metric'],x['value']) for x in facts],[('aum',196.45),('average_aum',184.94)])

    def test_bandhan_month_end_and_average_aum(self):
        f='Bandhan Small Cap Fund'
        text=self.report(f,'Details as on August 31, 2026\nMonthly Avg AUM: ₹ 33,251.44 Crores\nMonth end AUM: ₹ 34,176.00 Crores\nNAV as on August 31, 2026')
        values={(x['metric'],x['plan']):(x['value'],x['as_of']) for x in page_facts(text,f)}
        self.assertEqual(values[('aum','All')],(34176.00,'2026-08-31'))
        self.assertEqual(values[('average_aum','All')],(33251.44,'2026-08-31'))

    def test_candidate_links_reads_embedded_documents(self):
        from bs4 import BeautifulSoup
        from tracker.providers import candidate_links
        soup=BeautifulSoup('<iframe src="/wp-content/uploads/bandhan-factsheet.pdf#page=1"></iframe><div data-file="/wp-content/uploads/bandhan-small-cap.xlsx"></div><iframe src="https://viewer.example/view?url=https%3A%2F%2Fcmsnew.bandhanmutual.com%2Fwp-content%2Fuploads%2Fportfolio.pdf"></iframe>','html.parser')
        links=candidate_links(soup,'https://cmsnew.bandhanmutual.com/monthly-factsheets-2026/')
        self.assertIn('https://cmsnew.bandhanmutual.com/wp-content/uploads/bandhan-factsheet.pdf#page=1',links)
        self.assertIn('https://cmsnew.bandhanmutual.com/wp-content/uploads/bandhan-small-cap.xlsx',links)
        self.assertIn('https://cmsnew.bandhanmutual.com/wp-content/uploads/portfolio.pdf',links)

    def test_parser_upgrade_pending_query_retains_family_identity(self):
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn('SELECT DISTINCT d.family,d.url,v.hash FROM documents d',source)
        workflow=(Path(__file__).resolve().parents[1]/'.github'/'workflows'/'daily.yml').read_text()
        upgrade=workflow.split('- name: Apply official AMC report collector upgrade',1)[1].split('- name: Collect daily data',1)[0]
        self.assertNotIn('continue-on-error: true',upgrade)

    def test_parser_upgrade_does_not_duplicate_daily_amc_discovery(self):
        root=Path(__file__).resolve().parents[1]
        upgrade=(root/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertNotIn('amc_discovery.update(',upgrade)
        sync=(root/'tracker'/'sync.py').read_text()
        self.assertIn('amc_discovery.update',sync)

    def test_v24_parser_upgrade_targets_only_edelweiss(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v24'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Edelweiss Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bank Of India Small Cap Fund'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("rows=[row for row in rows if amc_reports.parser_upgrade_applies(row['family'])]",source)
        self.assertIn("amc_reports.parser_upgrade_applies(row['family'])",source)

    def test_boi_pdf_is_opted_into_targeted_historical_reprocess(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v24'):
            self.assertTrue(amc_reports.should_reprocess_existing(
                'Bank Of India Small Cap Fund',
                'https://www.boimf.in/docs/factsheet-august-2026.pdf?x=1'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Edelweiss Small Cap Fund',
                'https://www.edelweissmf.com/factsheet-september-2026.pdf'))
            self.assertTrue(amc_reports.should_reprocess_existing(
                'Samco Small Cap Fund',
                'https://www.samcomf.com/portfolio.xlsx'))

    def test_v45_parser_upgrade_targets_only_union(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v45'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Union Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bandhan Small Cap Fund'))
            self.assertTrue(amc_reports.should_reprocess_existing(
                'Union Small Cap Fund',
                'https://www.unionmf.com/docs/default-source/downloads/scheme-disclosures/factsheets/factsheet-march-2026.pdf'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Quant Small Cap Fund',
                'https://quantmutual.com/Admin/Factsheet/factsheet.pdf'))

    def test_v46_targets_only_benchmark_recovery_families(self):
        from tracker import amc_reports
        expected={
            'Bank Of India Small Cap Fund','Baroda Bnp Paribas Small Cap Fund',
            'Franklin India Small Cap Fund','Groww Small Cap Fund',
            'Invesco India Small Cap Fund','LIC Mf Small Cap Fund',
            'Pgim India Small Cap Fund',
            'Samco Small Cap Fund','Tata Small Cap Fund',
            'The Wealth Company Small Cap Fund','UTI Small Cap Fund',
        }
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v46'):
            for family in expected:
                self.assertTrue(amc_reports.parser_upgrade_applies(family))
                self.assertFalse(amc_reports.should_reprocess_existing(
                    family,'https://example.com/factsheet.pdf','hash'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Union Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bandhan Small Cap Fund'))

    def test_v47_targets_only_post_v46_benchmark_sources(self):
        from tracker import amc_reports
        expected={'Invesco India Small Cap Fund','The Wealth Company Small Cap Fund'}
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v47'):
            for family in expected:
                self.assertTrue(amc_reports.parser_upgrade_applies(family))
                self.assertFalse(amc_reports.should_reprocess_existing(
                    family,'https://example.com/factsheet.pdf','hash'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bandhan Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Union Small Cap Fund'))

    def test_union_transport_audit_does_not_retry_every_push(self):
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("transport_audit_complete=(amc_reports.PARSER_VERSION=='amc-reports-2026-09-v45' and not gaps)",source)
        self.assertIn("if (all(ok) or transport_audit_complete) and not gaps:",source)

    def test_union_catalog_keeps_reviewed_omnibus_fallback(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'tracker'/'report_catalog.json').read_text())
        urls=[row['url'] for row in rows if row['family']=='Union Small Cap Fund']
        self.assertIn(
            'https://www.unionmf.com/docs/default-source/downloads/scheme-disclosures/factsheets/factsheet-march-2026.pdf?sfvrsn=3ddcc4de_5',
            urls)

    def test_bandhan_wordpress_attachment_discovery_uses_official_media(self):
        from tracker.amc_discovery import discover
        post=[{
            'content':{'rendered':'<p>Monthly portfolio disclosure</p>'},
            '_links':{'wp:attachment':[{'href':'https://cmsnew.bandhanmutual.com/wp-json/wp/v2/media?parent=123'}]}
        }]
        media=[
            {'source_url':'https://cmsnew.bandhanmutual.com/wp-content/uploads/2026/09/Bandhan-Small-Cap-Portfolio-August-2026.xlsx',
             'title':{'rendered':'Bandhan Small Cap Portfolio August 2026'}},
            {'source_url':'https://cmsnew.bandhanmutual.com/wp-content/uploads/2026/09/Bandhan-Small-Cap-Portfolio-August-2026.pdf',
             'title':{'rendered':'Bandhan Small Cap Portfolio August 2026'}},
        ]
        def fake_read(url,body=None):
            if '/wp-json/wp/v2/posts?' in url:return (json.dumps(post).encode(),'h','application/json')
            if '/wp-json/wp/v2/media?' in url:return (json.dumps(media).encode(),'m','application/json')
            return (b'<html></html>','p','text/html')
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('Bandhan'))
        self.assertEqual(rows[0][0],'Bandhan Small Cap Fund')
        self.assertTrue(rows[0][1].endswith('.xlsx'))
        self.assertTrue(all('bandhanmutual.com' in x[1] for x in rows))

    def test_trust_monthly_disclosure_api_prefers_latest_structured_file(self):
        from tracker.amc_discovery import discover
        calls=[]
        def fake_read(url,body=None):
            calls.append(body)
            tag=(body or {}).get('tagName')
            if tag=='GetOneProductWeb':
                return (json.dumps({'resultSetArray':[]}).encode(),'product','application/json')
            if tag=='GetDownloadsForProductWeb':
                return (json.dumps({'resultSetArray':[]}).encode(),'downloads','application/json')
            if tag=='GetDisclosureByType':
                rows=[
                    {'title':'Monthly Portfolio Disclosure as on 31.07.2026',
                     'fileurl':'/uploads/TRUSTMF-Portfolio-July-2026.xlsx'},
                    {'title':'Monthly Portfolio Disclosure as on 31.08.2026',
                     'fileurl':'/uploads/TRUSTMF-Portfolio-August-2026.pdf'},
                    {'title':'Monthly Portfolio Disclosure as on 31.08.2026',
                     'fileurl':'/uploads/TRUSTMF-Portfolio-August-2026.xlsx'},
                ]
                return (json.dumps({'resultSetArray':rows}).encode(),'portfolio','application/json')
            raise AssertionError(tag)
        with patch('tracker.amc_discovery.read',side_effect=fake_read):
            rows=list(discover('TRUST'))
        self.assertEqual(rows[0][0],'Trustmf Small Cap Fund')
        self.assertTrue(rows[0][1].endswith('TRUSTMF-Portfolio-August-2026.xlsx'))
        self.assertTrue(all('31.08.2026' in row[2] for row in rows))
        payload=next(x for x in calls if x and x.get('tagName')=='GetDisclosureByType')
        self.assertEqual(payload['systemQueryFileName'],'disclosuresweb.xml')
        self.assertEqual(payload['replaceValue'],'portfolio-monthly-disclosure')

    def test_tata_portfolio_discovery_prefers_latest_monthly_excel(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <div>Monthly Portfolio August 2026
          <a data-file="/system/files/2026-09/Tata_Monthly_Portfolio_August_2026.xlsx">Excel</a>
          <a href="/system/files/2026-09/Tata_Monthly_Portfolio_August_2026.pdf">PDF</a>
        </div>
        <div>Monthly Portfolio July 2026
          <a href="/system/files/2026-08/Tata_Monthly_Portfolio_July_2026.xlsx">Excel</a>
        </div>
        <div>Fortnightly Portfolio August 2026
          <a href="/system/files/2026-09/Tata_Fortnightly_Portfolio_August_2026.xlsx">Excel</a>
        </div>
        <div>Press Release to create a segregated portfolio in 3 schemes
          <a href="/system/files/2023-06/dhfl_update_press_release_07062019.pdf">PDF</a>
        </div>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'hash','text/html')):
            rows=list(discover('Tata'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],'Tata Small Cap Fund')
        self.assertEqual(rows[0][1],
            'https://www.tatamutualfund.com/system/files/2026-09/Tata_Monthly_Portfolio_August_2026.xlsx')

    def test_v27_replays_only_edelweiss_pdfs(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v27'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Edelweiss Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bank Of India Small Cap Fund'))
            self.assertTrue(amc_reports.should_reprocess_existing(
                'Edelweiss Small Cap Fund',
                'https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026.pdf',
                'archived'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Edelweiss Small Cap Fund',
                'https://www.edelweissmf.com/portfolio.xlsx',
                'archived'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Bank Of India Small Cap Fund',
                'https://www.boimf.in/factsheet.pdf',
                'archived'))

    def test_v26_quantity_reprocess_is_limited_to_retained_workbook_hashes(self):
        from tracker import amc_reports,db
        family='HDFC Small Cap Fund'
        url='https://files.hdfcfund.com/current.xlsx'
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v26'):
            self.assertFalse(amc_reports.should_reprocess_existing(family,url,'missing'))
            with db.connect() as c:
                c.execute("""INSERT INTO portfolios(family,as_of,complete,source,hash,observed_at)
                  VALUES(?,?,?,?,?,?)""",(family,'2026-08-31',1,url,'retained',db.now()))
            self.assertTrue(amc_reports.should_reprocess_existing(family,url,'retained'))
            self.assertFalse(amc_reports.should_reprocess_existing(family,'https://files.hdfcfund.com/old.pdf','retained'))

    def test_quant_statutory_discovery_prefers_monthly_portfolio_files(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <div>MONTHLY PORTFOLIO - FUND - WISE
          <div>Aug 2026 <a data-file="/Admin/Portfolio/quant_Small_Cap_Fund_Aug_2026.xlsx">Download</a></div>
        </div>
        <div>MONTHLY PORTFOLIO
          <a href="/Admin/Portfolio/Monthly_Portfolio_All_Schemes_August_2026.xlsx">2026</a>
        </div>
        <div>Other disclosure <a href="/Admin/Notice/notice.pdf">Notice</a></div>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'hash','text/html')):
            rows=list(discover('quant Mutual'))
        self.assertEqual(len(rows),2)
        urls=[x[1] for x in rows]
        self.assertIn('https://quantmutual.com/Admin/Portfolio/quant_Small_Cap_Fund_Aug_2026.xlsx',urls)
        self.assertIn('https://quantmutual.com/Admin/Portfolio/Monthly_Portfolio_All_Schemes_August_2026.xlsx',urls)
        self.assertTrue(all(x[0]=='Quant Small Cap Fund' for x in rows))

    def test_catalog_amc_resolver_handles_long_names_without_quantum_collision(self):
        from tracker.disclosures import resolve_registered_amc
        sources=[
            ['Bajaj','https://www.bajajamc.com/','Fund house'],
            ['Canara','https://www.canararobeco.com/','Fund house'],
            ['HSBC','https://www.assetmanagement.hsbc.co.in/','Fund house'],
            ['quant Mutual','https://quantmutual.com/','Fund house'],
            ['Quantum','https://www.quantumamc.com/','Fund house'],
        ]
        self.assertEqual(resolve_registered_amc('Bajaj Finserv Mutual Fund',sources),'Bajaj')
        self.assertEqual(resolve_registered_amc('Canara Robeco Mutual Fund',sources),'Canara')
        self.assertEqual(resolve_registered_amc('HSBC Mutual Fund',sources),'HSBC')
        self.assertEqual(resolve_registered_amc('quant Mutual Fund',sources),'quant Mutual')
        self.assertEqual(resolve_registered_amc('Quantum Mutual Fund',sources),'Quantum')
        ambiguous=[['Alpha','https://a.example/',''],['Beta','https://b.example/','']]
        self.assertIsNone(resolve_registered_amc('Alpha Beta Mutual Fund',ambiguous))

    def test_lic_complete_portfolio_reconciles_wrapped_sector_and_cash(self):
        from tracker.report_parser import lic_complete_portfolio
        holdings='\n'.join(f'Example Company {i} Ltd. 4.7015%' for i in range(1,21))
        text='''LIC MF SMALL CAP FUND
Scheme Type: Small Cap Fund - An open-ended equity scheme predominantly investing in small cap stocks.
Inception/Allotment Date: June 21, 2017
First Tier Benchmark: Nifty Smallcap 250 - TRI
PORTFOLIO as on 31/03/2026
Company % of NAV
Equity Holdings
Agricultural, Commercial & Construction
Vehicles
94.03%
'''+holdings+'''
Equity Holdings Total 94.03%
Cash & Other Receivables Total 5.97%
Top 10 holdings Grand Total 100.00%'''
        parsed=lic_complete_portfolio(text)
        self.assertEqual(parsed['day'],'2026-03-31')
        self.assertEqual(parsed['benchmark'],'Nifty Smallcap 250 - TRI')
        self.assertEqual(len(parsed['positions']),21)
        self.assertEqual(parsed['positions'][0]['sector'],'Agricultural, Commercial & Construction Vehicles')
        self.assertEqual(parsed['positions'][-1]['asset_type'],'Cash and net current assets')
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100)
        wrong=text.replace('Small Cap Fund','Mid Cap Fund').replace('Smallcap 250','Midcap 150').replace('June 21, 2017','January 25, 2017')
        self.assertIsNone(lic_complete_portfolio(wrong))

    def test_quantum_fee_footnote_is_preserved(self):
        f='Quantum Small Cap Fund'
        text=self.report(f,'Scheme Portfolio as on July 31, 2026\nAUM ₹ (In Crores)\nAbsolute AUM: 254.14\nDirect Plan – Total TER 0.70%\nTotal Expense ratio inclusive of transaction cost please click the link')
        values={x['metric']:x['value'] for x in page_facts(text,f)}
        self.assertNotIn('ter',values)
        self.assertEqual(values['ter_excluding_transaction_cost'],.70)

    def test_reject_index_fund_holding_and_future_report(self):
        f='Test Small Cap Fund'
        wrong=self.report('Test Nifty Smallcap 250 Index Fund','Month End: Rs. 100 Cr\nData as on July 31, 2026\nHoldings\nTest Small Cap Fund\n2.0')
        self.assertEqual(page_facts(wrong,f),[])
        self.assertEqual(page_facts(self.report(f,'AUM as on July 31, 2099: Rs. 100 Cr\nNAV as on July 31, 2026'),f),[])

    def test_equity_table_excludes_sector_totals(self):
        f='Canara Robeco Small Cap Fund'
        text=self.report(f,'Name of the Instruments Market Cap % of NAV\nBanks 5.0%\nAlpha Bank Ltd S 2.0%\nBeta Bank Limited M 3.0%\nGrand Total 100.0%\nTOP 10 INDUSTRIES\nBanks 5.0%')
        positions=equity_positions(text,f)
        self.assertEqual([x['name'] for x in positions],['Alpha Bank Ltd','Beta Bank Limited'])
        self.assertEqual(sum(x['weight'] for x in positions),5)

    def test_month_rollover_and_no_url_date_inference(self):
        from datetime import date
        from tracker.amc_reports import monthly_sources
        sources=list(monthly_sources(date(2026,1,5)))
        canara=[url for amc,url,_ in sources if amc=='Canara']
        sbi=[url for amc,url,_ in sources if amc=='SBI']
        self.assertEqual(len(canara),3)
        self.assertIn('/2025/november/',canara[-1])
        self.assertIn('november-2025.pdf',sbi[-1])
        self.assertEqual(page_facts(self.report('Test Small Cap Fund','Month End: Rs. 100 Cr'),'Test Small Cap Fund'),[])

    def test_motilal_explicit_aum_date_and_average(self):
        f='Motilal Oswal Small Cap Fund'
        text=self.report(f,'Latest AUM (31-July-2026) (in Rs Crs.) 7,604.53\nMonthly AAUM (31 -July-2026) (in Rs Crs.) 7,421.54\nData as on 4 September, 2026')
        facts=page_facts(text,f)
        self.assertEqual([(x['metric'],x['value'],x['as_of']) for x in facts],[('aum',7604.53,'2026-07-31'),('average_aum',7421.54,'2026-07-31')])

    def test_mirae_crore_units_and_reject_multi_fund_snapshot(self):
        f='Mirae Asset Small Cap Fund'
        text=self.report(f,'Monthly Factsheet as on 31 July, 2026\nNet AUM (Cr.) 5,220.93\nBase Expense Ratio\nRegular Plan 1.60%\nDirect Plan 0.34%')
        facts=page_facts(text,f)
        self.assertEqual(facts[0]['value'],5220.93)
        self.assertEqual(facts[-1]['metric'],'base_expense_ratio')
        self.assertEqual(page_facts('Mirae Asset Equity Snapshot\n'+text,f),[])

    def test_sbi_inr_not_usd_and_ter_not_ber(self):
        f='SBI Small Cap Fund'
        text=self.report(f,'FUND DETAILS AS ON 31/07/2026\nFund Size ` in Cr. $ in Mn.\nMonth end AUM 39,942.33 4,188.12\nMonthly Avg. AUM 40,368.60 4,232.81\nExpense Ratio\nPlan Regular Direct\nTER 1.57 0.74\nBER 1.29 0.57\nBenchmark BSE 250 Small Cap\nIndex TRI')
        values={(x['metric'],x['plan']):x['value'] for x in page_facts(text,f)}
        self.assertEqual(values[('aum','All')],39942.33)
        self.assertEqual(values[('ter','Direct')],.74)
        self.assertEqual(values[('base_expense_ratio','Direct')],.57)
        self.assertEqual(values[('benchmark','All')],'BSE 250 Small Cap Index TRI')

    def test_sbi_wrapped_equities_exclude_cash_and_sector_rows(self):
        f='SBI Small Cap Fund'
        text=self.report(f,'Company/ Issuer Rating Net% To AUM\nEQUITY SHARES\nCHEMICALS\nAlpha Fertilizers And Petrochemicals\nCorporation Ltd 2.04\nPOWER\nBeta Ltd 2.17\nTOTAL 4.21\nTREASURY BILLS\nCASH 95.79')
        positions=equity_positions(text,f)
        self.assertEqual([x['name'] for x in positions],['Alpha Fertilizers And Petrochemicals Corporation Ltd','Beta Ltd'])
        self.assertAlmostEqual(sum(x['weight'] for x in positions),4.21)

    def test_samco_wrapped_portfolio_reconciles_named_derivatives_and_treps(self):
        from tracker.portfolio_parser import parse_sheet
        f='Samco Small Cap Fund'
        rows=[
            ['SAMCO MUTUAL FUND',None,None,None,None,None,None,None],
            [None]*8,
            ['MONTHLY PORTFOLIO STATEMENT OF SAMCO SMALL CAP FUND AS ON August 31, 2026',None,None,None,None,None,None,None],
            [None]*8,
            ['Name of the Instrument',None,'ISIN','Industry','Quantity','Market/Fair Value (Rs. in Lakhs)','% to Net\n Assets','YTM'],
            ['Equity & Equity related',None,None,None,None,None,None,None],
            ['AENP01','Ather Energy Limited','INE0LEZ01016','Automobiles',100,50,0.50,None],
            [None,'Derivatives',None,None,None,None,None,None],
            [None,'Index / Stock Futures',None,None,None,None,None,None],
            ['ABFSSEP26','Aditya Birla Capital Limited September 2026 Future',None,'Finance',100,20,0.20,None],
            [None,'Reverse Repo / TREPS',None,None,None,None,None,None],
            ['TRP_010926','Clearing Corporation of India Ltd',None,None,None,40,0.40,None],
            [None,'Net Receivables / (Payables)',None,None,None,-10,-0.10,None],
            [None,'GRAND TOTAL',None,None,None,100,1.00,None],
        ]
        formats=[['']*8 for _ in rows]
        for i in (6,9,11,12,13):formats[i][6]='0.00%'
        parsed=parse_sheet(rows,formats,f)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertTrue(parsed['complete'])
        self.assertEqual(parsed['aum'],1.0)
        self.assertEqual([x['name'] for x in parsed['positions']],[
            'Ather Energy Limited','Aditya Birla Capital Limited September 2026 Future',
            'Clearing Corporation of India Ltd','Net Receivables / (Payables)'])
        self.assertEqual([x['asset_type'] for x in parsed['positions']],[
            'Equity','Derivative','Money market','Cash and net current assets'])
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100)


    def test_baroda_discovery_prefers_latest_all_funds_workbook(self):
        from tracker import amc_discovery,db
        db.init()
        html='''<ul>
        <li>31st July 2026 <a href="/assets/download_documents/BOBBNPMF_Monthly_Portfolio_31-07-2026_19000.xls">Download</a></li>
        <li>31st August 2026 <a href="/assets/download_documents/BOBBNPMF_Monthly_Portfolio_31-08-2026_19961.xls">Download</a></li>
        <li>Baroda BNP Paribas Large Cap Fund 31st August 2026 <a href="/assets/download_documents/YR56_19960.xlsx">Download</a></li>
        </ul>'''.encode()
        with patch('tracker.amc_discovery.read',return_value=(html,'fixture','text/html')):
            rows=list(amc_discovery.discover('Baroda'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][:2],('Baroda Bnp Paribas Small Cap Fund','https://www.barodabnpparibasmf.in/assets/download_documents/BOBBNPMF_Monthly_Portfolio_31-08-2026_19961.xls'))


    def test_pgim_discovery_uses_official_monthly_factsheet_paths(self):
        from tracker import amc_discovery
        with patch('tracker.amc_discovery.date') as fake:
            fake.today.return_value=__import__('datetime').date(2026,9,22)
            rows=list(amc_discovery.discover('PGIM'))
        self.assertEqual(rows,[
            ('Pgim India Small Cap Fund','https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet - August 2026.pdf','Factsheet - August 2026'),
            ('Pgim India Small Cap Fund','https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet - July 2026.pdf','Factsheet - July 2026'),
        ])


    def test_samco_discovery_prefers_latest_smallcap_excel(self):
        from tracker import amc_discovery,db
        db.init()
        html='''<table>
        <tr><td>IN_MF_MONTHLY_PORTFOLIO_July_2026_Samco_ Small_Cap_ Fund</td><td><a href="https://media1.samco.in/july-small-cap.xlsx">Excel</a></td></tr>
        <tr><td>IN_MF_MONTHLY_PORTFOLIO_August_2026_Samco_ Small_Cap_ Fund</td><td><a href="https://media1.samco.in/aug-small-cap.pdf">PDF</a><a href="https://media1.samco.in/aug-small-cap.xlsx">Excel</a></td></tr>
        <tr><td>IN_MF_MONTHLY_PORTFOLIO_August_2026_Samco_Flexicap_Fund</td><td><a href="https://media1.samco.in/aug-flexi.xlsx">Excel</a></td></tr>
        </table>'''.encode()
        with patch('tracker.amc_discovery.read',return_value=(html,'fixture','text/html')):
            rows=list(amc_discovery.discover('Samco'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][:2],('Samco Small Cap Fund','https://media1.samco.in/aug-small-cap.xlsx'))
        self.assertIn('Small_Cap_ Fund',rows[0][2])

    def test_official_motilal_download_fields_with_or_without_colon(self):
        from bs4 import BeautifulSoup
        from tracker.providers import candidate_links
        soup=BeautifulSoup('<ul><li><strong>brochurepdf</strong>/content/dam/motilal-mf/report.pdf</li><li><strong>portfolioUrl:</strong> /content/dam/motilal-mf/portfolio.xlsx</li><li><strong>latestFactsheetPdf</strong>https://third-party.example/factsheet.pdf</li></ul>','html.parser')
        links=candidate_links(soup,'https://www.motilaloswalmf.com/mutual-funds/motilal-oswal-small-cap-fund')
        self.assertEqual(set(links),{'https://www.motilaloswalmf.com/content/dam/motilal-mf/report.pdf','https://www.motilaloswalmf.com/content/dam/motilal-mf/portfolio.xlsx'})


if __name__=='__main__':unittest.main()
