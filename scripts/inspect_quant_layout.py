"""Temporary read-only diagnostic for retained quant Small Cap factsheet pages."""
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

FAMILY='Quant Small Cap Fund'

def main():
    db.init()
    rows=db.rows("""SELECT d.title,d.url,dv.hash,a.path,dv.observed_at
      FROM documents d
      JOIN document_versions dv ON dv.document_id=d.id
      JOIN archives a ON a.hash=dv.hash
      WHERE d.family=? AND d.kind='factsheet'
      ORDER BY dv.observed_at DESC LIMIT 5""",(FAMILY,))
    if not rows:
        print('QUANT_LAYOUT_DIAGNOSTIC=no factsheet versions',flush=True);return
    materialize_hashes([r['hash'] for r in rows])
    pattern=re.compile(r'quant\s+Small\s+Cap\s+Fund',re.I)
    for row in rows:
        path=(db.DATA/row['path']).resolve()
        if not path.exists():
            print('QUANT_LAYOUT_MISSING='+json.dumps({'url':row['url'],'hash':row['hash']},separators=(',',':')),flush=True)
            continue
        reader=PdfReader(path)
        texts=[p.extract_text() or '' for p in reader.pages]
        hits=[i for i,t in enumerate(texts) if pattern.search(t)]
        wanted=sorted({j for i in hits for j in (i-1,i,i+1) if 0<=j<len(texts)})
        for index in wanted[:8]:
            page=reader.pages[index]
            text=page.extract_text() or ''
            layout=page.extract_text(extraction_mode='layout') or ''
            payload={
              'title':row['title'],'url':row['url'],'hash':row['hash'],
              'observed_at':row['observed_at'],'page':index+1,'pages':len(reader.pages),
              'matched_scheme':bool(pattern.search(text)),
              'text':text[:18000],
              'layout':layout[:18000] if layout!=text else '',
            }
            print('QUANT_LAYOUT_PAGE='+json.dumps(payload,ensure_ascii=False,separators=(',',':')),flush=True)

if __name__=='__main__':
    main()
