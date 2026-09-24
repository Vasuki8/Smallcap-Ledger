"""One-time Bandhan public-disclosure upgrade; retain old data on failure."""
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker import db, disclosures, amc_discovery
from tracker.coverage import expected_portfolio_as_of
from tracker.bandhan_portfolios import FAMILY, PARSER_VERSION, MEDIA_HOST, MEDIA_BUCKET

UPGRADE_KEY = 'source_upgrade_' + PARSER_VERSION


def run():
    db.init()
    disclosures.seed_sources()
    if db.setting(UPGRADE_KEY, False):
        print('Bandhan monthly discovery upgrade already applied; nightly discovery remains active.')
        return True
    started = db.now()
    failures = []
    attempted = 0
    try:
        for family, url, title in amc_discovery.discover('Bandhan'):
            if family != FAMILY:
                raise ValueError('Unexpected family in Bandhan discovery')
            attempted += 1
            try:
                count = amc_discovery.store_report('Bandhan', family, url, title)
                print(f'Bandhan monthly report: {count} dated facts/holdings; {url}', flush=True)
            except Exception as exc:
                failures.append((str(exc) or type(exc).__name__).splitlines()[0][:240])
    except Exception as exc:
        failures.append((str(exc) or type(exc).__name__).splitlines()[0][:240])

    latest = db.one('''SELECT p.as_of,p.complete,p.source,COUNT(h.id) positions,SUM(h.weight) weight
      FROM portfolios p LEFT JOIN holdings h ON h.snapshot_id=p.id
      WHERE p.family=? GROUP BY p.id ORDER BY p.as_of DESC,p.id DESC LIMIT 1''', (FAMILY,))
    current = False
    if latest:
        parsed = urlparse(latest['source'])
        official_media = (parsed.hostname == MEDIA_HOST and
                          parsed.path.startswith('/' + MEDIA_BUCKET + '/'))
        current = bool(latest['as_of'] >= expected_portfolio_as_of()
                       and latest['positions'] >= 200 and official_media)
    success = bool(attempted and current and not failures)
    detail = f'Bandhan: {attempted} monthly report(s); latest={latest}; ' + '; '.join(failures)
    with db.connect() as c:
        c.execute('INSERT INTO jobs(kind,started_at,finished_at,status,detail) VALUES(?,?,?,?,?)',
                  ('amc-reports', started, db.now(), 'ok' if success else 'partial', detail))
    if success:
        with db.connect() as c:
            c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (UPGRADE_KEY, 'true'))
        print(detail, flush=True)
    else:
        print('::warning::Bandhan monthly upgrade incomplete; prior data retained. ' + detail, flush=True)
    return success


if __name__ == '__main__':
    run()
