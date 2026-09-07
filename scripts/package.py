"""Create the portable GitHub source package with a verified historical seed."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import db
from tracker.app import funds,status
from scripts.github_state import seed,digest,verify_data


def coverage():
    index=funds()['funds'];report=status();groups={}
    for f in index:groups.setdefault(f['family'],[]).append(f)
    families=[]
    for family,plans in sorted(groups.items()):
        aum=next((f['metrics']['aum'] for f in plans if f['metrics'].get('aum')),None)
        def fee(plan):
            f=next((x for x in plans if x['plan']==plan),None)
            if not f:return None
            m=f['metrics'];return m.get('ter') or m.get('ter_observed') or m.get('base_expense_ratio')
        families.append({'family':family,'nav_series':len(plans),'aum':aum,'direct_fee':fee('Direct'),'regular_fee':fee('Regular'),
            'nav_history':db.one('SELECT MIN(n.date) first,MAX(n.date) last,COUNT(*) points FROM nav n JOIN schemes s ON s.code=n.code WHERE s.family=?',(family,)),
            'aum_dates':db.one("SELECT COUNT(DISTINCT as_of) n FROM metrics WHERE family=? AND metric='aum'",(family,))['n'],
            'fee_dates':db.one("SELECT COUNT(DISTINCT as_of) n FROM metrics WHERE family=? AND metric IN ('ter','ter_observed','base_expense_ratio')",(family,))['n'],
            'portfolio_snapshots':db.one('SELECT COUNT(*) n FROM portfolios WHERE family=?',(family,))['n'],
            'publication_versions':db.one("SELECT COUNT(*) n FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE d.family=? AND d.kind!='news'",(family,))['n']})
    report['counts']['aum_funds']=sum(f['aum'] is not None for f in families)
    report['counts']['fee_funds']=sum(bool(f['direct_fee'] or f['regular_fee']) for f in families)
    report['counts']['portfolio_funds']=db.one('SELECT COUNT(DISTINCT family) n FROM portfolios')['n']
    report['families']=families
    report['limitations']=[
        'AUM, expenses, full portfolios and archived communications are incomplete across the universe.',
        'Current AMFI small-cap category; the historical closed/merged universe is not reconstructed.',
        'Older NAV comes from MFapi; it is not all independently verified against AMFI.',
        'Nifty Smallcap 250 TRI is a category comparator where the stated benchmark is unavailable or unverified.',
        'BSE TRI and historical benchmark changes are not included.',
        'IDCW total returns require complete distribution data; bonus options require unit adjustments.',
        'Automated portfolios are partial; security departures do not prove sales.',
        'Archived versions start when accessible documents are collected; unavailable older versions remain gaps.',
        'A daily schedule requests midnight IST execution; GitHub may delay or skip runs.',
        'GitHub deployment, Windows desktop launch and browser visual testing have not been performed.',
    ]
    (ROOT/'COVERAGE-AS-OF.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    c=report['counts'];latest=max(f['nav_history']['last'] or '' for f in families)
    md=['# Included data coverage','',f"Prepared: {report['server_time']}",'',
        f"**{c['funds']} funds, {c['plans']} NAV series, {c['nav_points']:,} NAV observations. Latest included NAV: {latest}.**",'',
        f"AUM: **{c['aum_funds']} / {c['funds']} funds**. Expense figures: **{c['fee_funds']} / {c['funds']} funds**. Parsed portfolios: **{c['portfolio_funds']} / {c['funds']} funds**.",'',
        f"The archive includes {c['benchmark_points']:,} actual TRI observations. Third-party news has been removed; Fund communications contains AMC publications and official source pages.",'',
        '## Per-fund figures','',
        'Values retain their reporting dates. AUM is fund-wide in ₹ crore; do not add Direct and Regular rows together. TER and BER are distinct. A gap means no verified numeric record has been collected, not a zero expense or fund size.','',
        '| Fund | NAV series | AUM · ₹ Cr / date | Direct expense / date | Regular expense / date | Portfolio snapshots |',
        '| --- | ---: | --- | --- | --- | ---: |']
    def value(m,is_aum=False):
        if not m:return 'Gap'
        label='₹ '+format(float(m['value']),',.2f') if is_aum else str(m['value'])+'% '+('BER' if m['metric']=='base_expense_ratio' else 'TER')
        return label+' · '+m['as_of']
    for f in families:md.append(f"| {f['family']} | {f['nav_series']} | {value(f['aum'],True)} | {value(f['direct_fee'])} | {value(f['regular_fee'])} | {f['portfolio_snapshots']} |")
    md+=['','## Sources and limits','',
        'Source URLs and per-fund dates are included in COVERAGE-AS-OF.json and on every fund page. Portfolio counts include partial views and different versions of one reporting date. Source-page archival is not proof that all numeric fields were parsed.','']
    md+=['- '+x for x in report['limitations']]
    md+=['','Read GITHUB-SETUP.md to enable the online site and daily workflow. No GitHub deployment is active merely because this package was created.','']
    (ROOT/'COVERAGE-AS-OF.md').write_text('\n'.join(md))
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    if db.one("SELECT id FROM jobs WHERE status='running' LIMIT 1"):raise RuntimeError('Finish updates before packaging')
    verify_data(db.DATA);report=coverage();seed(ROOT/'bootstrap')
    excluded={'.venv','__pycache__','.git','.openai','node_modules','data','site'}
    sources=[f for f in ROOT.rglob('*') if f.is_file() and not any(x in excluded for x in f.relative_to(ROOT).parts) and f.suffix not in ('.pyc','.zip')]
    if any(f.stat().st_size>=25*1024*1024 for f in sources):raise RuntimeError('A source-package file exceeds the browser upload limit')
    output=a.output.resolve();output.parent.mkdir(parents=True,exist_ok=True);manifest=[]
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(sources):
            name='Smallcap-Ledger/'+f.relative_to(ROOT).as_posix();z.write(f,name)
            manifest.append({'path':name,'bytes':f.stat().st_size,'sha256':digest(f)})
        z.writestr('Smallcap-Ledger/PACKAGE-MANIFEST.json',json.dumps({'prepared_at':report['server_time'],'files':manifest},indent=2)+'\n')
    with zipfile.ZipFile(output) as z:
        if z.testzip():raise RuntimeError('Package ZIP verification failed')
    print(json.dumps({'output':str(output),'bytes':output.stat().st_size,'files':len(manifest)+1,'funds':report['counts']['funds'],'plans':report['counts']['plans'],'aum_funds':report['counts']['aum_funds'],'fee_funds':report['counts']['fee_funds']},indent=2))


if __name__=='__main__':main()
