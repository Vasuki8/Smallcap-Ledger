"""Temporary read-only diagnostic for retained Bank of India Small Cap factsheets."""
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

FAMILY='Bank Of India Small Cap Fund'

def main():
    db.init()
    rows=db.rows("""SELECT d.title,d.url,dv.hash,a.path,dv.observed_at
      FROM documents d
      JOIN document_versions dv ON dv.document_id=d.id
      JOIN archives a ON a.hash=dv.hash
      WHERE d.family=? AND d.kind='factsheet'
      ORDER BY dv.observed_at DESC LIMIT 4""",(FAMILY,))
    if not rows:
        print('BOI_LAYOUT_DIAGNOSTIC=no factsheet versions',flush=True);return
    materialize_hashes([r['hash'] for r in rows])
    pattern=re.compile(r'Bank\s+of\s+India\s+Small\s+Cap\s+Fund',re.I)
    portfolio=re.compile(r'Portfolio\s+Holdings|EQUITY\s+HOLDINGS|GRAND\s+TOTAL',re.I)
    for row in rows:
        path=(db.DATA/row['path']).resolve()
        reader=PdfReader(path)
        texts=[p.extract_text() or '' for p in reader.pages]
        hits=[i for i,t in enumerate(texts) if pattern.search(t) or portfolio.search(t)]
        wanted=sorted({j for i in hits for j in (i-1,i,i+1) if 0<=j<len(texts)})
        for index in wanted[:12]:
            page=reader.pages[index]
            text=texts[index]
            layout=page.extract_text(extraction_mode='layout') or ''
            payload={
              'title':row['title'],'url':row['url'],'hash':row['hash'],
              'page':index+1,'pages':len(reader.pages),
              'matched_scheme':bool(pattern.search(text)),
              'matched_portfolio':bool(portfolio.search(text)),
              'text':text[:16000],
              'layout':layout[:16000] if layout!=text else '',
            }
            print('BOI_LAYOUT_PAGE='+json.dumps(payload,ensure_ascii=False,separators=(',',':')),flush=True)

if __name__=='__main__':
    main()
