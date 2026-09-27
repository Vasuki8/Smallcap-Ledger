"""Read-only AMFI category catalogue parser for staged expansion."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import date,datetime
from decimal import Decimal,InvalidOperation

from .categories import REGISTRY,category_from_amfi_header,get_category

AMFI_NAV_URL="https://www.amfiindia.com/spages/NAVAll.txt"


def _date(value):
    raw=str(value or "").strip().strip("()")
    for fmt in ("%Y-%m-%d","%d-%b-%Y","%d-%m-%Y","%d-%m-%y","%d %b %Y",
                "%d/%m/%Y","%d/%m/%y","%d %B %Y","%B %d, %Y","%b %d %Y"):
        try:return datetime.strptime(raw,fmt).date()
        except ValueError:pass
    raise ValueError("invalid_date")


def _nav(value):
    raw=str(value or "").replace(",","").strip()
    try:number=Decimal(raw)
    except (InvalidOperation,ValueError):raise ValueError("invalid_nav")
    if not number.is_finite() or number<=0:raise ValueError("invalid_nav")
    return number


def _headers(line):
    return [x.strip() for x in line.split(";")]


def parse_catalogue(content,category_ids=("small-cap","mid-cap"),today=None):
    today=today or date.today()
    selected=tuple(category_ids)
    if not selected:
        raise ValueError("At least one category must be selected")
    for category in selected:get_category(category)

    if isinstance(content,str):raw=content.encode("utf-8")
    else:raw=bytes(content)
    text=raw.decode("utf-8-sig",errors="replace")
    lines=text.splitlines()
    header=[];active_category=None;active_label=None;amc=""
    rows=[];rejected=[];seen={};identical_duplicates=0

    for line_number,original in enumerate(lines,1):
        line=original.strip()
        if not line:continue
        if line.startswith("Scheme Code;"):
            header=_headers(line)
            required={"Scheme Code","Scheme Name","Date"}
            if not required.issubset(header) or not ({"Net Asset Value","NAV"} & set(header)):
                raise ValueError("AMFI header is missing required fields")
            continue
        if ";" not in line:
            if "Schemes" in line and "(" in line:
                active_category=category_from_amfi_header(line)
                active_label=line
                amc=""
                if active_category not in selected:
                    active_category=None
                continue
            if active_category and not line.startswith(("Scheme","Note")):
                amc=line
            continue

        fields=line.split(";")
        if not fields or not fields[0].strip().isdigit():
            continue
        if not active_category:
            continue
        if not header:
            raise ValueError("AMFI scheme rows appeared before the header")
        record=dict(zip(header,fields))
        code=int(fields[0].strip())
        name=str(record.get("Scheme Name") or "").strip()
        plan_raw=str(record.get("Plan") or "").strip()
        option_raw=str(record.get("Option") or "").strip()
        nav_raw=str(record.get("Net Asset Value",record.get("NAV","")) or "").strip()
        date_raw=str(record.get("Date") or "").strip()
        if not amc or not name:
            rejected.append({"line":line_number,"code":code,"reason":"missing_scheme_identity"})
            continue
        try:
            nav=_nav(nav_raw);day=_date(date_raw)
        except ValueError as exc:
            rejected.append({"line":line_number,"code":code,"reason":str(exc)})
            continue
        if day>today:
            rejected.append({"line":line_number,"code":code,"reason":"future_date"})
            continue
        item={
            "code":code,"category":active_category,"amc":amc,"name":name,
            "plan_raw":plan_raw,"option_raw":option_raw,"nav_raw":nav_raw,
            "date":day.isoformat(),"source_label":active_label,"source_line":line_number,
            "isin":None if str(record.get("ISIN Div Payout/ ISIN Growth") or "").strip() in ("","-")
                   else str(record.get("ISIN Div Payout/ ISIN Growth")).strip(),
            "reinvestment_isin":None if str(record.get("ISIN Div Reinvestment") or "").strip() in ("","-")
                   else str(record.get("ISIN Div Reinvestment")).strip(),
        }
        identity=(item["category"],item["amc"],item["name"],item["plan_raw"],item["option_raw"],
                  item["date"],nav)
        if code in seen:
            if seen[code]==identity:
                identical_duplicates+=1
                continue
            raise ValueError(f"Conflicting AMFI rows for scheme code {code}")
        seen[code]=identity;rows.append(item)

    if not header:
        raise ValueError("AMFI header was not found")
    return {
        "source_url":AMFI_NAV_URL,
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "source_bytes":len(raw),
        "category_ids":list(selected),
        "registry":{key:REGISTRY[key].label for key in selected},
        "rows":rows,
        "rejected_rows":rejected,
        "identical_duplicates":identical_duplicates,
        "production_writes":0,
    }
