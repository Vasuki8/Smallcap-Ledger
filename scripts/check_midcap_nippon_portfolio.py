"""Read-only diagnostic for Nippon India August 2026 Top-10 holdings workbook."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers

SOURCE=(
    "https://mf.nipponindiaim.com/InvestorServices/Top%2010%20holdings/"
    "IN-MF-TOP-10-ISSUER-AND-SECTOR-ALLOCATION-Corporate-Bond-fund-Aug-2026.xls"
)
TARGETS=("Nippon India Growth Mid Cap Fund","Growth Mid Cap Fund")


def clean(value):
    return " ".join(str(value or "").split())


def main():
    body,_,typ=providers.fetch(SOURCE,archive=False,max_bytes=30*1024*1024)
    hits=[]
    sheets=[]
    if body.startswith(b"PK"):
        import openpyxl
        book=openpyxl.load_workbook(io.BytesIO(body),data_only=True,read_only=True)
        try:
            for sheet in book.worksheets[:50]:
                sheet_hits=[]
                rows=list(sheet.iter_rows(values_only=True))
                for r,row in enumerate(rows):
                    values=[clean(v) for v in row[:20]]
                    text=" | ".join(v for v in values if v)
                    if any(target.casefold() in text.casefold() for target in TARGETS):
                        sheet_hits.append({
                            "row":r+1,
                            "values":values,
                            "context":[
                                [clean(v) for v in rows[rr][:20]]
                                for rr in range(max(0,r-4),min(len(rows),r+18))
                            ],
                        })
                if sheet_hits:
                    hits.extend({"sheet":sheet.title,**hit} for hit in sheet_hits)
                sheets.append({
                    "name":sheet.title,
                    "nrows":sheet.max_row,
                    "ncols":sheet.max_column,
                })
        finally:
            book.close()
        actual_format="xlsx"
    elif body.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        import xlrd
        book=xlrd.open_workbook(file_contents=body,on_demand=True)
        try:
            for name in book.sheet_names()[:50]:
                sheet=book.sheet_by_name(name)
                sheet_hits=[]
                for r in range(sheet.nrows):
                    values=[clean(sheet.cell_value(r,c)) for c in range(min(sheet.ncols,20))]
                    text=" | ".join(v for v in values if v)
                    if any(target.casefold() in text.casefold() for target in TARGETS):
                        sheet_hits.append({
                            "row":r+1,
                            "values":values,
                            "context":[
                                [clean(sheet.cell_value(rr,c)) for c in range(min(sheet.ncols,20))]
                                for rr in range(max(0,r-4),min(sheet.nrows,r+18))
                            ],
                        })
                if sheet_hits:
                    hits.extend({"sheet":name,**hit} for hit in sheet_hits)
                sheets.append({"name":name,"nrows":sheet.nrows,"ncols":sheet.ncols})
        finally:
            book.release_resources()
        actual_format="xls"
    else:
        raise ValueError("Nippon Top-10 download is not a supported Excel workbook")
    print(json.dumps({
        "mode":"read_only_nippon_aug2026_top10_diagnostic",
        "source":SOURCE,
        "source_sha256":hashlib.sha256(body).hexdigest(),
        "source_content_type":typ,
        "actual_format":actual_format,
        "sheets":sheets,
        "matches":hits[:20],
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    if not hits:
        raise ValueError("Nippon August Top-10 workbook has no exact Growth Mid Cap identity")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
