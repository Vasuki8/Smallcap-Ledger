"""Read-only discovery preflight for Helios Mid Cap current digital factsheet."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker.coverage import expected_portfolio_as_of
from tracker import providers

FAMILY="Helios Mid Cap Fund"
SOURCE="https://heliosmf.in/digital-factsheet/2026/august/Mid%20cap%20fund.html"


def clean(value):
    return " ".join(str(value or "").split())


def norm(value):
    return re.sub(r"[^a-z0-9]+","",clean(value).casefold())


def main():
    expected=expected_portfolio_as_of()
    body,_,typ=providers.fetch(SOURCE,archive=False,max_bytes=12*1024*1024)
    soup=BeautifulSoup(body,"html.parser")
    text=clean(soup.get_text(" ",strip=True))
    if norm(FAMILY) not in norm(text):
        raise ValueError("Helios current-route probe lacks exact staged family identity")
    y,m,d=expected.split("-")
    month=__import__("calendar").month_name[int(m)]
    labels={
        expected,
        f"{month} {int(d)}, {y}",
        f"{int(d)} {month} {y}",
        f"{month} {int(d)} {y}",
    }
    if not any(label.casefold() in text.casefold() for label in labels):
        raise ValueError(f"Helios current-route probe does not prove portfolio date {expected}")
    tables=[]
    for table in soup.find_all("table"):
        rows=[]
        for tr in table.find_all("tr"):
            cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        header=" | ".join(rows[0]).casefold()
        if "issuer name" in header and ("% of aum" in header or "% to nav" in header):
            tables.append(rows)
    if len(tables)!=1:
        raise ValueError(f"Helios probe exposed {len(tables)} exact portfolio tables")
    rows=tables[0]
    print(json.dumps({
        "mode":"read_only_helios_midcap_portfolio_probe",
        "family":FAMILY,
        "expected_as_of":expected,
        "table_rows":len(rows)-1,
        "sample_rows":rows[1:6],
        "source":SOURCE,
        "source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
