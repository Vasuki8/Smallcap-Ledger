import io
import json
import unittest
from datetime import date
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
        self.assertEqual(next(x['value'] for x in facts if x['metric']=='benchmark'),'BSE 250 Small Cap Index TRI')
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

    def test_august_refresh_catalog_has_current_hsbc_and_pgim_sources(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'tracker'/'report_catalog.json').read_text())
        urls={(row['family'],row['url']) for row in rows}
        self.assertIn(('HSBC Small Cap Fund',
            'https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf'),urls)
        self.assertIn(('Pgim India Small Cap Fund',
            'https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet%20-%20August%202026.pdf'),urls)

    def test_v50_catalog_phase_uses_verified_september_sources(self):
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("current_catalog={",source)
        self.assertIn("Abakkus_Fund_Spectrum_Sep_2026_0d434fa086.pdf",source)
        self.assertIn("absl-factsheet_sep-2026.pdf",source)
        self.assertIn("lic-mf-factsheet-31st-august-2026.pdf",source)
        self.assertNotIn("'https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet%20-%20August%202026.pdf',\n        }",source)
        self.assertIn("rows=[row for row in rows if row['url'] in current_catalog]",source)

    def test_v52_reparses_groww_after_scheme_code_fix(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v52'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Groww Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Quant Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Groww Small Cap Fund','https://example.com/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("'amc-reports-2026-09-v52'",source)

    def test_v51_targets_current_groww_monthly_portfolio(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v51'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Groww Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Quant Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Groww Small Cap Fund','https://example.com/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("amc_discovery.discover('Groww')",source)
        self.assertIn("snap['as_of']>='2026-08-31' and snap['positions']>=20",source)

    def test_v50_supersedes_both_complete_refresh_batches(self):
        from tracker import amc_reports
        expected={
            'Abakkus Small Cap Fund','Aditya Birla Sun Life Small Cap Fund',
            'Franklin India Small Cap Fund','HSBC Small Cap Fund',
            'LIC Mf Small Cap Fund','Pgim India Small Cap Fund',
        }
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v50'):
            for family in expected:
                self.assertTrue(amc_reports.parser_upgrade_applies(family))
                self.assertFalse(amc_reports.should_reprocess_existing(
                    family,'https://example.com/factsheet.pdf','hash'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Groww Small Cap Fund'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        for pair in (
            "('Abakkus','Abakkus Small Cap Fund')",
            "('Aditya Birla','Aditya Birla Sun Life Small Cap Fund')",
            "('Franklin','Franklin India Small Cap Fund')",
            "('HSBC','HSBC Small Cap Fund')",
            "('LIC','LIC Mf Small Cap Fund')",
            "('PGIM','Pgim India Small Cap Fund')",
        ):
            self.assertIn(pair,source)
        self.assertIn("'HSBC Small Cap Fund'",source)
        self.assertIn("'Pgim India Small Cap Fund'",source)
        self.assertIn("snap['as_of']>='2026-08-31' and snap['complete']",source)

    def test_v49_targets_current_complete_portfolio_refresh(self):
        from tracker import amc_reports
        expected={'Abakkus Small Cap Fund','HSBC Small Cap Fund','Pgim India Small Cap Fund'}
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v49'):
            for family in expected:
                self.assertTrue(amc_reports.parser_upgrade_applies(family))
                self.assertFalse(amc_reports.should_reprocess_existing(
                    family,'https://example.com/factsheet.pdf','hash'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Franklin India Small Cap Fund'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("amc_discovery.discover('Abakkus')",source)
        self.assertIn("snap['as_of']>='2026-08-31' and snap['complete']",source)
        self.assertIn("'HSBC Small Cap Fund','Pgim India Small Cap Fund'",source)

    def test_v48_targets_only_live_benchmark_pages(self):
        from tracker import amc_reports
        expected={'Bank Of India Small Cap Fund','Invesco India Small Cap Fund','Samco Small Cap Fund'}
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v48'):
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

    def test_v125_targets_only_trustmf_current_structured_portfolio(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v125'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Trustmf Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Tata Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Trustmf Small Cap Fund','https://trustmf.com/Content/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("'amc-reports-2026-09-v125'",source)
        self.assertIn("amc_discovery.discover('TRUST')",source)
        self.assertIn("path.lower().endswith(('.xls','.xlsx'))",source)

    def test_v126_targets_only_sundaram_richer_partial(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v126'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Sundaram Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Trustmf Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Sundaram Small Cap Fund','https://www.sundarammutual.com/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("'amc-reports-2026-09-v126'",source)
        self.assertIn("amc_discovery.discover('Sundaram')",source)
        self.assertIn("snap['positions']>=77",source)
        self.assertIn("not snap['complete']",source)

    def test_invesco_complete_monthly_api_selects_two_closed_smallcap_workbooks(self):
        from tracker.amc_discovery import invesco_complete_monthly
        calls=[]
        rows=[{
            'Name':'Invesco India Small Cap Fund',
            'JulUrl':'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/july.xlsx?sfvrsn=1',
            'AugUrl':'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/august.xlsx?sfvrsn=2',
            'JulName':'07/26','AugName':'08/26',
        },{
            'Name':'Invesco India Mid Cap Fund',
            'JulUrl':'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/wrong-july.xlsx',
            'AugUrl':'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/wrong-august.xlsx',
            'JulName':'07/26','AugName':'08/26',
        }]
        def fake_read(url,body=None):
            calls.append(url)
            self.assertIn('year=2026&classification=equity',url)
            return (json.dumps(rows).encode(),'api','application/json')
        found=list(invesco_complete_monthly(fake_read,date(2026,9,24)))
        self.assertEqual(found,[
            ('Invesco India Small Cap Fund',
             'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/august.xlsx?sfvrsn=2',
             'Complete monthly holdings 08/26'),
            ('Invesco India Small Cap Fund',
             'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/july.xlsx?sfvrsn=1',
             'Complete monthly holdings 07/26'),
        ])
        self.assertEqual(len(calls),1)

    def test_invesco_closed_month_discovery_handles_year_rollover_and_rejects_bad_host(self):
        from tracker.amc_discovery import closed_month_ends,invesco_complete_monthly
        self.assertEqual(list(closed_month_ends(date(2027,1,5),2)),
                         [date(2026,12,31),date(2026,11,30)])
        rows=[{
            'Name':'Invesco India Small Cap Fund',
            'NovUrl':'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/nov.xlsx',
            'DecUrl':'https://example.com/dec.xlsx',
            'NovName':'11/26','DecName':'12/26',
        }]
        def fake_read(url,body=None):
            return (json.dumps(rows).encode(),'api','application/json')
        found=list(invesco_complete_monthly(fake_read,date(2027,1,5)))
        self.assertEqual(found,[(
            'Invesco India Small Cap Fund',
            'https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/nov.xlsx',
            'Complete monthly holdings 11/26')])

    def test_v127_targets_invesco_complete_current_and_prior_portfolios(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v127'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Invesco India Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Sundaram Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Invesco India Small Cap Fund','https://www.invescomutualfund.com/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("'amc-reports-2026-09-v127'",source)
        self.assertIn("amc_discovery.discover('Invesco')",source)
        self.assertIn("'2026-08-31','2026-07-31'",source)
        self.assertIn("ok.append(current and previous)",source)
        discovery=(Path(__file__).resolve().parents[1]/'tracker'/'amc_discovery.py').read_text()
        self.assertIn("'ITI','Invesco','Mahindra'",discovery)

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

    def test_tata_api_discovery_prefers_latest_official_workbook(self):
        from tracker.amc_discovery import discover
        api_rows=[
            {'field_document_title':'Portfolio as on 31st July, 2026',
             'field_media_document':'https://betacms.tatamutualfund.com/system/files/2026-08/Monthly-Portfolio-July-2026.xlsx',
             'field_section_flag':'On'},
            {'field_document_title':'Portfolio as on 31st August, 2026',
             'field_media_document':'https://betacms.tatamutualfund.com/system/files/2026-09/Monthly-Portfolio-August-2026.xlsx',
             'field_section_flag':'On'},
            {'field_document_title':'Portfolio as on 30th September, 2026',
             'field_media_document':'https://betacms.tatamutualfund.com/system/files/2026-10/Monthly-Portfolio-September-2026.xlsx',
             'field_section_flag':'On'},
            {'field_document_title':'Portfolio as on 31st August, 2026',
             'field_media_document':'https://example.com/not-tata.xlsx',
             'field_section_flag':'On'},
        ]
        def fake_read(url,body=None):
            self.assertIn('CMSDATA_portfolio?type=monthly',url)
            return (json.dumps(api_rows).encode(),'api-hash','application/json')
        with patch('tracker.amc_discovery.read',side_effect=fake_read):
            rows=list(discover('Tata'))
        self.assertEqual(rows,[(
            'Tata Small Cap Fund',
            'https://betacms.tatamutualfund.com/system/files/2026-09/Monthly-Portfolio-August-2026.xlsx',
            'Portfolio as on 31st August, 2026')])

    def test_v124_targets_only_tata_current_structured_portfolio(self):
        from tracker import amc_reports
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v124'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Tata Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Axis Small Cap Fund'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Tata Small Cap Fund','https://betacms.tatamutualfund.com/portfolio.xlsx','hash'))
        source=(Path(__file__).resolve().parents[1]/'scripts'/'refresh_amc_reports.py').read_text()
        self.assertIn("'amc-reports-2026-09-v124'",source)
        self.assertIn("amc_discovery.discover('Tata')",source)

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

    def test_v103_replays_only_exact_retained_edelweiss_september_pdf(self):
        from tracker import amc_reports
        exact='https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf'
        with patch.object(amc_reports,'PARSER_VERSION','amc-reports-2026-09-v103'):
            self.assertTrue(amc_reports.parser_upgrade_applies('Edelweiss Small Cap Fund'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Mirae Asset Small Cap Fund'))
            self.assertTrue(amc_reports.should_reprocess_existing('Edelweiss Small Cap Fund',exact,'archived'))
            self.assertFalse(amc_reports.should_reprocess_existing(
                'Edelweiss Small Cap Fund',
                'https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_August__2026_10082026160011.pdf',
                'archived'))
            self.assertFalse(amc_reports.parser_upgrade_applies('Bank Of India Small Cap Fund'))

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

    def test_groww_discovery_prefers_latest_monthly_workbook(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <a href="https://assets-netstorage.growwmf.in/portfolio/Monthly-Portfolio-July-31-2026.xlsx">Monthly Portfolio- July 31 2026.xlsx</a>
        <a href="https://assets-netstorage.growwmf.in/portfolio/Monthly-Portfolio-Aug-31-2026.xlsx">Monthly Portfolio- Aug 31 2026.xlsx</a>
        <a href="https://assets-netstorage.growwmf.in/portfolio/Fortnightly-Portfolio-Sep-15-2026.xlsx">Fortnightly Portfolio- Sep 15 2026.xlsx</a>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'page','text/html')), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('Groww'))
        self.assertEqual(rows,[(
            'Groww Small Cap Fund',
            'https://assets-netstorage.growwmf.in/portfolio/Monthly-Portfolio-Aug-31-2026.xlsx',
            'Monthly Portfolio- Aug 31 2026.xlsx')])

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

    def test_quant_api_discovery_prefers_latest_exact_small_cap_workbook(self):
        from tracker.amc_discovery import discover
        level1=json.dumps({'d':"""<ul>
          <li class='yearurl active1' id='7'>Jul</li>
          <li class='yearurl active1' id='8'>Aug</li>
        </ul>"""}).encode()
        level2=json.dumps({'d':"""<ul>
          <li><a href='/Admin/disclouser/quant_Multi_Cap_Fund_31_Aug_2026.xlsx'>quant Multi Cap Fund</a></li>
          <li><a href='/Admin/disclouser/quant_Small_Cap_Fund_31_Aug_2026.xlsx'>quant Small Cap Fund</a></li>
        </ul>"""}).encode()
        def fake_read(url,body=None):
            if url.endswith('displaydisclouser1'):
                self.assertEqual(body,{'id':'2026','cat':'MONTHLY PORTFOLIO - FUND - WISE'})
                return level1,'api1','application/json'
            if url.endswith('displaydisclouser2'):
                self.assertEqual(body,{'id':'8','cat':'MONTHLY PORTFOLIO - FUND - WISE','tab':'2026'})
                return level2,'api2','application/json'
            raise AssertionError(url)
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('quant Mutual'))
        self.assertEqual(rows,[(
            'Quant Small Cap Fund',
            'https://quantmutual.com/Admin/disclouser/quant_Small_Cap_Fund_31_Aug_2026.xlsx',
            'quant Small Cap Fund')])

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


    def test_abakkus_embedded_discovery_prefers_latest_month_end_workbook(self):
        from tracker.amc_discovery import _abakkus_embedded_monthly_portfolios
        payload=[{
            'title':'Monthly Portfolio Disclosures',
            'sections':[{
                'subSections':[{'items':[
                    {'title':'July 31, 2026','downloadUrl':'/uploads/july.pdf'},
                    {'title':'August 31, 2026','downloadUrl':'/uploads/august.pdf'},
                    {'title':'August 31, 2026','downloadUrl':'/uploads/august.xlsx'},
                    {'title':'September 15, 2026','downloadUrl':'/uploads/midmonth.xlsx'},
                ]}]
            }]
        }]
        html=('<html><body><script type="application/json">'+json.dumps(payload)+'</script></body></html>').encode()
        with patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=_abakkus_embedded_monthly_portfolios(
                html,'https://www.abakkusmf.com/statutory-disclosures.html','Abakkus')
        self.assertEqual(rows,[
            (__import__('datetime').date(2026,8,31),2,'https://www.abakkusmf.com/uploads/august.xlsx','August 31, 2026'),
            (__import__('datetime').date(2026,8,31),1,'https://www.abakkusmf.com/uploads/august.pdf','August 31, 2026'),
        ])

    def test_absl_discovery_prefers_latest_official_monthly_portfolio_zip(self):
        from tracker.amc_discovery import discover
        page=b'''<html><body><ul class="tabInject">
        <li data-accordian-api="/postlogin/CustomApi/Resources/FactsheetAccordionById?id=abc&amp;ctype=individual">
        <button><span>Monthly Portfolio</span></button></li></ul></body></html>'''
        payload=json.dumps({'ReturnCode':'1','AccordionList':[
            {'ResourceLink':'Monthly Portfolios as on July 31, 2026',
             'pdfUrl':'https://abcscprod.azureedge.net/monthly-july.zip'},
            {'ResourceLink':'Monthly Portfolios as on August 31, 2026',
             'pdfUrl':'https://abcscprod.azureedge.net/monthly-august.zip'},
        ]}).encode()
        def fake_read(url,body=None):
            if 'FactsheetAccordionById' in url:return payload,'api','application/json'
            return page,'page','text/html'
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('Aditya Birla'))
        self.assertEqual(rows,[
            ('Aditya Birla Sun Life Small Cap Fund',
             'https://mutualfund.adityabirlacapital.com/monthly-august.zip',
             'Monthly Portfolios as on August 31, 2026'),
            ('Aditya Birla Sun Life Small Cap Fund',
             'https://abcscprod.azureedge.net/monthly-august.zip',
             'Monthly Portfolios as on August 31, 2026'),
        ])

    def test_absl_monthly_zip_reuses_complete_spreadsheet_reconciliation(self):
        import zipfile
        import openpyxl
        from tracker import db
        from tracker.structured_reports import absl_zip
        db.init()
        wb=openpyxl.Workbook();ws=wb.active;ws.title='Small Cap'
        rows=[
            ['Aditya Birla Sun Life Small Cap Fund',None,None,None,None,None],
            ['Monthly Portfolio Statement as on August 31, 2026',None,None,None,None,None],
            ['Name of the Instrument','ISIN','Industry / Rating','Quantity','Market/Fair Value (Rs. in Lakhs)','% to NAV'],
            ['Equity & Equity related',None,None,None,None,None],
            ['Alpha Industries Limited','INE000A01010','Industrial Products',1000,6000,60.0],
            ['Beta Bank Limited','INE000B01018','Banks',1000,3500,35.0],
            ['Net Current Assets',None,None,None,500,5.0],
            ['GRAND TOTAL',None,None,None,10000,100.0],
        ]
        for row in rows:ws.append(row)
        xlsx=io.BytesIO();wb.save(xlsx);wb.close()
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('ABSL_Small_Cap_Aug_2026.xlsx',xlsx.getvalue())
            z.writestr('readme.txt',b'official monthly portfolio package')
        saved=absl_zip(archive.getvalue(),'Aditya Birla Sun Life Small Cap Fund',
                       'https://abcscprod.azureedge.net/monthly-august.zip','absl-zip')
        self.assertGreaterEqual(saved,3)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family='Aditya Birla Sun Life Small Cap Fund' AND p.hash='absl-zip'
          GROUP BY p.id""")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1,'positions':3})

    def test_absl_discovery_prefers_latest_official_factsheet(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <div data-file="/-/media/bsl/files/resources/factsheets/2026/absl-factsheet_aug-2026.pdf">ABSL Factsheet Aug 2026</div>
        <div data-file="/-/media/bsl/files/resources/factsheets/2026/absl-factsheet_sep-2026.pdf">ABSL Factsheet Sep 2026</div>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'page','text/html')), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('Aditya Birla'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],'Aditya Birla Sun Life Small Cap Fund')
        self.assertTrue(rows[0][1].endswith('absl-factsheet_sep-2026.pdf'))

    def test_lic_discovery_prefers_latest_dated_official_factsheet(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <div data-file="/assets/downloads/monthly_fact_sheet/2026-2027/08/lic-mf-factsheet-31st-july-2026.pdf">Fact Sheet 31st July 2026</div>
        <div data-file="/assets/downloads/monthly_fact_sheet/2026-2027/09/lic-mf-factsheet-31st-august-2026.pdf">Fact Sheet 31st August 2026</div>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'page','text/html')), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('LIC'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],'LIC Mf Small Cap Fund')
        self.assertTrue(rows[0][1].endswith('lic-mf-factsheet-31st-august-2026.pdf'))

    def test_franklin_discovery_prefers_latest_official_monthly_portfolio(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <div data-file="/downloads/portfolio/Franklin-Small-Cap-as-on-July-31-2026.xlsx">Monthly Portfolio As on July 31 2026</div>
        <div data-file="/downloads/portfolio/Franklin-Small-Cap-as-on-August-31-2026.xlsx">Monthly Portfolio As on August 31 2026</div>
        <a href="/downloads/portfolio/Franklin-Small-Cap-as-on-August-31-2026.pdf">Monthly Portfolio As on August 31 2026</a>
        </body></html>'''
        def fake_read(url,body=None):
            return html,'page','text/html'
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('Franklin'))
        self.assertEqual(rows[0][0],'Franklin India Small Cap Fund')
        self.assertTrue(rows[0][1].endswith('Franklin-Small-Cap-as-on-August-31-2026.xlsx'))
        self.assertEqual(len(rows),2)
        self.assertFalse(any('July-31-2026' in row[1] for row in rows))

    def test_hsbc_discovery_uses_archive_exact_link_then_stable_fallback(self):
        from tracker import amc_discovery
        html=b'''<html><body>
        <a href="/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-real-aug-2026.pdf">The Asset as on - August 2026</a>
        <a href="/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-real-jul-2026.pdf">The Asset as on - July 2026</a>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'page','text/html')), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            self.assertEqual(list(amc_discovery.discover('HSBC')),[(
                'HSBC Small Cap Fund',
                'https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-real-aug-2026.pdf',
                'The Asset as on - August 2026')])
        with patch('tracker.amc_discovery.read',side_effect=ValueError('archive unavailable')), \
             patch('tracker.amc_discovery.date') as fake:
            fake.today.return_value=date(2026,9,23)
            rows=list(amc_discovery.discover('HSBC'))
        self.assertEqual(rows[0],(
            'HSBC Small Cap Fund',
            'https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf',
            'The Asset - August 2026'))

    def test_mirae_discovery_uses_official_portfolio_service(self):
        from tracker import amc_discovery
        payload=json.dumps({'ReturnCode':'0','DataCount':4,'Data':[
            {'Title':'Portfolio Details as on 31st August 2026 for Mirae Asset Nifty Smallcap 250 ETF',
             'URL':'/docs/smallcap-etf-august-2026.xlsx','PublishDate':'/Date(1788998400000)/'},
            {'Title':'Portfolio Details as on 31st July 2026 for Mirae Asset Small Cap Fund',
             'URL':'/docs/monthly-portfolio-july-2026.pdf','PublishDate':'/Date(1785456000000)/'},
            {'Title':'Portfolio Details as on 31st August 2026 for Mirae Asset Small Cap Fund',
             'URL':'/docs/monthly-portfolio-august-2026.xlsx','PublishDate':'/Date(1788134400000)/'},
            {'Title':'Portfolio Details as on 31st August 2026 for Mirae Asset Small Cap Fund',
             'URL':'/docs/monthly-portfolio-august-2026.pdf','PublishDate':'/Date(1788134400000)/'},
        ]}).encode()
        def fake_read(url,body=None):
            self.assertEqual(url,'https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData')
            self.assertEqual(body,{'request':{'modulename':'portfolio_tab1','pgno':1,'pgsize':100}})
            return payload,'api','application/json'
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(amc_discovery.discover('Mirae'))
        self.assertEqual(rows[0],(
            'Mirae Asset Small Cap Fund',
            'https://www.miraeassetmf.co.in/docs/monthly-portfolio-august-2026.xlsx',
            'Portfolio Details as on 31st August 2026 for Mirae Asset Small Cap Fund'))
        self.assertEqual(len(rows),3)

    def test_pgim_discovery_uses_official_disclosure_api_for_latest_smallcap_workbook(self):
        from tracker import amc_discovery
        payload=json.dumps({'resultInfo':{'resultCodeId':'1'},'data':[{
            'tabId':12,'content':[
                {'disclosureSection':'SECTION_747960037','disclosureTab':12,
                 'pdfPath':'https://www.pgimindia.com/api/v1/brochure/about-us/image/PGIM INDIA SMALL CAP FUND  Jul 2026.xlsx',
                 'dateMonthYear':'31 July 2026','title':'PGIM INDIA SMALL CAP FUND  Jul 2026'},
                {'disclosureSection':'SECTION_747960037','disclosureTab':12,
                 'pdfPath':'https://www.pgimindia.com/api/v1/brochure/about-us/image/PGIM INDIA SMALL CAP FUND Aug 2026.xlsx',
                 'dateMonthYear':'31 August 2026','title':'PGIM INDIA SMALL CAP FUND Aug 2026'},
                {'disclosureSection':'SECTION_747960037','disclosureTab':12,
                 'pdfPath':'https://www.pgimindia.com/api/v1/brochure/about-us/image/PGIM INDIA MIDCAP FUND Aug 2026.xlsx',
                 'dateMonthYear':'31 August 2026','title':'PGIM INDIA MIDCAP FUND Aug 2026'},
            ]}]}).encode()
        def fake_read(url,body=None):
            if 'published/disclosure' in url:
                self.assertEqual(body,{'headerId':2,'sectionId':'SECTION_747960037'})
                return payload,'api','application/json'
            raise AssertionError('fallback should not be needed')
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(amc_discovery.discover('PGIM'))
        self.assertEqual(rows,[(
            'Pgim India Small Cap Fund',
            'https://www.pgimindia.com/api/v1/brochure/about-us/image/PGIM INDIA SMALL CAP FUND Aug 2026.xlsx',
            'PGIM INDIA SMALL CAP FUND Aug 2026')])

    def test_pgim_discovery_prefers_structured_monthly_portfolio(self):
        from tracker import amc_discovery
        monthly=b'''<html><body>
        <a href="/downloads/monthly-portfolio-july-2026.pdf">Monthly Portfolio July 2026</a>
        <a href="/downloads/monthly-portfolio-august-2026.xlsx">Monthly Portfolio August 2026</a>
        </body></html>'''
        factsheet=b'''<html><body>
        <a href="/downloads/factsheet-august-2026.pdf">Factsheet - August 2026</a>
        </body></html>'''
        def fake_read(url,body=None):
            return (monthly if 'Monthly-Portfolio' in url else factsheet),'page','text/html'
        with patch('tracker.amc_discovery.read',side_effect=fake_read), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(amc_discovery.discover('PGIM'))
        self.assertEqual(rows[0],(
            'Pgim India Small Cap Fund',
            'https://www.pgimindia.com/downloads/monthly-portfolio-august-2026.xlsx',
            'Monthly Portfolio August 2026'))
        self.assertEqual(len(rows),2)

    def test_pgim_discovery_keeps_stable_fallback_when_indexes_fail(self):
        from tracker import amc_discovery
        with patch('tracker.amc_discovery.read',side_effect=ValueError('index unavailable')), \
             patch('tracker.amc_discovery.date') as fake:
            fake.today.return_value=date(2026,9,22)
            rows=list(amc_discovery.discover('PGIM'))
        self.assertEqual(rows[0],(
            'Pgim India Small Cap Fund',
            'https://www.pgimindia.com/api/v1/brochure/about-us/image/Factsheet - August 2026.pdf',
            'Factsheet - August 2026'))


    def test_dsp_discovery_prefers_latest_month_end_zip(self):
        from tracker.amc_discovery import discover
        html=b'''<html><body>
        <a href="/media/pages/mandatory-disclosures/portfolio-disclosures/july/dsp-monthend-portfolio-as-on-31-jul-2026.zip">Portfolio Details as on July 31, 2026</a>
        <a href="/media/pages/mandatory-disclosures/portfolio-disclosures/aug/dsp-monthend-portfolio-as-on-31-aug-2026.zip">Portfolio Details as on August 31, 2026</a>
        <a href="/media/pages/mandatory-disclosures/portfolio-disclosures/aug/dsp-fortnightly-portfolio-as-on-31-aug-2026.zip">Fortnightly Portfolios as on August 31, 2026</a>
        </body></html>'''
        with patch('tracker.amc_discovery.read',return_value=(html,'page','text/html')), \
             patch('tracker.amc_discovery.disclosures.official_publication_url',return_value=True):
            rows=list(discover('DSP'))
        self.assertEqual(rows,[(
            'DSP Small Cap Fund',
            'https://www.dspim.com/media/pages/mandatory-disclosures/portfolio-disclosures/aug/dsp-monthend-portfolio-as-on-31-aug-2026.zip',
            'Portfolio Details as on August 31, 2026')])

    def test_dsp_month_end_zip_reuses_spreadsheet_reconciliation(self):
        import io,zipfile,openpyxl
        from tracker import db
        from tracker.structured_reports import dsp_zip
        wb=openpyxl.Workbook();ws=wb.active;ws.title='DSP Small Cap Fund'
        rows=[
            ['DSP Small Cap Fund',None,None,None,None,None],
            ['Monthly Portfolio Statement as on August 31, 2026',None,None,None,None,None],
            ['Name of Instrument','ISIN','Industry','Quantity','Market Value (Rs. in Lakhs)','% to Net Assets'],
            ['Alpha Limited','INE123456789','Banks',100,9500,95.0],
            ['TREPS',None,None,None,400,4.0],
            ['Net Receivables / Payables',None,None,None,100,1.0],
            ['Grand Total',None,None,None,10000,100.0],
        ]
        for row in rows:ws.append(row)
        xlsx=io.BytesIO();wb.save(xlsx);wb.close()
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('DSP_Small_Cap_Aug_2026.xlsx',xlsx.getvalue())
        saved=dsp_zip(archive.getvalue(),'DSP Small Cap Fund',
                      'https://www.dspim.com/dsp-monthend-portfolio-as-on-31-aug-2026.zip','dsp-zip')
        self.assertGreaterEqual(saved,3)
        snap=db.one("""SELECT p.as_of,p.complete,COUNT(h.id) positions
          FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family='DSP Small Cap Fund' AND p.hash='dsp-zip' GROUP BY p.id""")
        self.assertEqual(snap,{'as_of':'2026-08-31','complete':1,'positions':3})

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
