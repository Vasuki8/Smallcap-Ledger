"""Versioned extraction results and rolling official monthly report locations."""
from __future__ import annotations
import calendar
from datetime import date
from urllib.parse import urlparse
from . import db

PARSER_VERSION='amc-reports-2026-09-v2'


def monthly_sources(today=None):
    today=today or date.today()
    for offset in range(3):
        year,month=divmod(today.year*12+today.month-1-offset,12);month+=1
        name=calendar.month_name[month].lower()
        # These are public monthly publication conventions verified against downloaded
        # July reports. A missing/newly changed path remains an explicit source gap.
        yield ('Canara',f'https://digitalassets.canararobeco.com/digital-factsheet/{year}/{name}/Scheme/Factsheet.pdf','Monthly factsheet')
        yield ('Invesco',f'https://www.invescomutualfund.com/docs/default-source/factsheet/invesco-mf-factsheet-{name}-{year}.pdf','Monthly factsheet')
        yield ('Mirae',f'https://www.miraeassetmf.co.in/docs/default-source/fachsheet/active-factsheet---{name}-{year}.pdf','Monthly active factsheet')
        yield ('SBI',f'https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-small-cap-fund-factsheet-{name}-{year}.pdf','Small cap monthly factsheet')


def init():
    with db.connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS document_extractions(
          family TEXT NOT NULL,hash TEXT NOT NULL,parser_version TEXT NOT NULL,
          source TEXT NOT NULL,status TEXT NOT NULL,records INTEGER NOT NULL,
          detail TEXT NOT NULL,checked_at TEXT NOT NULL,
          PRIMARY KEY(family,hash,parser_version))''')


def extract(content,family,url,h):
    """Cache only successful parsing, including an explicit unrecognized-layout result."""
    from . import disclosures
    from .publications import exclusion_reason
    if exclusion_reason(family,url):return 0
    init()
    old=db.one('SELECT * FROM document_extractions WHERE family=? AND hash=? AND parser_version=?',
               (family,h,PARSER_VERSION))
    if old and old['status']!='error':return old['records']
    try:
        path=urlparse(url).path.lower()
        if content.startswith(b'%PDF'):
            from .providers import classify
            # SID/KIM can state regulatory maximum expenses, not actual current fees.
            if classify('',url)!='scheme document':disclosures.factsheet_pdf(content,family,url,h)
        elif content.startswith((b'PK',b'\xd0\xcf')) and path.endswith(('.xls','.xlsx')):
            disclosures.spreadsheet(content,family,url,h)
        elif path.endswith('.xml'):
            disclosures.summary_xml(content,family,url,h)
        else:return 0
        metrics=db.one('SELECT COUNT(*) n FROM metrics WHERE family=? AND hash=?',(family,h))['n']
        holdings=db.one('SELECT COUNT(*) n FROM holdings h JOIN portfolios p ON p.id=h.snapshot_id WHERE p.family=? AND p.hash=?',(family,h))['n']
        count=metrics+holdings
        status='parsed' if count else 'unrecognized'
        detail=f'{metrics} dated facts; {holdings} holdings (portfolio may be partial)' if count else 'Original archived; no supported, unambiguous dated scheme table found'
    except Exception as e:
        status='error';count=0;detail=f'{type(e).__name__}: {str(e)[:250]}'
    with db.connect() as c:
        c.execute('INSERT OR REPLACE INTO document_extractions VALUES(?,?,?,?,?,?,?,?)',
                  (family,h,PARSER_VERSION,url,status,count,detail,db.now()))
    if status=='error':raise ValueError(detail)
    return count


def reprocess_archived():
    """Upgrade extracted facts in place. Never replace the cumulative database."""
    from .providers import classify
    from .publications import exclusion_reason
    init();checked=0;gaps=[]
    rows=db.rows('''SELECT DISTINCT d.family,d.url,v.hash,a.path FROM documents d
      JOIN document_versions v ON v.document_id=d.id JOIN archives a ON a.hash=v.hash
      LEFT JOIN document_extractions e ON e.family=d.family AND e.hash=v.hash AND e.parser_version=?
      WHERE d.origin='AMC' AND e.hash IS NULL ORDER BY d.last_seen DESC''',(PARSER_VERSION,))
    for row in rows:
        if exclusion_reason(row['family'],row['url']):continue
        if classify('',row['url']) not in ('factsheet','portfolio','scheme document'):continue
        try:
            extract((db.DATA/row['path']).read_bytes(),row['family'],row['url'],row['hash']);checked+=1
        except Exception as e:gaps.append(row['family']+': '+str(e)[:120])
    return checked,gaps
