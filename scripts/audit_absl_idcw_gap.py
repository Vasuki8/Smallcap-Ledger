"""One-time read-only exact option-level audit for ABSL Regular IDCW 105805."""
from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

BASE="https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
CODE=105805
FROM="2010-05-31"
TO="2010-06-08"

def amfi_date(day):
    return date.fromisoformat(day).strftime("%d-%b-%Y")

def rows_for_code(text):
    rows=[]
    for raw in text.lstrip("\ufeff").splitlines():
        line=raw.strip()
        if ";" not in line:
            continue
        parts=[x.strip() for x in line.split(";")]
        if parts and parts[0].isdigit() and int(parts[0])==CODE:
            rows.append(parts)
    return rows

def main():
    query=urlencode({"mf":3,"frmdt":amfi_date(FROM),"todt":amfi_date(TO)})
    url=f"{BASE}?{query}"
    body,_,mime=providers.fetch(url,archive=False,max_bytes=8*1024*1024)
    text=body.decode("utf-8-sig",errors="replace")
    rows=rows_for_code(text)
    print("ABSL_IDCW_GAP_SOURCE",url,flush=True)
    print("ABSL_IDCW_GAP_META",f"bytes={len(body)}",f"mime={mime}",
          "sha256="+hashlib.sha256(body).hexdigest(),flush=True)
    print("ABSL_IDCW_GAP_ROWS",len(rows),flush=True)
    for row in rows:
        print("ABSL_IDCW_GAP_ROW",";".join(row),flush=True)
    if len(rows)!=2:
        print("::warning::Expected exactly the retained boundary observations for scheme 105805",flush=True)

if __name__=="__main__":
    main()
