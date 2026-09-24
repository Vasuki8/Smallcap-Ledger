"""Official AMC expense disclosures that are not currently present in AMFI's Small Cap feed."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import base64
import hashlib
import io
import json
import re
import shutil
import subprocess
import uuid
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode

import httpx
import openpyxl

from . import db
from .providers import fetch, number, public_url

CANARA_FAMILY = "Canara Robeco Small Cap Fund"
CANARA_SCHEME_CODE = "SC"
CANARA_PAGE = "https://www.canararobeco.com/expense-ratio"
CANARA_API = "https://www.canararobeco.com/wp-json/ter/v1/records"
CANARA_PLANS = {"Regular Plan": "Regular", "Direct Plan": "Direct"}

ICICI_FAMILY = "ICICI Prudential Small Cap Fund"
ICICI_TER_PAGE = "https://www.icicipruamc.com/about-us/financials-&-disclosures?currentTabFilter=Total%20Expense%20Ratio"
ICICI_API_BASE = "https://apimf.icicipruamc.com"
ICICI_CATEGORIES_API = ICICI_API_BASE + "/fds/v1/categories"
ICICI_FILES_API = ICICI_API_BASE + "/fds/v1/files"
ICICI_FILE_BASE = "https://app.beta.icicipruamc.com/blob"
ICICI_TER_CATEGORY_CODE = "TOTAL_EXPENSE_RATIO"
ICICI_TER_SUBCATEGORY_CODE = "TOTAL_EXPENSE_RATIO"
ICICI_TER_TITLE = "Total Expense Ratio"
ICICI_TER_SHOW = "TER Details"
_ICICI_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_ICICI_TITLE = re.compile(r"^TotalExpenseRatio([A-Za-z]+)(20\d{2})$")
_ICICI_FILE = re.compile(r"^TotalExpenseRatio([A-Za-z]+)(20\d{2})\.xlsx$", re.I)
_ICICI_HEADER = {
    "A": "Scheme Name",
    "B": "Date (DD/MM/YYYY)",
    "C": "Base Expense Ratio (BER) (%)",
    "D": "Brokerage cost (%)",
    "E": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "F": "Statutory Levies (including GST) (%)",
    "G": "Total TER (%)",
    "H": "Base Expense Ratio (BER) (%)",
    "I": "Brokerage cost (%)",
    "J": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "K": "Statutory Levies (including GST) (%)",
    "L": "Total TER (%)",
}

HSBC_FAMILY = "HSBC Small Cap Fund"
HSBC_SCHEME_CODE = "HEMIDF"
HSBC_NSDL_CODE = "LTMF/O/E/SCF/14/02/0023"
HSBC_TER_LINK = "https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx"
HSBC_CAMS_API = "https://digital.camsonline.com/api/v1/camsonline"
_HSBC_IV = b"globalaesvectors"
_HSBC_REQUEST_SECRET = "TkVJTEhobWFj"
_HSBC_RESPONSE_SECRET = "UkRYTElobWFj"
_HSBC_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_HSBC_HEADER = (
    "Scheme Code",
    "NSDL Scheme Code",
    "Scheme Name",
    "TER Date",
    "Regular Plan - Base Expense Ratio (BER) (%)",
    "Regular Plan - Brokerage cost (%)",
    "Regular Plan - Transaction Cost incurred for the purpose of execution of trade (%)",
    "Regular Plan - Statutory Levies (including GST) (%)",
    "Regular Plan - Total TER (%)",
    "Direct Plan - Base Expense Ratio (BER) (%)",
    "Direct Plan - Brokerage cost (%)",
    "Direct Plan - Transaction Cost incurred for the purpose of execution of trade (%)",
    "Direct Plan - Statutory Levies (including GST) (%)",
    "Direct Plan - Total TER (%)",
)


def _value(row, field):
    raw = row.get(field)
    if raw is None or str(raw).strip() in ("", "-", "NA", "N/A"):
        raise ValueError(f"Canara expense row is missing {field}")
    value = number(raw)
    if not 0 <= value <= 5:
        raise ValueError(f"Canara expense {field} is outside the accepted range")
    return value


def parse_canara_records(records, today=None):
    """Return the latest exact two-plan Small Cap BER/TER disclosure.

    The public Canara page uses this first-party JSON API in the browser.
    We retain only the AMC-published base_ter and total_ter fields; components
    are not recomputed into a TER.
    """
    today = today or date.today()
    if not isinstance(records, list):
        raise ValueError("Canara TER API response changed format")

    grouped = defaultdict(list)
    for row in records:
        if not isinstance(row, dict):
            continue
        if str(row.get("scheme_name", "")).strip() != CANARA_FAMILY:
            continue
        if str(row.get("sch_code", "")).strip().upper() != CANARA_SCHEME_CODE:
            continue
        plan = str(row.get("plan_type", "")).strip()
        if plan not in CANARA_PLANS:
            continue
        day = str(row.get("date", "")).strip()
        try:
            parsed = date.fromisoformat(day)
        except ValueError:
            continue
        if parsed > today:
            continue
        grouped[day].append(row)

    for day in sorted(grouped, reverse=True):
        rows = grouped[day]
        by_plan = defaultdict(list)
        for row in rows:
            by_plan[str(row.get("plan_type", "")).strip()].append(row)
        if set(by_plan) != set(CANARA_PLANS):
            continue
        if any(len(by_plan[p]) != 1 for p in CANARA_PLANS):
            raise ValueError(f"Canara TER API returned duplicate plan rows for {day}")

        result = {}
        for published_plan, plan in CANARA_PLANS.items():
            row = by_plan[published_plan][0]
            ber = _value(row, "base_ter")
            ter = _value(row, "total_ter")
            if ter + 1e-9 < ber:
                raise ValueError(f"Canara Total TER is below BER for {published_plan} on {day}")
            result[plan] = {"base_expense_ratio": ber, "ter": ter}
        return day, result

    raise ValueError("Canara TER API returned no complete dated Small Cap plan pair")


def canara(progress=lambda _: None, today=None, lookback_days=7):
    """Collect current Canara Robeco Small Cap BER/TER from its browser API."""
    today = today or date.today()
    if lookback_days < 1:
        raise ValueError("Canara expense lookback must be at least one day")
    if not db.one("SELECT code FROM schemes WHERE family=? LIMIT 1", (CANARA_FAMILY,)):
        return "Canara Small Cap is not in the active universe"

    start = today - timedelta(days=lookback_days - 1)
    url = CANARA_API + "?" + urlencode(
        {"from_date": start.isoformat(), "to_date": today.isoformat()}
    )
    progress("Canara Robeco expense ratios · official TER API")
    body, content_hash, _ = fetch(url, max_bytes=2 * 1024 * 1024)
    try:
        records = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Canara TER API returned invalid JSON") from exc

    day, plans = parse_canara_records(records, today)
    for plan, values in plans.items():
        db.metric(
            CANARA_FAMILY,
            plan,
            "base_expense_ratio",
            day,
            values["base_expense_ratio"],
            "% p.a. · reported by AMC",
            url,
            content_hash,
        )
        db.metric(
            CANARA_FAMILY,
            plan,
            "ter",
            day,
            values["ter"],
            "% p.a. · reported by AMC",
            url,
            content_hash,
        )
    return (
        f"{CANARA_FAMILY}: official AMC BER/TER as of {day} "
        f"(Direct {plans['Direct']['base_expense_ratio']:.2f}%/"
        f"{plans['Direct']['ter']:.2f}% BER/TER)"
    )


def _hsbc_key(secret):
    # CAMS' public browser bundle hashes these presentation-layer constants and
    # uses the first 32 hex characters as the UTF-8 AES-256 key bytes.
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:32].encode("ascii")


def _hsbc_aes(data, secret, *, decrypt=False):
    openssl = shutil.which("openssl")
    if not openssl:
        raise ValueError("OpenSSL is required to decode the public HSBC TER download")
    command = [
        openssl,
        "enc",
        "-aes-256-cbc",
        "-K",
        _hsbc_key(secret).hex(),
        "-iv",
        _HSBC_IV.hex(),
        "-nosalt",
    ]
    if decrypt:
        command.append("-d")
    result = subprocess.run(
        command,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    if result.returncode:
        raise ValueError("CAMS public HSBC TER transport could not be decoded")
    return result.stdout


def _hsbc_request_payload():
    payload = {
        "flag": "GET_UPD_MB_RESULT",
        "jobday": "hsbc_ter_report.xlsx",
        "browser": "Chrome",
        "device_id": "153.0.0.0",
        "os_id": "10",
        "application": "CAMSONLINE",
        "sub_application": "DIGITALADMIN",
        "deviceid": "desktop",
        "page_name": "/dnlresult/hsbc_ter_report.xlsx",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ciphertext = _hsbc_aes(raw, _HSBC_REQUEST_SECRET)
    return base64.b64encode(ciphertext).decode("ascii").replace("+", "-").replace("/", "_")


def _hsbc_decode_response(raw):
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("CAMS HSBC TER response is unexpectedly large")
    try:
        outer = json.loads(raw)
        if not isinstance(outer, str) or not outer:
            raise ValueError
        ciphertext = base64.b64decode(
            outer.replace("-", "+").replace("_", "/"), validate=True
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError("CAMS HSBC TER response has an invalid encrypted envelope") from exc
    plain = _hsbc_aes(ciphertext, _HSBC_RESPONSE_SECRET, decrypt=True)
    try:
        payload = json.loads(plain.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("CAMS HSBC TER response decrypted to invalid JSON") from exc
    status = payload.get("status")
    details = payload.get("detail")
    if (
        not isinstance(status, dict)
        or bool(status.get("errorflag"))
        or not isinstance(details, list)
        or len(details) != 1
        or not isinstance(details[0], dict)
    ):
        raise ValueError("CAMS HSBC TER service did not return one successful workbook")
    result = details[0].get("RESULT")
    if not isinstance(result, str) or not result:
        raise ValueError("CAMS HSBC TER response did not include workbook bytes")
    try:
        workbook = base64.b64decode(result, validate=True)
    except ValueError as exc:
        raise ValueError("CAMS HSBC TER workbook payload is invalid base64") from exc
    if not workbook.startswith(b"PK") or not 10_000 < len(workbook) <= 12 * 1024 * 1024:
        raise ValueError("CAMS HSBC TER payload is not a plausible XLSX workbook")
    return workbook


def _hsbc_workbook():
    public_url(HSBC_CAMS_API)
    encoded = _hsbc_request_payload()
    headers = {
        "User-Agent": "SmallcapLedger/1.0 (public AMC disclosure collection)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://digital.camsonline.com",
        "Referer": HSBC_TER_LINK,
    }
    try:
        with httpx.Client(timeout=60, headers=headers, follow_redirects=False) as client:
            response = client.post(HSBC_CAMS_API, json={"data": encoded})
            response.raise_for_status()
            raw = response.content
    except httpx.HTTPError as exc:
        raise ValueError("CAMS HSBC TER service is unavailable") from exc
    return _hsbc_decode_response(raw)


def _hsbc_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _hsbc_number(value, label):
    if value is None or str(value).strip() in ("", "-", "NA", "N/A"):
        raise ValueError(f"HSBC TER workbook is missing {label}")
    parsed = number(value)
    if not 0 <= parsed <= 5:
        raise ValueError(f"HSBC TER workbook {label} is outside the accepted range")
    return parsed


def parse_hsbc_workbook(content, today=None):
    """Return HSBC Small Cap's newest explicit BER and Total TER plan pair."""
    today = today or date.today()
    try:
        book = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError("HSBC TER disclosure is not a readable XLSX workbook") from exc
    try:
        if "TER" not in book.sheetnames:
            raise ValueError("HSBC TER workbook no longer contains the TER sheet")
        sheet = book["TER"]
        rows = sheet.iter_rows(values_only=True)
        next(rows, None)
        title = next(rows, None)
        header = next(rows, None)
        if not title or str(title[0] or "").strip() != "Total Expense Ratio (TER) for HSBC Mutual Fund":
            raise ValueError("HSBC TER workbook title changed")
        if not header or tuple(str(x or "").strip() for x in header[:14]) != _HSBC_HEADER:
            raise ValueError("HSBC TER workbook columns changed")

        matches = defaultdict(list)
        for row in rows:
            if len(row) < 14:
                continue
            if str(row[0] or "").strip() != HSBC_SCHEME_CODE:
                continue
            if str(row[1] or "").strip() != HSBC_NSDL_CODE:
                continue
            if str(row[2] or "").strip() != HSBC_FAMILY:
                continue
            day = _hsbc_day(row[3])
            if day is None or day > today:
                continue
            matches[day.isoformat()].append(row)

        if not matches:
            raise ValueError("HSBC TER workbook contains no dated Small Cap rows")
        day = max(matches)
        if len(matches[day]) != 1:
            raise ValueError(f"HSBC TER workbook has duplicate Small Cap rows for {day}")
        row = matches[day][0]

        regular = {
            "base_expense_ratio": _hsbc_number(row[4], "Regular BER"),
            "brokerage": _hsbc_number(row[5], "Regular brokerage"),
            "transaction_cost": _hsbc_number(row[6], "Regular transaction cost"),
            "statutory_levies": _hsbc_number(row[7], "Regular statutory levies"),
            "ter": _hsbc_number(row[8], "Regular Total TER"),
        }
        direct = {
            "base_expense_ratio": _hsbc_number(row[9], "Direct BER"),
            "brokerage": _hsbc_number(row[10], "Direct brokerage"),
            "transaction_cost": _hsbc_number(row[11], "Direct transaction cost"),
            "statutory_levies": _hsbc_number(row[12], "Direct statutory levies"),
            "ter": _hsbc_number(row[13], "Direct Total TER"),
        }
        for plan, values in (("Regular", regular), ("Direct", direct)):
            if values["ter"] + 1e-9 < values["base_expense_ratio"]:
                raise ValueError(f"HSBC {plan} Total TER is below BER on {day}")
            component_total = (
                values["base_expense_ratio"]
                + values["brokerage"]
                + values["transaction_cost"]
                + values["statutory_levies"]
            )
            if abs(component_total - values["ter"]) > 0.02:
                raise ValueError(f"HSBC {plan} TER components do not reconcile on {day}")
        return day, {"Regular": regular, "Direct": direct}
    finally:
        book.close()


def hsbc(progress=lambda _: None, today=None):
    """Collect HSBC Small Cap's detailed TER workbook linked by its AMC factsheet."""
    today = today or date.today()
    if not db.one("SELECT code FROM schemes WHERE family=? LIMIT 1", (HSBC_FAMILY,)):
        return "HSBC Small Cap is not in the active universe"

    progress("HSBC Small Cap expense ratios · AMC-linked detailed TER workbook")
    try:
        workbook = _hsbc_workbook()
        content_hash = db.archive(workbook, _HSBC_XLSX_MIME)
        with db.connect() as connection:
            connection.execute(
                "INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",
                (HSBC_TER_LINK, db.now(), "ok", content_hash),
            )
        day, plans = parse_hsbc_workbook(workbook, today)
        for plan, values in plans.items():
            for metric in (
                "base_expense_ratio",
                "brokerage",
                "transaction_cost",
                "statutory_levies",
                "ter",
            ):
                db.metric(
                    HSBC_FAMILY,
                    plan,
                    metric,
                    day,
                    values[metric],
                    "% p.a. · reported by AMC via AMC-linked CAMS workbook",
                    HSBC_TER_LINK,
                    content_hash,
                )
    except Exception as exc:
        with db.connect() as connection:
            connection.execute(
                "INSERT INTO fetches(url,fetched_at,status,detail) VALUES(?,?,?,?)",
                (HSBC_TER_LINK, db.now(), "error", str(exc)[:400]),
            )
        raise

    return (
        f"{HSBC_FAMILY}: official detailed BER/TER as of {day} "
        f"(Direct {plans['Direct']['base_expense_ratio']:.2f}%/"
        f"{plans['Direct']['ter']:.2f}% BER/TER)"
    )



def _icici_headers():
    return {
        "User-Agent": "SmallcapLedger/1.0 (public AMC disclosure collection)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.icicipruamc.com",
        "Referer": ICICI_TER_PAGE,
        "env": "api",
        "baggage": "",
        "requestAPIId": str(uuid.uuid4()),
    }


def _icici_api(url, *, body=None):
    """Call the same unauthenticated financial-disclosure API as ICICI's SPA."""
    public_url(url)
    try:
        with httpx.Client(
            timeout=httpx.Timeout(60, connect=15),
            headers=_icici_headers(),
            follow_redirects=False,
        ) as client:
            response = client.post(url, json=body) if body is not None else client.get(url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("ICICI financial disclosure API is unavailable or invalid") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("success"), dict):
        raise ValueError("ICICI financial disclosure API response changed format")
    if payload.get("error"):
        raise ValueError("ICICI financial disclosure API returned an error")
    return payload["success"].get("data")


def _icici_financial_year(today):
    start = today.year if today.month >= 4 else today.year - 1
    return f"{start}-{start + 1}"


def _icici_category_ids(categories, today=None):
    today = today or date.today()
    if not isinstance(categories, list):
        raise ValueError("ICICI financial categories response is not a list")
    top = [
        row for row in categories
        if isinstance(row, dict)
        and row.get("isEnabled") is True
        and str((row.get("title") or {}).get("code", "")).strip() == ICICI_TER_CATEGORY_CODE
        and str((row.get("title") or {}).get("text", "")).strip() == ICICI_TER_TITLE
        and str(row.get("internalName", "")).strip() == "total-expense-ratio"
    ]
    if len(top) != 1:
        raise ValueError("ICICI Total Expense Ratio category is not uniquely identified")
    parent = top[0]
    sub = [
        row for row in (parent.get("subCategory") or [])
        if isinstance(row, dict)
        and row.get("isEnabled") is True
        and str((row.get("title") or {}).get("code", "")).strip() == ICICI_TER_SUBCATEGORY_CODE
        and str((row.get("title") or {}).get("text", "")).strip() == ICICI_TER_TITLE
        and str(row.get("internalName", "")).strip() == "Total Expense Ratio"
    ]
    if len(sub) != 1:
        raise ValueError("ICICI Total Expense Ratio subcategory is not uniquely identified")
    child = sub[0]
    filters = {
        str((item.get("key") or {}).get("code", "")).strip():
        {str(value.get("code", "")).strip() for value in (item.get("value") or []) if isinstance(value, dict)}
        for item in (child.get("filter") or [])
        if isinstance(item, dict)
    }
    if ICICI_TER_SHOW not in filters.get("SHOW", set()):
        raise ValueError("ICICI TER Details filter is no longer published")
    financial_year = _icici_financial_year(today)
    if financial_year not in filters.get("FINANCIAL_YEAR", set()):
        raise ValueError("ICICI current financial year is absent from TER filters")
    return str(parent.get("id")), str(child.get("id")), financial_year


def _icici_month(value):
    token = str(value or "").strip()
    for fmt in ("%B%Y", "%b%Y"):
        try:
            parsed = datetime.strptime(token, fmt).date()
            return parsed.year, parsed.month
        except ValueError:
            pass
    return None


def _icici_select_file(files, parent_id, child_id, financial_year, today=None):
    today = today or date.today()
    if not isinstance(files, list):
        raise ValueError("ICICI TER file response is not a list")
    found = defaultdict(list)
    for row in files:
        if not isinstance(row, dict):
            continue
        title = row.get("title") or {}
        title_text = str(title.get("text", "") if isinstance(title, dict) else "").strip()
        match = _ICICI_TITLE.fullmatch(title_text)
        path = str(row.get("url", "")).strip()
        file_name = path.rsplit("/", 1)[-1]
        file_match = _ICICI_FILE.fullmatch(file_name)
        if not match or not file_match:
            continue
        title_month = _icici_month(match.group(1) + match.group(2))
        file_month = _icici_month(file_match.group(1) + file_match.group(2))
        if title_month is None or file_month is None or title_month != file_month:
            continue
        year, month = title_month
        if (year, month) > (today.year, today.month):
            continue
        if (
            row.get("isEnabled") is not True
            or str(row.get("category", "")).strip() != ICICI_TER_CATEGORY_CODE
            or str(row.get("categoryName", "")).strip() != ICICI_TER_TITLE
            or str(row.get("level1Id", "")).strip() != parent_id
            or str(row.get("level2Id", "")).strip() != child_id
            or ICICI_TER_SHOW not in (row.get("SHOW") or [])
            or financial_year not in (row.get("FINANCIAL_YEAR") or [])
            or not path.startswith("/financials-disclosures-files/Files/Total Expense Ratio/")
            or not path.lower().endswith(".xlsx")
        ):
            continue
        found[(year, month)].append(row)
    if not found:
        raise ValueError("ICICI TER API returned no current TER Details workbook")
    key = max(found)
    if len(found[key]) != 1:
        raise ValueError("ICICI TER API returned duplicate workbooks for the latest month")
    row = found[key][0]
    source = ICICI_FILE_BASE + quote(str(row["url"]), safe="/")
    public_url(source)
    return source


def _icici_inline_strings(content):
    """Read rows from ICICI's XLSX sheet XML.

    The current workbook has valid inline-string rows but malformed worksheet
    dimension metadata, so ordinary openpyxl iteration exposes only row 1.
    Parsing the standard OOXML sheet cells retains the source exactly.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("ICICI TER disclosure is not a valid XLSX package") from exc
    try:
        sheets = [
            name for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        ]
        if len(sheets) != 1:
            raise ValueError("ICICI TER workbook must contain exactly one worksheet")
        raw = archive.read(sheets[0])
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError("ICICI TER worksheet XML is unexpectedly large")
        root = ET.fromstring(raw)
    except (KeyError, ET.ParseError) as exc:
        raise ValueError("ICICI TER worksheet XML is invalid") from exc
    finally:
        archive.close()
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows = []
    for row in root.findall(".//x:sheetData/x:row", ns):
        values = {}
        for cell in row.findall("x:c", ns):
            ref = str(cell.attrib.get("r", ""))
            column = re.match(r"[A-Z]+", ref)
            if not column:
                continue
            parts = [node.text or "" for node in cell.findall(".//x:t", ns)]
            if parts:
                value = "".join(parts)
            else:
                node = cell.find("x:v", ns)
                value = "" if node is None else (node.text or "")
            values[column.group(0)] = value
        rows.append(values)
    return rows


def _icici_percent(value, label):
    raw = str(value or "").strip()
    if not raw or raw.upper() in ("NA", "N/A", "-"):
        raise ValueError(f"ICICI TER workbook is missing {label}")
    parsed = number(raw)
    if not 0 <= parsed <= 5:
        raise ValueError(f"ICICI TER workbook {label} is outside the accepted range")
    return parsed


def parse_icici_workbook(content, today=None):
    """Return the newest exact Small Cap BER and published Total TER pair."""
    today = today or date.today()
    rows = _icici_inline_strings(content)
    if len(rows) < 4:
        raise ValueError("ICICI TER workbook contains no usable rows")
    if rows[0].get("A", "").strip() != "Total Expense Ratio (TER) for Mutual Fund Schemes":
        raise ValueError("ICICI TER workbook title changed")
    if rows[1].get("C", "").strip() != "Regular Plan" or rows[1].get("H", "").strip() != "Direct Plan":
        raise ValueError("ICICI TER plan headings changed")
    for column, expected in _ICICI_HEADER.items():
        if rows[2].get(column, "").strip() != expected:
            raise ValueError(f"ICICI TER column {column} changed")

    matches = defaultdict(list)
    for row in rows[3:]:
        if row.get("A", "").strip() != ICICI_FAMILY:
            continue
        try:
            day = datetime.strptime(row.get("B", "").strip(), "%d/%m/%Y").date()
        except ValueError:
            continue
        if day <= today:
            matches[day.isoformat()].append(row)
    if not matches:
        raise ValueError("ICICI TER workbook contains no dated Small Cap rows")
    day = max(matches)
    if len(matches[day]) != 1:
        raise ValueError(f"ICICI TER workbook has duplicate Small Cap rows for {day}")
    row = matches[day][0]

    regular = {
        "base_expense_ratio": _icici_percent(row.get("C"), "Regular BER"),
        "brokerage": _icici_percent(row.get("D"), "Regular brokerage"),
        "transaction_cost": _icici_percent(row.get("E"), "Regular transaction cost"),
        "statutory_levies": _icici_percent(row.get("F"), "Regular statutory levies"),
        "ter": _icici_percent(row.get("G"), "Regular Total TER"),
    }
    direct = {
        "base_expense_ratio": _icici_percent(row.get("H"), "Direct BER"),
        "brokerage": _icici_percent(row.get("I"), "Direct brokerage"),
        "transaction_cost": _icici_percent(row.get("J"), "Direct transaction cost"),
        "statutory_levies": _icici_percent(row.get("K"), "Direct statutory levies"),
        "ter": _icici_percent(row.get("L"), "Direct Total TER"),
    }
    for plan, values in (("Regular", regular), ("Direct", direct)):
        if values["ter"] + 1e-9 < values["base_expense_ratio"]:
            raise ValueError(f"ICICI {plan} Total TER is below BER on {day}")
        component_total = (
            values["base_expense_ratio"]
            + values["brokerage"]
            + values["transaction_cost"]
            + values["statutory_levies"]
        )
        if abs(component_total - values["ter"]) > 0.02:
            raise ValueError(f"ICICI {plan} TER components do not reconcile on {day}")
    return day, {"Regular": regular, "Direct": direct}


def _icici_disclosure(today=None):
    today = today or date.today()
    categories = _icici_api(ICICI_CATEGORIES_API + "?userType=Investor")
    parent_id, child_id, financial_year = _icici_category_ids(categories, today)
    payload = {
        "categoryId": child_id,
        "userType": "Investor",
        "fileType": "All",
        "page": "1",
        "size": "20",
        "filter": [
            {"SHOW": [ICICI_TER_SHOW]},
            {"FINANCIAL_YEAR": [financial_year]},
        ],
        "search": "",
    }
    data = _icici_api(ICICI_FILES_API, body=payload)
    if not isinstance(data, dict):
        raise ValueError("ICICI TER file-list response changed format")
    source = _icici_select_file(
        data.get("files"),
        parent_id,
        child_id,
        financial_year,
        today,
    )
    workbook, content_hash, _ = fetch(source, max_bytes=5 * 1024 * 1024)
    if not workbook.startswith(b"PK"):
        raise ValueError("ICICI TER file is not an XLSX workbook")
    return source, workbook, content_hash


def icici(progress=lambda _: None, today=None):
    """Collect ICICI Prudential Small Cap's explicit BER/Total TER workbook."""
    today = today or date.today()
    if not db.one("SELECT code FROM schemes WHERE family=? LIMIT 1", (ICICI_FAMILY,)):
        return "ICICI Prudential Small Cap is not in the active universe"
    progress("ICICI Prudential Small Cap expense ratios · official TER Details workbook")
    source, workbook, content_hash = _icici_disclosure(today)
    day, plans = parse_icici_workbook(workbook, today)
    for plan, values in plans.items():
        for metric in (
            "base_expense_ratio",
            "brokerage",
            "transaction_cost",
            "statutory_levies",
            "ter",
        ):
            db.metric(
                ICICI_FAMILY,
                plan,
                metric,
                day,
                values[metric],
                "% p.a. · reported by AMC",
                source,
                content_hash,
            )
    return (
        f"{ICICI_FAMILY}: official BER/TER as of {day} "
        f"(Direct {plans['Direct']['base_expense_ratio']:.2f}%/"
        f"{plans['Direct']['ter']:.2f}% BER/TER)"
    )


def update(progress=lambda _: None):
    results = []
    errors = []
    for collector in (canara, hsbc, icici):
        try:
            results.append(collector(progress))
        except Exception as exc:
            errors.append(f"{collector.__name__}: {str(exc)[:220]}")
    if errors:
        raise ValueError("; ".join(results + errors))
    return "; ".join(results)
