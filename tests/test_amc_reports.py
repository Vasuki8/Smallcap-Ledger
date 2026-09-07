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
        self.assertEqual(len(sources),6)
        self.assertIn('/2025/november/',sources[-2][1])
        self.assertEqual(page_facts(self.report('Test Small Cap Fund','Month End: Rs. 100 Cr'),'Test Small Cap Fund'),[])


if __name__=='__main__':unittest.main()
