"""One-time SBI discovery upgrade; retain old data on source failure."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracker import db, disclosures, amc_discovery
from tracker.coverage import expected_portfolio_as_of
from tracker.sbi_portfolios import FAMILY, PARSER_VERSION

UPGRADE_KEY = 'source_upgrade_' + PARSER_VERSION


def run():
    db.init()
    disclosures.seed_sources()
    if db.setting(UPGRADE_KEY, False):
        print('SBI monthly discovery upgrade already applied; nightly discovery remains active.')
        return True
    started = db.now()
    failures = []
    attempted = 0
    try:
        for family, url, title in amc_discovery.discover('SBI'):
            if family != FAMILY:
                raise ValueError('Unexpected family in SBI discovery')
            attempted += 1
            try:
                count = amc_discovery.store_report('SBI', family, url, title)
                print(f'SBI monthly report: {count} dated facts/holdings; {url}', flush=True)
            except Exception as exc:
                failures.append(str(exc).splitlines()[0][:240])
    except Exception as exc:
        failures.append(str(exc).splitlines()[0][:240])
    latest = db.one('''SELECT as_of,complete FROM portfolios WHERE family=?
      ORDER BY as_of DESC,complete DESC,id DESC LIMIT 1''', (FAMILY,))
    current = bool(latest and latest['complete'] and
                   latest['as_of'] >= expected_portfolio_as_of())
    success = bool(attempted and current and not failures)
    detail = f'SBI: {attempted} monthly report(s); latest={latest}; ' + '; '.join(failures)
    with db.connect() as c:
        c.execute('INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)',
                  ('amc-reports', started, db.now(), 'ok' if success else 'partial', detail))
    if success:
        with db.connect() as c:
            c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (UPGRADE_KEY, 'true'))
        print(detail, flush=True)
    else:
        print('::warning::SBI monthly upgrade incomplete; prior data retained. ' + detail, flush=True)
    return success


if __name__ == '__main__':
    run()
