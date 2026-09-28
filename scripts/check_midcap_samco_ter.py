"""Read-only real-source preflight for Samco TER; never promote audit evidence."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db, providers
from tracker.midcap_samco_ter import AMC,FAMILY,NSDL,fetch_samco_ter
from tracker.midcap_source_coverage import _match_ter
from tracker.midcap_ter_readiness import reconcile


def main():
    with patch.object(db,'connect',side_effect=AssertionError('Preflight cannot access database')), \
         patch.object(db,'archive',side_effect=AssertionError('Preflight cannot archive sources')):
        selector_url='https://www.amfiindia.com/api/populate-mf'
        raw,_,_=providers.fetch(selector_url,archive=False,max_bytes=1024*1024)
        payload=json.loads(raw)
        records=payload.get('data') if isinstance(payload,dict) else payload
        if not isinstance(records,list):
            raise ValueError('Unexpected official AMC selector shape')
        matches=[r for r in records if isinstance(r,dict) and r.get('mfName')==AMC]
        if len(matches)!=1:
            raise ValueError('No unique exact Samco selector')
        selector={'name':matches[0]['mfName'],'id':str(matches[0]['mfId'])}
        rows,checks=fetch_samco_ter(selector,fetch_fn=providers.fetch)
        matched,_=_match_ter(rows,[{'family':FAMILY,'amc':AMC}])
        if FAMILY not in matched:
            raise ValueError('No validated current-month Samco plan pair')
        evidence=matched[FAMILY]
        if not evidence.get('direct') or not evidence.get('regular'):
            raise ValueError('Samco TER evidence is not a complete plan pair')
        result=reconcile({'families':[{'family':FAMILY,'amc':AMC,
            'direct_ter_available':True,'ter':evidence}]},{'results':[]})
        accepted=result['families'][0]
        if accepted['identity']['nsdl_scheme_code']!=NSDL or not accepted.get('source_sha256'):
            raise ValueError('Reconciled source identity/provenance missing')
        print(json.dumps({'mode':'read_only_source_preflight','production_writes':0,
            'public_export_enabled':False,'selector_source':selector_url,
            'selector_sha256':hashlib.sha256(raw).hexdigest(),
            'result':accepted,'source_checks':checks},indent=2,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
