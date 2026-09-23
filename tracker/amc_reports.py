"""Versioned extraction results and rolling official monthly report locations."""
from __future__ import annotations
import calendar
import re
from datetime import date
from urllib.parse import urlparse
from . import db

PARSER_VERSION='amc-reports-2026-09-v50'
# Parser upgrades are full-catalog by default. Versions listed here changed
# only specific family parsers and can safely avoid replaying unrelated source
# binaries. A future unlisted version automatically falls back to all families.
PARSER_UPGRADE_FAMILIES={
    'amc-reports-2026-09-v24':frozenset({'Edelweiss Small Cap Fund'}),
    'amc-reports-2026-09-v25':frozenset({'Bandhan Small Cap Fund','Bank Of India Small Cap Fund','Baroda Bnp Paribas Small Cap Fund','Franklin India Small Cap Fund','Groww Small Cap Fund','ICICI Prudential Small Cap Fund','Invesco India Small Cap Fund','Jm Small Cap Fund','LIC Mf Small Cap Fund','Pgim India Small Cap Fund','Samco Small Cap Fund','Sundaram Small Cap Fund','Tata Small Cap Fund','The Wealth Company Small Cap Fund','Trustmf Small Cap Fund','UTI Small Cap Fund','Union Small Cap Fund'}),
    'amc-reports-2026-09-v26':frozenset({'Abakkus Small Cap Fund','Baroda Bnp Paribas Small Cap Fund','HDFC Small Cap Fund','Helios Small Cap Fund','Motilal Oswal Small Cap Fund','Nippon India Small Cap Fund','Quantum Small Cap Fund','Samco Small Cap Fund','Sundaram Small Cap Fund','The Wealth Company Small Cap Fund'}),
    'amc-reports-2026-09-v27':frozenset({'Edelweiss Small Cap Fund'}),
    'amc-reports-2026-09-v28':frozenset({'Aditya Birla Sun Life Small Cap Fund'}),
    'amc-reports-2026-09-v29':frozenset({'Jm Small Cap Fund'}),
    'amc-reports-2026-09-v30':frozenset({'Jm Small Cap Fund'}),
    'amc-reports-2026-09-v31':frozenset({'ICICI Prudential Small Cap Fund'}),
    'amc-reports-2026-09-v32':frozenset({'Bank Of India Small Cap Fund'}),
    'amc-reports-2026-09-v33':frozenset({'Groww Small Cap Fund'}),
    'amc-reports-2026-09-v34':frozenset({'Quant Small Cap Fund'}),
    'amc-reports-2026-09-v35':frozenset({'Union Small Cap Fund'}),
    'amc-reports-2026-09-v36':frozenset({'Quant Small Cap Fund'}),
    'amc-reports-2026-09-v37':frozenset({'Tata Small Cap Fund'}),
    'amc-reports-2026-09-v38':frozenset({'Union Small Cap Fund'}),
    'amc-reports-2026-09-v39':frozenset({'Trustmf Small Cap Fund'}),
    'amc-reports-2026-09-v40':frozenset({'Bajaj Finserv Small Cap Fund'}),
    'amc-reports-2026-09-v41':frozenset({'Bajaj Finserv Small Cap Fund'}),
    'amc-reports-2026-09-v42':frozenset({'Bajaj Finserv Small Cap Fund'}),
    'amc-reports-2026-09-v43':frozenset({'Trustmf Small Cap Fund'}),
    'amc-reports-2026-09-v44':frozenset({'Trustmf Small Cap Fund'}),
    'amc-reports-2026-09-v45':frozenset({'Union Small Cap Fund'}),
    'amc-reports-2026-09-v46':frozenset({'Bank Of India Small Cap Fund','Baroda Bnp Paribas Small Cap Fund','Franklin India Small Cap Fund','Groww Small Cap Fund','Invesco India Small Cap Fund','LIC Mf Small Cap Fund','Pgim India Small Cap Fund','Samco Small Cap Fund','Tata Small Cap Fund','The Wealth Company Small Cap Fund','UTI Small Cap Fund'}),
    'amc-reports-2026-09-v47':frozenset({'Invesco India Small Cap Fund','The Wealth Company Small Cap Fund'}),
    'amc-reports-2026-09-v48':frozenset({'Bank Of India Small Cap Fund','Invesco India Small Cap Fund','Samco Small Cap Fund'}),
    'amc-reports-2026-09-v49':frozenset({'Abakkus Small Cap Fund','HSBC Small Cap Fund','Pgim India Small Cap Fund'}),
    'amc-reports-2026-09-v50':frozenset({'Aditya Birla Sun Life Small Cap Fund','Franklin India Small Cap Fund','LIC Mf Small Cap Fund'}),
}

def parser_upgrade_applies(family):
    targets=PARSER_UPGRADE_FAMILIES.get(PARSER_VERSION)
    return targets is None or family in targets

# v7 changes only spreadsheet portfolio interpretation; do not reparse hundreds
# of historical PDFs during the one-time upgrade.
REPROCESS_EXISTING_EXTENSIONS=('.xls','.xlsx')

def should_reprocess_existing(family,url,h=None):
    """Keep parser upgrades narrow and avoid replaying discarded portfolio history."""
    path=urlparse(url).path.lower()
    if PARSER_VERSION=='amc-reports-2026-09-v26':
        # Quantity backfill is useful only for the rolling snapshots retained in
        # portfolios. Older source documents stay archived but are not reparsed.
        return bool(h and path.endswith(REPROCESS_EXISTING_EXTENSIONS)
                    and db.one("SELECT 1 FROM portfolios WHERE family=? AND hash=?",(family,h)))
    if PARSER_VERSION=='amc-reports-2026-09-v27':
        # Edelweiss's current September factsheet is already archived. Replay
        # only this fund's official PDFs so the Top-30 parser can advance the
        # rolling portfolio from July to the August month-end.
        return family=='Edelweiss Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v28':
        # ABSL's already archived monthly factsheet contains a full reconciled
        # Small Cap portfolio page. Re-open only ABSL PDFs for this parser bump.
        return family=='Aditya Birla Sun Life Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v29':
        # JM's current monthly factsheets are already archived. Re-open only JM
        # PDFs so the reconciled Top-25 parser can recover the latest snapshot.
        return family=='Jm Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v30':
        # JM changed PDF text ordering across monthly factsheets. Replay only
        # archived JM PDFs for the table-header anchored Top-25 parser.
        return family=='Jm Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v31':
        # ICICI's current consolidated factsheet is already archived. Replay
        # only ICICI PDFs for the reconciled two-page named-holdings parser.
        return family=='ICICI Prudential Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v32':
        # BOI's current factsheet is already archived. Replay only BOI PDFs for
        # the real four-column portfolio reconstruction.
        return family=='Bank Of India Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v34':
        # quant's retained monthly factsheets publish a validated Top-10 table.
        # Replay only quant PDFs; the snapshot stays explicitly partial.
        return family=='Quant Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v35':
        # Union's versioned Small Cap factsheet publishes the complete portfolio.
        return family=='Union Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v36':
        # Replay only quant PDFs after matching the AMC's real text extraction.
        return family=='Quant Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v38':
        # Retry Union's versioned official Small Cap factsheet after the
        # corrected complete-portfolio regression fixture.
        return family=='Union Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v39':
        # Replay only TRUSTMF's reviewed official Small Cap factsheet. The
        # resulting named-holdings snapshot remains explicitly partial.
        return family=='Trustmf Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v40':
        # Bajaj's August 2026 Small Cap PDF is already retained in cumulative
        # history. Materialize and replay it without depending on the 403
        # landing page or a new network transfer.
        return family=='Bajaj Finserv Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v41':
        return family=='Bajaj Finserv Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v42':
        # Replay retained Bajaj PDF with the real two-page Top-10 + aggregate layout.
        return family=='Bajaj Finserv Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v43':
        # Retry TRUSTMF using reviewed alternate monthly factsheet URLs. Existing
        # content-signature guards reject HTML app shells at .pdf routes.
        return family=='Trustmf Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v44':
        # v44 discovers TRUSTMF's current monthly disclosure through its
        # first-party API instead of replaying stale HTML-at-PDF routes.
        return False
    if PARSER_VERSION=='amc-reports-2026-09-v45':
        # Union's primary single-scheme route is unreachable from GitHub Actions.
        # Replay only Union PDFs and try reviewed official fallback/alternate routes.
        return family=='Union Small Cap Fund' and path.endswith('.pdf')
    if PARSER_VERSION=='amc-reports-2026-09-v46':
        # v46 backfills benchmark identity from reviewed catalog sources only.
        # The catalog pass materializes those exact originals; do not replay the
        # broader historical document archive for this metadata-only change.
        return False
    if PARSER_VERSION=='amc-reports-2026-09-v47':
        # v47 replays the reviewed sources added after v46 was already marked
        # applied. This remains a metadata-only exact-catalog replay.
        return False
    if PARSER_VERSION=='amc-reports-2026-09-v48':
        # v48 uses current, exact official fund pages for benchmark identity.
        # No historical source replay is needed.
        return False
    if PARSER_VERSION=='amc-reports-2026-09-v49':
        # v49 fetches current official August sources; no historical replay.
        return False
    if PARSER_VERSION=='amc-reports-2026-09-v50':
        # v50 discovers current official factsheets/portfolio downloads.
        return False
    if path.endswith(REPROCESS_EXISTING_EXTENSIONS):return True
    if family=='Bank Of India Small Cap Fund' and path.endswith('.pdf'):return True
    # v25 only changes strict benchmark-label parsing. Re-open retained PDF
    # evidence solely for the families that were missing benchmark identity.
    if PARSER_VERSION=='amc-reports-2026-09-v25' and parser_upgrade_applies(family) and path.endswith('.pdf'):return True
    return False



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
        yield ('JM Financial',f'https://www.jmfinancialmf.com/CMS/downloads/Factsheet/Factsheet/Factsheet%20{calendar.month_name[month]}%20{year}.pdf','Monthly factsheet')
        yield ('HSBC',f'https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-{name}-{year}.pdf','Monthly factsheet')
        yield ('Kotak',f'https://www.kotakmf.com/factsheet/{calendar.month_name[month]}_{year}/kotak/SMALL-CAP.html','Small cap monthly factsheet')


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
        elif content.startswith(b'PK') and path.endswith('.zip') and family=='UTI Small Cap Fund':
            from .structured_reports import uti_zip
            uti_zip(content,family,url,h)
        elif content.startswith((b'PK',b'\xd0\xcf')) and path.endswith(('.xls','.xlsx')):
            disclosures.spreadsheet(content,family,url,h)
        elif path.endswith('.xml'):
            disclosures.summary_xml(content,family,url,h)
        else:
            from .structured_reports import extract as structured
            if structured(content,family,url,h) is None:
                from . import amc_metrics
                known=any(f==family and u==url for _,f,u in amc_metrics.PAGES)
                digital=family in ('Mahindra Manulife Small Cap Fund','Iti Small Cap Fund','Canara Robeco Small Cap Fund') and 'factsheet/' in url.lower()
                kotak_monthly=family=='Kotak Small Cap Fund' and bool(re.fullmatch(r'/factsheet/[A-Za-z]+_\d{4}/kotak/SMALL-CAP\.html',urlparse(url).path,re.I))
                if not known and not digital and not kotak_monthly:return 0
                amc_metrics.parse_page(content,family,url,h)
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
        if not parser_upgrade_applies(row['family']):continue
        if exclusion_reason(row['family'],row['url']):continue
        if classify('',row['url']) not in ('factsheet','portfolio','scheme document'):continue
        if not should_reprocess_existing(row['family'],row['url'],row['hash']):continue
        try:
            extract((db.DATA/row['path']).read_bytes(),row['family'],row['url'],row['hash']);checked+=1
        except Exception as e:gaps.append(row['family']+': '+str(e)[:120])
    return checked,gaps
