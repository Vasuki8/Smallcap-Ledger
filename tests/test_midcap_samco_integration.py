"""Regression for AMFI selector omission plus plural category wording."""
import copy
import json
import unittest
from datetime import date
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from tracker import midcap_source_coverage as coverage
from tracker.midcap_samco_ter import FAMILY, AMC
from test_midcap_samco_ter import Feed, row

class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026,9,28)

class PipelineFeed:
    def __init__(self, primary=False):
        self.primary=primary
        self.calls=[]
        self.fallback=Feed([row(Scheme_Name='Samco Large & Mid Cap Fund'),
                            row('2026-09-01'),row()],size=2)
    def __call__(self,url,**kwargs):
        self.calls.append(url)
        if url.endswith('/api/populate-mf'):
            data={'data':[{'mfName':'AAA Mutual Fund','mfId':'1'},
                          {'mfName':AMC,'mfId':'74'}]}
        else:
            params=parse_qs(urlsplit(url).query)
            if params['strCat']==['-1']:
                return self.fallback(url,**kwargs)
            if params['MF_ID']==['1']:
                records=[dict(row(),Scheme_Name='Example Mid Cap Fund',
                              SchemeCat_Desc='Equity Scheme - Mid Cap Fund')]
            elif self.primary:
                records=[dict(row(),SchemeCat_Desc='Equity Scheme - Mid Cap Fund')]
            else:
                records=[]
            data={'data':records,'meta':{'page':1,'pageSize':100,'total':len(records),'pageCount':1 if records else 0}}
        return json.dumps(data).encode(),None,'application/json'

class SamcoIntegrationTests(unittest.TestCase):
    def families(self):
        return [{'family':'Example Mid Cap Fund','amc':'AAA Mutual Fund'},
                {'family':FAMILY,'amc':AMC}]
    def collect(self,feed,families=None):
        with patch.object(coverage,'date',FixedDate):
            return coverage._fetch_midcap_ter(families or self.families(),fetch_fn=feed,sleep_fn=lambda _:None)
    def test_exact_plural_midcap_category_is_accepted(self):
        self.assertTrue(coverage._is_mid_cap_category('Equity Schemes - Mid Cap Fund'))
        for label in ('Equity Schemes - Large & Mid Cap Fund','Equity Schemes - Small Cap Fund',
                      'Equity Schemes - Mid Cap Fund Extra','Equity Scheme - Multi Cap Fund'):
            self.assertFalse(coverage._is_mid_cap_category(label))
    def test_filtered_omission_recovers_latest_exact_samco_and_proof(self):
        feed=PipelineFeed();rows,checks,errors=self.collect(feed)
        self.assertEqual(errors,[])
        matched,_=coverage._match_ter(rows,self.families(),today=FixedDate.today())
        self.assertIn(FAMILY,matched)
        self.assertEqual(matched[FAMILY]['as_of'],'2026-09-25')
        self.assertEqual(matched[FAMILY]['direct']['value'],1.58)
        self.assertEqual(matched[FAMILY]['regular']['value'],3.0)
        self.assertEqual(matched[FAMILY]['category'],'Equity Schemes - Mid Cap Fund')
        self.assertEqual(matched[FAMILY]['identity']['nsdl_scheme_code'],'SAMC/O/E/MIF/25/10/0013')
        self.assertIn('strCat=-1',matched[FAMILY]['source'])
        self.assertEqual(len(matched[FAMILY]['source_sha256']),64)
        self.assertEqual(matched[FAMILY]['published_row']['D_BER'],'0.8100')
        self.assertEqual(len(feed.fallback.calls),2)
        self.assertEqual(checks[-1]['unmatched_families'],[])
    def test_ter_reconciliation_keeps_samco_provenance_and_primary_precedence(self):
        from tracker.midcap_ter_readiness import reconcile
        rows,_,_=self.collect(PipelineFeed())
        matched,_=coverage._match_ter(rows,self.families(),today=FixedDate.today())
        original=copy.deepcopy(matched[FAMILY])
        audit={'built_at':'2026-09-28T06:00:00Z','families':[
            {'family':FAMILY,'amc':AMC,'direct_ter_available':True,'ter':matched[FAMILY]}]}
        result=reconcile(audit,{'results':[{'family':FAMILY,'status':'recovered','direct_ter':9.9}]})
        value=result['families'][0]
        self.assertEqual(value['direct_ter'],1.58)
        self.assertEqual(value['evidence_channel'],'amfi')
        self.assertEqual(value.get('identity'),original['identity'])
        for field in ('source_sha256','source_observed_at','published_row','source_row'):
            self.assertEqual(value.get(field),original[field])
        self.assertEqual(matched[FAMILY],original)
        self.assertFalse(result['public_export_enabled'])
        self.assertEqual(result['production_writes'],0)
    def test_primary_success_never_triggers_extra_samco_request(self):
        feed=PipelineFeed(primary=True);_,_,errors=self.collect(feed)
        self.assertEqual(errors,[])
        self.assertFalse(feed.fallback.calls)
    def test_non_samco_universe_does_not_trigger_samco_fallback(self):
        feed=PipelineFeed();self.collect(feed,self.families()[:1])
        self.assertFalse(feed.fallback.calls)
    def test_same_family_under_wrong_amc_is_not_authorization(self):
        feed=PipelineFeed();self.collect(feed,[self.families()[0],{'family':FAMILY,'amc':'AAA Mutual Fund'}])
        self.assertFalse(feed.fallback.calls)
    def test_failed_fallback_does_not_export_partial_rows(self):
        feed=PipelineFeed()
        def truncate(data,page):
            if page==2:data['data']=[]
        feed.fallback.mutate=truncate
        rows,checks,errors=self.collect(feed)
        self.assertTrue(errors)
        self.assertNotIn(FAMILY,coverage._match_ter(rows,self.families(),today=FixedDate.today())[0])
        self.assertIn(FAMILY,checks[-1]['unmatched_families'])
        self.assertTrue(any(check.get('kind')=='ter_samco_amc_page' for check in checks))
    def test_fallback_is_read_only_even_if_database_is_unavailable(self):
        with patch.object(coverage.db,'connect',side_effect=AssertionError('database access forbidden')):
            self.assertEqual(self.collect(PipelineFeed())[2],[])

if __name__=='__main__':unittest.main()
