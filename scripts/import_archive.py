"""Accept owner-supplied additions only if the current history is preserved."""
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
try:
    from .github_state import db,download_asset,repository,unpack
except ImportError:
    from github_state import db,download_asset,repository,unpack


def check_superset(old,new):
    with sqlite3.connect(old/'ledger.sqlite3') as c:
        c.execute('ATTACH DATABASE ? AS incoming',(str(new/'ledger.sqlite3'),))
        # Identifiers must remain stable because they join files and snapshots.
        # Daily collection may advance current NAVs, while these historical rows
        # are append-only and may never be lost by an import.
        for table in ('nav_observations','benchmark_observations','archives','metrics','portfolios','holdings','documents','document_versions'):
            columns=[r[1] for r in c.execute(f'PRAGMA main.table_info({table})') if r[1] not in ('last_seen',)]
            if table=='documents':columns=['id','family','url','first_seen']
            fields=','.join('"'+v+'"' for v in columns)
            if c.execute(f'SELECT {fields} FROM main.{table} EXCEPT SELECT {fields} FROM incoming.{table} LIMIT 1').fetchone():
                raise ValueError('Import would lose or rewrite retained '+table+' records. Start again from the latest archive.')
        for table,fields in [('schemes','code'),('nav','code,date'),('benchmark','name,date')]:
            if c.execute(f'SELECT {fields} FROM main.{table} EXCEPT SELECT {fields} FROM incoming.{table} LIMIT 1').fetchone():
                raise ValueError('Import would remove historical '+table+' coverage. Restore the latest archive first.')


if __name__=='__main__':
    asset=os.environ['IMPORT_ARCHIVE_ASSET']
    if not asset.endswith('.zip'):raise ValueError('Choose a ZIP asset containing cumulative data')
    with tempfile.TemporaryDirectory(dir=db.DATA.parent) as tmp:
        zip_path=download_asset(repository(),asset,tmp);incoming=Path(tmp)/'incoming'
        unpack(zip_path,incoming);check_superset(db.DATA,incoming)
        previous=Path(tmp)/'previous';shutil.move(str(db.DATA),previous)
        try:shutil.move(str(incoming),db.DATA)
        except BaseException:shutil.move(str(previous),db.DATA);raise
    print('Imported additions; all previously retained history was preserved')
