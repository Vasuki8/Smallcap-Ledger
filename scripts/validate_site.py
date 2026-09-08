"""Validate a generated static site without launching a browser."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tracker.publications import exclusion_reason


def validate(root):
    root=Path(root).resolve()
    def read(path):return json.loads((root/path).read_text(encoding='utf-8'))
    for file in ('index.html','style.css','app.js','analytics.js','static-data.js','runtime-config.js','.nojekyll'):
        assert (root/file).is_file(),file+' missing'
    index=(root/'index.html').read_text()
    assert 'src="/app.js"' not in index and 'href="/style.css"' not in index,'Assets must support repository base paths'
    funds=read('data/funds.json')['funds'];status=read('data/status.json');bench=read('data/benchmarks.json')
    assert funds and status['counts']['plans']==len(funds)
    seen=set();growth=0;compared=0
    for f in funds:
        detail=read(f'data/funds/{f["code"]}.json');points=read(f'data/nav/{f["code"]}.json')
        dates=[p[0] for p in points]
        assert dates==sorted(set(dates)),f'Duplicate/out-of-order NAV dates for {f["code"]}'
        assert all(isinstance(p[1],(int,float)) and p[1]>0 for p in points),'Invalid NAV'
        if f['option']=='Growth':
            growth+=1
            if len(set(dates).intersection(p[0] for p in bench.get('Nifty Smallcap 250 TRI',{}).get('data',[])))>=2:compared+=1
        if detail['family_id'] not in seen:
            seen.add(detail['family_id']);docs=read('data/communications/'+detail['family_id']+'.json')
            assert all(d['kind']!='news' and (d['origin']=='AMC' or d['origin'].startswith('User import')) for d in docs),'Third-party news entered the export'
            for d in docs:
                assert urlparse(d['url']).scheme in ('http','https'),'Invalid source URL'
                assert d['family']==f['family'],'Publication attached to another fund'
                assert not exclusion_reason(f['amc'],d['url'],d['title']),f'Unrelated AMC publication: {d["url"]}'
    for source,target in read('data/downloads.json').items():
        p=(root/target).resolve()
        assert source.startswith('/api/') and p.is_relative_to(root) and p.is_file(),f'Broken download: {source}'
    assert compared>0,'No growth series can be compared against the index'
    assert status['counts']['aum_funds']>0 and status['counts']['fee_funds']>0,'The requested metrics are missing'
    result={'funds':len(seen),'plans':len(funds),'growth_series':growth,'growth_series_with_comparison':compared,'aum_funds':status['counts']['aum_funds'],'expense_funds':status['counts']['fee_funds'],'checks':'passed'}
    print(json.dumps(result,indent=2));return result


if __name__=='__main__':validate(sys.argv[1] if len(sys.argv)>1 else 'site')
