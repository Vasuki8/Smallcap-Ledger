"""Temporary read-only diagnostic for retained JM Small Cap factsheet layout."""
from __future__ import annotations
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pypdf import PdfReader
from tracker import db
from scripts.github_state import materialize_hashes

FAMILY='Jm Small Cap Fund'

def main():
    db.init()
    rows=db.rows("""SELECT d.title,d.url,dv.hash,a.path,dv.observed_at
      FROM documents d
      JOIN document_versions dv ON dv.document_id=d.id
      JOIN archives a ON a.hash=dv.hash
      WHERE d.family=? AND d.kind='factsheet'
      ORDER BY dv.observed_at DESC LIMIT 6""",(FAMILY,))
    if not rows:
        print('JM_LAYOUT_DIAGNOSTIC=no factsheet versions',flush=True);return
    materialize_hashes([r['hash'] for r in rows])
    for row in rows:
        path=(db.DATA/row['path']).resolve()
        reader=PdfReader(path)
        for index,page in enumerate(reader.pages):
            text=page.extract_text() or ''
            if not re.search(r'(?:SCHEME\s+PORTFOLIO|TOP\s*25\s+STOCKS|Other\s+Equity\s+Stocks|JM\s+Small\s+Cap\s+Fund)',text,re.I):
                continue
            payload={
              'title':row['title'],'url':row['url'],'hash':row['hash'],
              'page':index+1,'pages':len(reader.pages),
              'text':text[:9000],
            }
            print('JM_LAYOUT_PAGE='+json.dumps(payload,ensure_ascii=False,separators=(',',':')),flush=True)

if __name__=='__main__':
    main()
