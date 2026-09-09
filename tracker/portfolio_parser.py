"""Complete monthly portfolios validated against reported net assets.

No balancing cash is invented. Unknown rows or non-reconciling totals leave the
existing ISIN-only extractor in charge of a visibly partial snapshot.
"""
import math
import re
from datetime import date
from .providers import number


def parse_sheet(rows,formats,family):
    from .disclosures import same_fund_title,report_date
    header=None;hi=None
    for i,row in enumerate(rows[:35]):
        cells=[str(v or '').lower() for v in row]
        if any('isin' in v for v in cells) and any('%' in v and re.search(r'nav|aum|net.*asset',v) for v in cells):header=cells;hi=i;break
    if header is None:return None
    def owned(value):
        text=str(value)
        if family=='The Wealth Company Small Cap Fund':text=re.sub(r'^WCSC\s*-\s*','',text,flags=re.I)
        return same_fund_title(text,family)
    if not any(owned(v) for row in rows[:hi] for v in row if v):return None
    prefix=' '.join(str(v) for row in rows[:hi] for v in row if v is not None)
    day=report_date(prefix)
    if not day or day>date.today().isoformat():return None
    def col(predicate):return next((i for i,v in enumerate(header) if predicate(v)),None)
    ic=col(lambda v:'isin' in v);nc=col(lambda v:'name' in v or 'instrument' in v or 'issuer' in v)
    wc=col(lambda v:'%' in v and re.search(r'nav|aum|net.*asset',v))
    vc=col(lambda v:re.search(r'market|mkt|fair',v) and re.search(r'value',v))
    sc=col(lambda v:'industry' in v or 'rating' in v or 'sector' in v);qc=col(lambda v:'quantity' in v)
    if None in (nc,wc,vc):return None
    divisor=100 if re.search(r'la(?:kh|c)s?\b',header[vc]) else 1 if re.search(r'crores?\b',header[vc]) else None
    if divisor is None:return None
    def numeric(value):
        v=number(re.sub(r'^[$#*^]\s*(?=0(?:\.0+)?\s*%?$)','',str(value)))
        if not math.isfinite(v):raise ValueError('Non-finite portfolio figure')
        return v
    def weight(ri,row):
        value=numeric(row[wc]);fmt=re.sub(r'"[^"\n]*"|\\.','',formats[ri][wc] or '')
        return value*100 if isinstance(row[wc],(int,float)) and '%' in fmt else value
    def empty(value):return str(value or '').strip().lower() in ('','-','nil','0','0.0','0.00')
    positions=[];values=[];grand=None;unknown=[];asset='Equity'
    for ri,row in enumerate(rows[hi+1:],hi+1):
        if max(ic,nc,wc,vc)>=len(row):continue
        name=str(row[nc] or '').strip();label=name or ' '.join(str(x or '') for x in row[:max(nc,ic)+1]).strip()
        if re.fullmatch(r'grand\s+total(?:\s*\(aum\))?|total\s+net\s+assets?',label,re.I):
            try:grand=(numeric(row[vc]),weight(ri,row))
            except ValueError:pass
            break
        isin=str(row[ic] or '').strip();valid_isin=bool(re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}',isin))
        named_equity=not isin and asset=='Equity' and re.search(r'\b(?:Ltd\.?|Limited)\s*[*^@#]?$',name,re.I) and qc is not None and not empty(row[qc])
        named_repo=family=='Motilal Oswal Small Cap Fund' and asset=='Money market' and isin=='CBLO' and re.fullmatch(r'TRP_\d{6}',name)
        if not valid_isin and not named_equity and not named_repo:
            if re.search(r'\b(?:sub\s*-?\s*total|total)\b',label,re.I):continue
            leaf=bool(re.fullmatch(r'(?:TREPS(?:\s*-\s*Tri-party Repo)?|Tri[ -]?party Repo|Reverse Repo(?: Investments)?|Net Receivables?\s*/?\s*\(?Payables?\)?|Net Current Assets|Cash(?: and Other Net Current Assets|\s*&\s*Cash Equivalents| Margin\s*-\s*CCIL)?|Margin Money(?:.*)?)\s*[*^#]?',label,re.I))
            if not leaf:
                if re.search(r'\bequity\b',label,re.I):asset='Equity'
                elif re.search(r'treasury|government|debt',label,re.I):asset='Debt'
                elif re.search(r'money market|repo|treps',label,re.I):asset='Money market'
                elif re.search(r'fund unit|exchange traded|mutual fund',label,re.I):asset='Fund units'
                elif re.search(r'derivative',label,re.I):asset='Derivative'
                if not empty(row[wc]) or not empty(row[vc]):unknown.append(label)
                continue
            if empty(row[wc]) and empty(row[vc]):continue
        try:w=weight(ri,row);v=numeric(row[vc])
        except ValueError:unknown.append(label);continue
        if not -100<=w<=100:unknown.append(label);continue
        kind=asset if valid_isin or named_equity or named_repo else ('Money market' if re.search(r'repo|treps',label,re.I) else 'Cash and net current assets')
        positions.append({'name':name or label,'isin':isin if valid_isin else None,'sector':str(row[sc] or '') if sc is not None and valid_isin else None,'weight':w,'asset_type':kind});values.append(v)
    aum=None
    if grand and 0<grand[0]/divisor<10_000_000 and abs(grand[1]-100)<.01:aum=round(grand[0]/divisor,6)
    complete=bool(aum and positions and not unknown)
    if grand:
        complete=complete and abs(sum(values)-grand[0])<=max(.05,.011*len(values))
        complete=complete and abs(sum(x['weight'] for x in positions)-grand[1])<=max(.05,.0051*len(positions))
    complete=complete and len({(p['isin'],p['name'],p['asset_type']) for p in positions})==len(positions)
    return {'day':day,'aum':aum,'complete':bool(complete),'positions':positions,'unknown_rows':unknown}
