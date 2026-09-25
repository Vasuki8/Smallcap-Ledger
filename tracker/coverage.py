"""Auditable per-fund coverage, regenerated from the cumulative archive."""
from datetime import date,timedelta
from . import db

FEE_METRICS=('ter','ter_observed','base_expense_ratio','expense_ratio')


def expected_portfolio_as_of(today=None):
    """Operational freshness target with a 10-day new-month publication grace."""
    today=today or date.today()
    prior=today.replace(day=1)-timedelta(days=1)
    if today.day<=10:prior=prior.replace(day=1)-timedelta(days=1)
    return prior.isoformat()



def _table_exists(name):
    return bool(db.one("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)))


def _portfolio_gap_audit(family,amc,official_publications):
    """Explain a missing portfolio from retained collection/parser evidence."""
    document=db.one("""SELECT d.title,d.kind,d.url,d.last_seen,v.hash,v.observed_at
      FROM documents d
      LEFT JOIN document_versions v ON v.id=(
        SELECT id FROM document_versions WHERE document_id=d.id
        ORDER BY observed_at DESC,id DESC LIMIT 1)
      WHERE d.family=? AND d.origin='AMC' AND d.kind IN ('portfolio','factsheet')
      ORDER BY CASE d.kind WHEN 'portfolio' THEN 0 ELSE 1 END,
               COALESCE(v.observed_at,d.last_seen) DESC,d.id DESC LIMIT 1""",(family,))
    extraction=None
    if document and document.get('hash') and _table_exists('document_extractions'):
        extraction=db.one("""SELECT status,records,detail,checked_at,parser_version,source
          FROM document_extractions WHERE family=? AND hash=?
          ORDER BY checked_at DESC LIMIT 1""",(family,document['hash']))
    source_page=db.one("""SELECT amc_match,url,label,last_checked,status,detail
      FROM source_pages WHERE enabled=1
        AND (instr(lower(?),lower(amc_match))>0 OR instr(lower(amc_match),lower(?))>0)
      ORDER BY COALESCE(last_checked,'') DESC,id DESC LIMIT 1""",(amc,amc))
    if not document:
        if source_page and source_page.get('status')=='Gap':
            reason='source_unavailable'
        elif source_page and source_page.get('status') in ('Limited','Partial'):
            reason='source_not_exposing_portfolio'
        elif official_publications:
            reason='no_portfolio_document'
        else:
            reason='no_official_document'
    elif not document.get('hash'):
        reason='document_not_archived'
    elif extraction and extraction.get('status')=='error':
        reason='extraction_error'
    elif extraction and extraction.get('status')=='unrecognized':
        reason='unsupported_document_layout'
    elif extraction and extraction.get('status')=='parsed' and extraction.get('records',0):
        reason='facts_only_no_portfolio'
    elif extraction is None:
        reason='document_not_parsed'
    else:
        reason='no_holdings_extracted'
    return {'reason':reason,'document':document,'extraction':extraction,'source_page':source_page}


def report():
    rows=[];expected=expected_portfolio_as_of()
    for scheme in db.rows('SELECT DISTINCT family,amc FROM schemes ORDER BY family'):
        family=scheme['family'];row=dict(scheme)
        for key in ('aum','ter','ter_observed','base_expense_ratio','expense_ratio','benchmark'):
            if key in FEE_METRICS:
                row[key]=db.one("""SELECT as_of,value,unit,plan,source FROM metrics
                  WHERE family=? AND metric=?
                  ORDER BY as_of DESC,
                           CASE plan WHEN 'Direct' THEN 0 WHEN 'Regular' THEN 1 WHEN 'All' THEN 2 ELSE 3 END,
                           observed_at DESC LIMIT 1""",(family,key))
            else:
                row[key]=db.one('SELECT as_of,value,unit,plan,source FROM metrics WHERE family=? AND metric=? ORDER BY as_of DESC,observed_at DESC LIMIT 1',(family,key))
        row['fee']=db.one("""SELECT metric,as_of,value,unit,plan,source FROM metrics
          WHERE family=? AND plan='Direct' AND metric IN ('ter','ter_observed','base_expense_ratio','expense_ratio')
          ORDER BY CASE metric WHEN 'ter' THEN 0 WHEN 'ter_observed' THEN 1 WHEN 'base_expense_ratio' THEN 2 ELSE 3 END,
                   as_of DESC,observed_at DESC LIMIT 1""",(family,))
        row['portfolio']=db.one('''SELECT p.as_of,p.source,p.complete,COUNT(h.id) positions FROM portfolios p
          JOIN holdings h ON h.snapshot_id=p.id WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,COUNT(h.id) DESC LIMIT 1''',(family,))
        row['portfolio_complete']=bool(row['portfolio'] and row['portfolio']['complete'])
        row['portfolio_fresh']=bool(row['portfolio'] and row['portfolio']['as_of']>=expected)
        row['official_publications']=db.one("SELECT COUNT(*) n FROM documents WHERE family=? AND origin='AMC' AND kind!='source page'",(family,))['n']
        row['portfolio_gap']=None if row['portfolio'] else _portfolio_gap_audit(family,scheme['amc'],row['official_publications'])
        rows.append(row)
    gap_reasons={}
    for row in rows:
        if row.get('portfolio_gap'):
            reason=row['portfolio_gap']['reason'];gap_reasons[reason]=gap_reasons.get(reason,0)+1
    return {'built_at':db.now(),'portfolio_expected_as_of':expected,'funds':rows,'portfolio_gap_reasons':gap_reasons,'counts':{
        'funds':len(rows),'aum':sum(bool(r['aum']) for r in rows),
        'fee':sum(bool(r['fee']) for r in rows),
        'ter':sum(bool(r['ter']) for r in rows),'base_expense_ratio':sum(bool(r['base_expense_ratio']) for r in rows),
        'portfolio':sum(bool(r['portfolio']) for r in rows),
        'portfolio_complete':sum(r['portfolio_complete'] for r in rows),
        'portfolio_fresh':sum(r['portfolio_fresh'] for r in rows),
        'portfolio_fresh_complete':sum(r['portfolio_fresh'] and r['portfolio_complete'] for r in rows),
        'portfolio_partial':sum(bool(r['portfolio']) and not r['portfolio_complete'] for r in rows),
        'benchmark_identity':sum(bool(r['benchmark']) for r in rows)},
        'notes':['Coverage means at least one dated record, not necessarily the latest reporting month.',
                 f'Portfolio freshness uses {expected} as the current expected month-end, with a 10-day grace at the start of a new month.',
                 'The Direct fee column prefers reported TER, then observed TER, BER, then an explicitly unqualified expense-ratio observation; labels remain distinct.',
                 'Base expense ratio and total expense ratio are distinct.',
                 'A benchmark name does not establish availability of its historical TRI series.',
                 'Portfolio records may be partial; see each snapshot and source.']}
