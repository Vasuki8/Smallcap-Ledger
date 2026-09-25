"""One-time read-only diagnostic for historical NAV gaps flagged by the audit."""
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
TARGETS=(
    {
        "code":105804,
        "amc":3,
        "isin":"INF209K01EN2",
        "family":"Aditya Birla Sun Life Small Cap Fund",
        "from":"2010-05-31",
        "to":"2010-06-08",
    },
    {
        "code":105989,
        "amc":6,
        "isin":"INF740K01797",
        "family":"DSP Small Cap Fund",
        "from":"2007-08-08",
        "to":"2007-08-16",
    },
    {
        "code":105989,
        "amc":6,
        "isin":"INF740K01797",
        "family":"DSP Small Cap Fund",
        "from":"2008-08-27",
        "to":"2008-09-04",
    },
    {
        "code":105989,
        "amc":6,
        "isin":"INF740K01797",
        "family":"DSP Small Cap Fund",
        "from":"2010-03-17",
        "to":"2010-03-25",
    },
    {
        "code":105989,
        "amc":6,
        "isin":"INF740K01797",
        "family":"DSP Small Cap Fund",
        "from":"2010-04-07",
        "to":"2010-04-15",
    },
)

def amfi_date(day: str) -> str:
    return date.fromisoformat(day).strftime("%d-%b-%Y")

def parse_rows(text: str, code: int):
    rows=[]
    for raw in text.lstrip("\ufeff").splitlines():
        line=raw.strip()
        if not line or ";" not in line:continue
        parts=[x.strip() for x in line.split(";")]
        if not parts or not parts[0].isdigit() or int(parts[0])!=code:continue
        rows.append(parts)
    return rows

def main():
    for target in TARGETS:
        query=urlencode({
            "mf":target["amc"],
            "frmdt":amfi_date(target["from"]),
            "todt":amfi_date(target["to"]),
        })
        url=f"{BASE}?{query}"
        body,_,mime=providers.fetch(url,archive=False,max_bytes=8*1024*1024)
        text=body.decode("utf-8-sig",errors="replace")
        rows=parse_rows(text,target["code"])
        print("NAV_GAP_AUDIT",target["family"],target["code"],target["from"],target["to"],flush=True)
        print("NAV_GAP_SOURCE",url,"bytes="+str(len(body)),"mime="+str(mime),
              "sha256="+hashlib.sha256(body).hexdigest(),flush=True)
        print("NAV_GAP_HEADER",next((x.strip() for x in text.splitlines() if x.strip().startswith("Scheme Code;")),"missing"),flush=True)
        print("NAV_GAP_ROWS",len(rows),flush=True)
        for row in rows:
            print("NAV_GAP_ROW",";".join(row),flush=True)
        if not rows:
            print("::warning::No exact scheme-code rows returned for "+target["family"],flush=True)

if __name__=="__main__":
    main()
