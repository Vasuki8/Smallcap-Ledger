"""Small, auditable backfill from publicly readable official reports.

These are reviewed observations, not a claim that automatic PDF retrieval worked.
The original URL remains the source; no synthetic original-file hash is assigned.
"""
import json
from functools import lru_cache
from datetime import date
from . import db


@lru_cache(maxsize=1)
def reports():
    return json.loads((db.ROOT/'tracker/reviewed_reports.json').read_text())


def apply():
    from .disclosures import official_publication_url
    from .providers import save_document
    count=0
    for r in reports():
        if not db.one('SELECT code FROM schemes WHERE family=?',(r['family'],)):continue
        if not official_publication_url(r['source'],r['amc']):raise ValueError('Reviewed report is not an official AMC source')
        if r['as_of']>date.today().isoformat():raise ValueError('Future reviewed report date')
        for f in r['facts']:
            metric=f['metric'];v=f['value']
            if metric not in ('aum','average_aum','ter','base_expense_ratio'):raise ValueError('Unsupported reviewed figure')
            if not 0<=v<(10_000_000 if 'aum' in metric else 5):raise ValueError('Invalid reviewed figure')
            db.metric(r['family'],f.get('plan','All'),metric,r['as_of'],v,'INR crore' if 'aum' in metric else '% p.a.',r['source'])
            count+=1
        save_document(r['family'],r['title'],r['source'],'factsheet','Fund',origin='AMC')
    return count


def annotate(fact):
    if fact.get('hash'):return fact
    for r in reports():
        if (fact['family'],fact['as_of'],fact['source'])!=(r['family'],r['as_of'],r['source']):continue
        if any((fact['metric'],fact['plan'],float(fact['value']))==(f['metric'],f.get('plan','All'),f['value']) for f in r['facts']):
            fact['source_note']='Reviewed official report · '+r['note']
            fact['reviewed_at']=r['reviewed_at']
    return fact
