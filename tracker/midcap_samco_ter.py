"""Recover exact Samco Mid Cap TER from AMFI's bounded AMC-scoped feed.

The category-filtered feed can omit this scheme while the all-category feed
reports it as 'Equity Schemes - Mid Cap Fund'. This is not an industry sweep.
Both published plan totals and the verified NSDL identity must be present.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from urllib.parse import urlencode

FAMILY = 'Samco Mid Cap Fund'
AMC = 'Samco Mutual Fund'
NSDL = 'SAMC/O/E/MIF/25/10/0013'
ENDPOINT = 'https://www.amfiindia.com/api/populate-te-rdata-revised'
MAX_PAGES = 5
COMPONENTS = ('BER', 'BrokerageCost', 'TransactionCost', 'StatutoryLevies')


class SamcoTERError(ValueError):
    """Incomplete or conflicting evidence, with the observed page checks."""
    def __init__(self, message, checks=None):
        super().__init__(message)
        self.checks = deepcopy(checks or [])


def _norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').casefold())


def _number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('missing or boolean TER component')
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError('invalid TER component') from exc
    if not result.is_finite() or not Decimal(0) <= result <= Decimal(10):
        raise ValueError('nonfinite or out-of-range TER component')
    return result


def _validate_target(row, today):
    if str(row.get('NSDLSchemeCode') or '').strip().upper() != NSDL:
        raise ValueError('Samco Mid Cap NSDL identity mismatch')
    if not re.fullmatch(r'Equity Schemes?\s*-\s*Mid\s*Cap Fund', str(row.get('SchemeCat_Desc') or '').strip(), re.I):
        raise ValueError('Samco Mid Cap category mismatch')
    if str(row.get('SchemeType_Desc') or '').strip().casefold() != 'open ended':
        raise ValueError('Samco scheme is not open ended')
    raw_date = row.get('TER_Date')
    if not isinstance(raw_date, str) or not re.match(r'^\d{4}-\d{2}-\d{2}(?:T|$)', raw_date):
        raise ValueError('invalid Samco TER date')
    day = datetime.fromisoformat(raw_date.replace('Z', '+00:00')).date()
    if day > today or (day.year, day.month) != (today.year, today.month):
        raise ValueError('Samco TER date is future or outside the requested month')
    signature = []
    for prefix in ('D', 'R'):
        components = [_number(row.get(prefix + '_' + name)) for name in COMPONENTS]
        total = _number(row.get(prefix + '_TER'))
        if total < components[0] or abs(sum(components) - total) > Decimal('0.02'):
            raise ValueError('published Samco BER/components do not reconcile to TER')
        signature.extend([*components, total])
    return day.isoformat(), tuple(signature)


def _reject_constant(value):
    raise ValueError('nonfinite JSON constant: ' + value)


def fetch_samco_ter(selector, *, fetch_fn, today=None):
    """Return validated original rows and page provenance, or fail atomically.

    All reported pages must be consumed, even if page 1 contains a matching
    older daily observation. On any later-page failure no partial rows escape.
    """
    today = today or date.today()
    checks, matched = [], {}
    try:
        if not isinstance(selector, dict) or selector.get('name') != AMC:
            raise ValueError('not the exact Samco AMC selector')
        mfid = str(selector.get('id') or '')
        if not re.fullmatch(r'[1-9]\d*', mfid):
            raise ValueError('invalid Samco AMC selector ID')
        month = today.strftime('%m-%Y')
        page, expected_meta, total_read = 1, None, 0
        while True:
            request = {'MF_ID':mfid, 'Month':month, 'strCat':'-1', 'strType':'1', 'page':page, 'pageSize':1000}
            url = ENDPOINT + '?' + urlencode(request)
            body, _, _ = fetch_fn(url, archive=False, max_bytes=2*1024*1024)
            digest = hashlib.sha256(body).hexdigest()
            observed = datetime.now(timezone.utc).isoformat()
            check = {'kind':'ter_samco_amc_page', 'source':url, 'sha256':digest,
                     'observed_at':observed, 'request':request, 'amc':AMC, 'page':page}
            checks.append(check)
            payload = json.loads(body, parse_constant=_reject_constant)
            if not isinstance(payload, dict) or not isinstance(payload.get('data'), list) or not isinstance(payload.get('meta'), dict):
                raise ValueError('AMFI TER response lacks data or pagination metadata')
            records, meta = payload['data'], payload['meta']
            if any(type(meta.get(key)) is not int for key in ('page','pageSize','total','pageCount')):
                raise ValueError('AMFI TER pagination has non-integer fields')
            size, total, pages = meta['pageSize'], meta['total'], meta['pageCount']
            if meta['page'] != page or not 0 < size <= 1000 or total < 0 or not 0 <= pages <= MAX_PAGES:
                raise ValueError('AMFI TER pagination exceeds bounds or returns wrong page')
            if pages != (total + size - 1)//size:
                raise ValueError('AMFI TER pagination totals disagree')
            contract = (size,total,pages)
            if expected_meta is not None and contract != expected_meta:
                raise ValueError('AMFI TER pagination changed during collection')
            expected_meta = contract
            if len(records) != min(size, max(0,total-(page-1)*size)):
                raise ValueError('AMFI TER page is truncated or empty before completion')
            check.update(rows=len(records), pagination=deepcopy(meta))
            for number, row in enumerate(records, 1):
                if not isinstance(row, dict):
                    raise ValueError('AMFI TER record is not an object')
                if isinstance(row.get('MF_ID'),bool) or str(row.get('MF_ID')) != mfid or row.get('Month') != month:
                    raise ValueError('AMFI returned a different AMC or reporting month')
                if _norm(row.get('Scheme_Name')) != _norm(FAMILY):
                    continue
                day, signature = _validate_target(row, today)
                if day in matched and matched[day][0] != signature:
                    raise ValueError('conflicting duplicate Samco TER observations')
                if day not in matched:
                    evidence = deepcopy(row)
                    evidence['_amfi_source_evidence'] = {
                        'source':url, 'source_sha256':digest, 'source_observed_at':observed,
                        'source_row':number, 'published_row':deepcopy(row),
                        'identity':{'scheme_name':row['Scheme_Name'], 'amc':AMC,
                                    'amfi_mf_id':mfid, 'nsdl_scheme_code':NSDL},
                    }
                    matched[day] = (signature,evidence)
            total_read += len(records)
            if page >= pages:
                break
            page += 1
        checks.append({'kind':'ter_samco_fallback_summary', 'amc':AMC, 'month':month,
                       'complete':True, 'total_rows':total_read, 'pages_checked':page,
                       'matched_families':[FAMILY] if matched else [],
                       'exact_daily_observations':len(matched),
                       'latest_reporting_date':max(matched) if matched else None})
        return [matched[day][1] for day in sorted(matched)], checks
    except Exception as exc:
        raise SamcoTERError(str(exc) or type(exc).__name__, checks) from exc
