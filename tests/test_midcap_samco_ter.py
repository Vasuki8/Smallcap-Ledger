"""Samco's filtered absence must not mask exact AMFI all-category evidence."""
import copy
import hashlib
import json
import unittest
from datetime import date
from urllib.parse import parse_qs,urlsplit
from tracker.midcap_samco_ter import fetch_samco_ter, SamcoTERError

TODAY=date(2026,9,28)
SELECTOR={'name':'Samco Mutual Fund','id':'74'}

def row(day='2026-09-25', **changes):
    result={'NSDLSchemeCode':'SAMC/O/E/MIF/25/10/0013','Scheme_Name':'Samco Mid Cap Fund',
      'SchemeType_Desc':'Open Ended','SchemeCat_Desc':'Equity Schemes - Mid Cap Fund',
      'TER_Year':'2026-2027','TER_Date':day+'T00:00:00.000Z','MF_ID':74,'Month':'09-2026',
      'R_BER':'2.1000','R_BrokerageCost':'0.1000','R_TransactionCost':'0.0100',
      'R_StatutoryLevies':'0.7900','R_TER':'3.0000','D_BER':'0.8100','D_BrokerageCost':'0.1000',
      'D_TransactionCost':'0.0100','D_StatutoryLevies':'0.6600','D_TER':'1.5800'}
    result.update(changes);return result

class Feed:
    def __init__(self, records, size=2):
        self.records=records;self.size=size;self.calls=[];self.bodies={};self.mutate=None
    def __call__(self,url,**kwargs):
        params=parse_qs(urlsplit(url).query);page=int(params['page'][0]);self.calls.append((url,kwargs))
        n=len(self.records);data=self.records[(page-1)*self.size:page*self.size]
        payload={'data':copy.deepcopy(data),'meta':{'page':page,'pageSize':self.size,'total':n,'pageCount':(n+self.size-1)//self.size}}
        if self.mutate:self.mutate(payload,page)
        body=json.dumps(payload).encode();self.bodies[page]=body
        return body,None,'application/json'

class SamcoTERTests(unittest.TestCase):
    def fetch(self,feed,**kwargs):
        return fetch_samco_ter(SELECTOR,fetch_fn=feed,today=TODAY,**kwargs)
    def test_recovers_exact_plural_category_with_complete_plan_pair(self):
        rows,checks=self.fetch(Feed([row()]))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['D_TER'],'1.5800');self.assertEqual(rows[0]['R_TER'],'3.0000')
        self.assertEqual(rows[0]['D_BER'],'0.8100')
        self.assertTrue(checks[-1]['complete'])
    def test_reads_all_pages_before_claiming_latest_date(self):
        records=[row(Scheme_Name='Samco Large & Mid Cap Fund')]*2+[row('2026-09-01'),row('2026-09-24'),row()]
        feed=Feed(records);rows,checks=self.fetch(feed)
        self.assertEqual(len(feed.calls),3)
        self.assertEqual(rows[-1]['TER_Date'],'2026-09-25T00:00:00.000Z')
        self.assertEqual(checks[-1]['total_rows'],5)
    def test_does_not_mutate_source_and_retains_exact_response_hash(self):
        original=row();feed=Feed([original]);rows,checks=self.fetch(feed)
        self.assertEqual(original,row())
        proof=rows[0]['_amfi_source_evidence']
        self.assertEqual(proof['source_sha256'],hashlib.sha256(feed.bodies[1]).hexdigest())
        self.assertEqual(proof['published_row'],original)
        self.assertIn('strCat=-1',proof['source'])
        self.assertEqual(proof['source_row'],1)
    def test_every_request_is_read_only_amc_scoped_and_bounded(self):
        feed=Feed([row()]);self.fetch(feed)
        for url,kw in feed.calls:
            self.assertEqual(urlsplit(url).hostname,'www.amfiindia.com')
            self.assertEqual(parse_qs(urlsplit(url).query)['MF_ID'],['74'])
            self.assertIs(kw['archive'],False);self.assertLessEqual(kw['max_bytes'],2*1024*1024)
    def test_other_schemes_are_not_returned(self):
        rows,_=self.fetch(Feed([row(Scheme_Name='Samco Large & Mid Cap Fund'),row(Scheme_Name='Samco Small Cap Fund')]))
        self.assertEqual(rows,[])
    def test_exact_empty_feed_is_a_diagnostic_gap_not_zero_fee(self):
        rows,checks=self.fetch(Feed([]));self.assertEqual(rows,[])
        self.assertTrue(checks[-1]['complete']);self.assertEqual(checks[-1]['matched_families'],[])
    def test_rejects_wrong_nsdl_category_or_scheme_type(self):
        for changes in ({'NSDLSchemeCode':'SAMC/O/E/LMF/25/03/0011'},
                        {'SchemeCat_Desc':'Equity Schemes - Large & Mid Cap Fund'},
                        {'SchemeType_Desc':'Closed Ended'}):
            with self.subTest(changes=changes),self.assertRaises(SamcoTERError):self.fetch(Feed([row(**changes)]))
    def test_rejects_wrong_amc_or_month_even_when_name_matches(self):
        for changes in ({'MF_ID':99},{'MF_ID':True},{'Month':'08-2026'}):
            with self.subTest(changes=changes),self.assertRaises(SamcoTERError):self.fetch(Feed([row(**changes)]))
    def test_rejects_future_malformed_or_other_month_dates(self):
        for stamp in ('2026-09-29T00:00:00Z','2026-08-31T00:00:00Z','2026-09-31T00:00:00Z','not-a-date'):
            with self.subTest(stamp=stamp),self.assertRaises(SamcoTERError):self.fetch(Feed([row(TER_Date=stamp)]))
    def test_rejects_missing_nonfinite_negative_or_boolean_numbers(self):
        for value in (None,'','NA','NaN','Infinity','-1',True,'11'):
            with self.subTest(value=value),self.assertRaises(SamcoTERError):self.fetch(Feed([row(D_TER=value)]))
    def test_requires_published_components_and_regular_plan(self):
        for changes in ({'R_TER':None},{'D_BrokerageCost':None},{'D_TER':'0.8100'},{'D_BER':'2.0'}):
            with self.subTest(changes=changes),self.assertRaises(SamcoTERError):self.fetch(Feed([row(**changes)]))
    def test_conflicting_duplicate_is_not_hidden(self):
        with self.assertRaises(SamcoTERError):self.fetch(Feed([row(),row(D_TER='1.5900',D_StatutoryLevies='0.6700')]))
    def test_identical_duplicate_can_be_deduplicated(self):
        rows,_=self.fetch(Feed([row(),row()]));self.assertEqual(len(rows),1)
    def test_rejects_incomplete_changed_or_wrong_pagination(self):
        cases=[lambda p,n:p['meta'].update(page=n+1),lambda p,n:p['meta'].update(pageCount=10),
               lambda p,n:p['meta'].update(total='1'),lambda p,n:p.update(data=[])]
        for mutate in cases:
            feed=Feed([row()]);feed.mutate=mutate
            with self.subTest(mutate=mutate),self.assertRaises(SamcoTERError):self.fetch(feed)
    def test_later_page_failure_returns_no_partial_success(self):
        feed=Feed([row('2026-09-01'),row('2026-09-24'),row()])
        def failure(url,**kw):
            if parse_qs(urlsplit(url).query)['page']==['2']:raise RuntimeError('upstream failure')
            return feed(url,**kw)
        with self.assertRaises(SamcoTERError) as caught:self.fetch(failure)
        self.assertTrue(caught.exception.checks)
    def test_missing_metadata_or_invalid_json_is_not_empty_success(self):
        for body in (b'{}',b'{"data":[]}',b'[]',b'{bad',b'{"data":[],"meta":NaN}'):
            with self.subTest(body=body),self.assertRaises(SamcoTERError):
                self.fetch(lambda url,**kw:(body,None,'application/json'))
    def test_rejects_wrong_selector_before_network(self):
        for selector in ({'name':'Another AMC','id':'74'},{'name':'Samco Mutual Fund','id':'All'}):
            with self.assertRaises(SamcoTERError):fetch_samco_ter(selector,fetch_fn=lambda *a,**k:self.fail('network called'),today=TODAY)
    def test_month_and_year_request_are_not_hardcoded(self):
        feed=Feed([]);fetch_samco_ter(SELECTOR,fetch_fn=feed,today=date(2027,1,1))
        self.assertEqual(parse_qs(urlsplit(feed.calls[0][0]).query)['Month'],['01-2027'])

if __name__=='__main__':unittest.main()
