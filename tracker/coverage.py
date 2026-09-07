"""Auditable per-fund coverage, regenerated from the cumulative archive."""
from . import db


def report():
    rows=[]
    for scheme in db.rows('SELECT DISTINCT family,amc FROM schemes ORDER BY family'):
        family=scheme['family'];row=dict(scheme)
        for key in ('aum','ter','base_expense_ratio','benchmark'):
            row[key]=db.one('SELECT as_of,value,unit,plan,source FROM metrics WHERE family=? AND metric=? ORDER BY as_of DESC,observed_at DESC LIMIT 1',(family,key))
        row['portfolio']=db.one('''SELECT p.as_of,p.source,p.complete,COUNT(h.id) positions FROM portfolios p
          JOIN holdings h ON h.snapshot_id=p.id WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,COUNT(h.id) DESC LIMIT 1''',(family,))
        row['official_publications']=db.one("SELECT COUNT(*) n FROM documents WHERE family=? AND origin='AMC' AND kind!='source page'",(family,))['n']
        rows.append(row)
    return {'built_at':db.now(),'funds':rows,'counts':{
        'funds':len(rows),'aum':sum(bool(r['aum']) for r in rows),
        'ter':sum(bool(r['ter']) for r in rows),'base_expense_ratio':sum(bool(r['base_expense_ratio']) for r in rows),
        'portfolio':sum(bool(r['portfolio']) for r in rows),
        'benchmark_identity':sum(bool(r['benchmark']) for r in rows)},
        'notes':['Coverage means at least one dated record, not necessarily the latest reporting month.',
                 'Base expense ratio and total expense ratio are distinct.',
                 'A benchmark name does not establish availability of its historical TRI series.',
                 'Portfolio records may be partial; see each snapshot and source.']}
