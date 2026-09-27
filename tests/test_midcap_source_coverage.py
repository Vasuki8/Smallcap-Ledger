"""Regression tests for staged Mid Cap source-coverage audit."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.midcap_source_coverage import report,_match_aum,_match_ter


def staged_family():
    return {"family":"Example Mid Cap Fund","amc":"Example AMC","codes":[200001,200002],
            "plans":["Direct","Regular"],"options":["Growth"],"nav_history_checked":"2026-09-27T00:00:00+00:00"}


class MidCapSourceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=patch.object(db,"DATA",Path(self.tmp.name));self.p.start();db.init()
        with db.connect() as conn:
            for code,plan in ((200001,"Direct"),(200002,"Regular")):
                conn.execute("""INSERT INTO category_staged_schemes(
                  code,category,name,family,amc,plan,option,source_sha256,first_seen,last_seen,metadata_json)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (code,"mid-cap","Example Mid Cap Fund","Example Mid Cap Fund","Example AMC",
                   plan,"Growth","abc","2026-09-27T00:00:00+00:00","2026-09-27T00:00:00+00:00","{}"))
            conn.execute("""INSERT INTO schemes(
              code,name,family,amc,plan,option,category,category_source)
              VALUES(1,'Live Small Cap','Live Small Cap','Example AMC','Direct','Growth','small-cap','fixture')""")
            conn.execute("""INSERT INTO source_pages(amc_match,url,label,status,last_checked)
              VALUES('Example AMC','https://example.com/downloads','Downloads','Checked','2026-09-27T00:00:00+00:00')""")

    def tearDown(self):
        self.p.stop();self.tmp.cleanup()

    def test_aum_and_ter_match_exact_midcap_family(self):
        families=[staged_family()]
        aum,_=_match_aum([{
            "schemeName":"Example Mid Cap Fund","dailyAUM":"123.45","navDate":"25-Sep-2026"
        }],families,today=date(2026,9,27))
        self.assertEqual(aum["Example Mid Cap Fund"]["value"],123.45)
        ter,_=_match_ter([{
            "Scheme_Name":"Example Mid Cap Fund","SchemeCat_Desc":"Equity Scheme - Mid Cap Fund",
            "TER_Date":"25-Sep-2026","D_TER":"0.55","R_TER":"1.50"
        }],families,today=date(2026,9,27))
        self.assertEqual(ter["Example Mid Cap Fund"]["direct"]["value"],0.55)

    def test_ter_collection_uses_exact_amc_month_contract(self):
        from tracker.midcap_source_coverage import _fetch_midcap_ter
        families=[staged_family()]
        calls=[]
        def fake_fetch(url,**kwargs):
            calls.append(url)
            if url.endswith('/api/populate-mf'):
                return b'{"data":[{"mfName":"Example AMC","mfId":"77"}]}',None,'application/json'
            self.assertIn('MF_ID=77',url)
            self.assertIn('strCat=-1',url)
            self.assertIn('strType=1',url)
            self.assertIn('page=1',url)
            payload={
                'data':[{
                    'Scheme_Name':'Example Mid Cap Fund',
                    'SchemeCat_Desc':'Equity Scheme - Mid Cap Fund',
                    'TER_Date':'2026-09-25T00:00:00',
                    'D_TER':'0.55','R_TER':'1.50',
                }],
                'meta':{'totalPages':1,'pageSize':10000},
            }
            return __import__('json').dumps(payload).encode(),None,'application/json'
        rows,checks,errors=_fetch_midcap_ter(
            families,months=1,fetch_fn=fake_fetch,sleep_fn=lambda _:None)
        self.assertEqual(errors,[])
        self.assertEqual(len(rows),1)
        self.assertEqual(len(calls),2)
        summary=checks[-1]
        self.assertEqual(summary['matched_families'],1)
        self.assertEqual(summary['unmatched_families'],[])
    def test_ter_collection_follows_reported_pagination_until_match(self):
        from tracker.midcap_source_coverage import _fetch_midcap_ter
        families=[staged_family()]
        calls=[]
        def fake_fetch(url,**kwargs):
            calls.append(url)
            if url.endswith('/api/populate-mf'):
                return b'{"data":[{"mfName":"Example AMC","mfId":"77"}]}',None,'application/json'
            page='2' if 'page=2' in url else '1'
            payload={
                'data':([{'Scheme_Name':'Other Fund','SchemeCat_Desc':'Equity Scheme - Large Cap Fund','TER_Date':'25-Sep-2026','D_TER':'0.4'}]
                        if page=='1' else
                        [{'Scheme_Name':'Example Mid Cap Fund','SchemeCat_Desc':'Equity Scheme - Mid Cap Fund','TER_Date':'25-Sep-2026','D_TER':'0.55','R_TER':'1.50'}]),
                'meta':{'totalPages':3,'pageSize':10},
            }
            return __import__('json').dumps(payload).encode(),None,'application/json'
        rows,checks,errors=_fetch_midcap_ter(
            families,months=1,fetch_fn=fake_fetch,sleep_fn=lambda _:None)
        self.assertEqual(errors,[])
        self.assertEqual(len(rows),1)
        self.assertEqual(len(calls),3)
        entry=next(x for x in checks if x.get('kind')=='ter_mid_cap_by_amc')
        self.assertEqual(len(entry['pages_checked']),2)
        self.assertEqual(entry['matched_families'],['Example Mid Cap Fund'])
    def test_non_midcap_ter_row_is_rejected(self):
        families=[staged_family()]
        ter,_=_match_ter([{
            "Scheme_Name":"Example Mid Cap Fund","SchemeCat_Desc":"Equity Scheme - Small Cap Fund",
            "TER_Date":"25-Sep-2026","D_TER":"0.55"
        }],families,today=date(2026,9,27))
        self.assertEqual(ter,{})

    def test_report_does_not_treat_shared_amc_as_coverage(self):
        result=report([],[],today=date(2026,9,27))
        row=result["families"][0]
        self.assertTrue(row["shared_live_amc"])
        self.assertEqual(len(row["amc_source_candidates"]),1)
        self.assertEqual(row["coverage_gaps"],["aum","direct_ter","benchmark_identity","current_portfolio"])
        self.assertFalse(row["all_required_source_evidence"])
        self.assertFalse(result["public_export_enabled"])
        self.assertEqual(result["production_writes"],0)
        self.assertFalse(result["mid_cap_launch_ready"])

    def test_exact_retained_family_evidence_counts(self):
        with db.connect() as conn:
            conn.execute("""INSERT INTO metrics(family,plan,metric,as_of,value,unit,source,hash,observed_at)
              VALUES('Example Mid Cap Fund','All','benchmark','2026-09-25','NIFTY Midcap 150 TRI','Reported',
              'https://example.com/factsheet','h','2026-09-27T00:00:00+00:00')""")
            pid=conn.execute("""INSERT INTO portfolios(family,as_of,complete,source,hash,observed_at)
              VALUES('Example Mid Cap Fund','2026-08-31',1,'https://example.com/portfolio','p',
              '2026-09-27T00:00:00+00:00')""").lastrowid
            conn.execute("""INSERT INTO holdings(snapshot_id,name,weight,asset_type)
              VALUES(?,?,?,?)""",(pid,"Example Holding",100.0,"Equity"))
        aum=[{"schemeName":"Example Mid Cap Fund","dailyAUM":"123.45","navDate":"25-Sep-2026"}]
        ter=[{"Scheme_Name":"Example Mid Cap Fund","SchemeCat_Desc":"Equity Scheme - Mid Cap Fund",
              "TER_Date":"25-Sep-2026","D_TER":"0.55","R_TER":"1.50"}]
        result=report(aum,ter,today=date(2026,9,27))
        row=result["families"][0]
        self.assertEqual(row["coverage_gaps"],[])
        self.assertEqual(result["counts"]["all_required_source_evidence"],1)
        self.assertTrue(result["source_coverage_ready"])
        self.assertFalse(result["mid_cap_launch_ready"])


if __name__=="__main__":
    unittest.main()
