import io
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tracker.report_parser import page_facts,owns_page,equity_positions,dated


class ReportParserTests(unittest.TestCase):
    def report(self,family,body):
        return family+'\nAn open-ended equity scheme predominantly investing in small cap stocks\n'+body

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
        text=self.report('Invesco India Smallcap Fund','AuM as on\n31st July, 2026: ₹ 14474.79 crores\nBase Expense Ratio\nRegular 1.45%\nDirect 0.41%')
        facts=page_facts(text,f)
        self.assertEqual(facts[0]['value'],14474.79)
        self.assertEqual(len(facts),3)

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
