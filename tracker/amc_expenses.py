"""Official AMC expense disclosures that are not currently present in AMFI's Small Cap feed."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import json
from urllib.parse import urlencode

from . import db
from .providers import fetch, number

CANARA_FAMILY = "Canara Robeco Small Cap Fund"
CANARA_SCHEME_CODE = "SC"
CANARA_PAGE = "https://www.canararobeco.com/expense-ratio"
CANARA_API = "https://www.canararobeco.com/wp-json/ter/v1/records"
CANARA_PLANS = {"Regular Plan": "Regular", "Direct Plan": "Direct"}


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


def update(progress=lambda _: None):
    return canara(progress)
