"""Bounded read-only Samco/AMFI contract diagnostic. Never imports the database."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


def main():
    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "mode":"read_only", "attempts":[]}
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"}) as client:
        def get(url):
            with client.stream("GET", url) as response:
                response.raise_for_status()
                body = bytearray()
                for part in response.iter_bytes():
                    body.extend(part)
                    if len(body) > 10 * 1024 * 1024:
                        raise ValueError("response exceeds bound")
                return bytes(body), str(response.url)
        def record(url, kind):
            body, final = get(url)
            item = {"kind":kind, "source":url, "resolved_url":final, "sha256":hashlib.sha256(body).hexdigest(), "bytes":len(body)}
            result["attempts"].append(item)
            return body, item
        for path in ("docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json",):
            audit = json.loads(Path(path).read_text())
            result["retained_samco"] = [r for r in audit.get("families",[]) if r.get("family")=="Samco Mid Cap Fund"]
            result["retained_amfi_checks"] = [r for r in audit.get("source_checks",[]) if r.get("amc")=="Samco Mutual Fund"]
        base="https://www.amfiindia.com"
        try:
            raw,item=record(base+"/api/populate-mf","amfi_selector")
            obj=json.loads(raw); rows=obj.get("data",[]) if isinstance(obj,dict) else obj
            matched=[r for r in rows if re.sub(r'[^a-z0-9]','',str(r.get('mfName','')).lower())=='samcomutualfund']
            item["samco_selectors"]=matched
            if len(matched)==1:
                for cat in ("17","-1"):
                    url=base+"/api/populate-te-rdata-revised?"+urlencode({"MF_ID":matched[0]["mfId"],"Month":"09-2026","strCat":cat,"strType":"1","page":1,"pageSize":1000})
                    raw,item=record(url,"amfi_samco")
                    obj=json.loads(raw);rows=obj.get('data',[]) if isinstance(obj,dict) else obj
                    item['meta']=obj.get('meta') if isinstance(obj,dict) else None
                    item['row_count']=len(rows)
                    item['midcap_rows']=[r for r in rows if re.search(r'mid\s*cap',str(r.get('Scheme_Name','')),re.I)][:8]
                    item['scheme_names']=sorted(set(str(r.get('Scheme_Name')) for r in rows))[:30]
        except Exception as exc:
            result['attempts'].append({'kind':'amfi_error','error':str(exc)[:300]})
        page="https://www.samcomf.com/total-expense-ratio"
        try:
            raw,item=record(page,'samco_page'); soup=BeautifulSoup(raw,'html.parser')
            item['tables']=[t.get_text(' ',strip=True)[:4000] for t in soup.select('table')][:2]
            scripts=[urljoin(page,s['src']) for s in soup.select('script[src]')]
            item['scripts']=scripts
            item['links']=[{'href':urljoin(page,a['href']),'label':a.get_text(' ',strip=True)} for a in soup.select('a[href]') if re.search('expense|ter|export',a['href'],re.I)][:20]
            inline=' '.join(s.get_text() for s in soup.select('script:not([src])'))
            item['inline_hints']=[inline[max(0,m.start()-100):m.end()+200] for m in list(re.finditer('expense|terData|terList|ter-data',inline,re.I))[:8]]
            selected=[url for url in scripts if urlsplit(url).hostname=='www.samcomf.com']
            for url in selected[:8]:
                try:
                    raw,js=record(url,'samco_js');text=raw.decode('utf-8','replace')
                    pattern=r'total.expense|expense.ratio|terData|terList|ter-data|ter_history|terhistory'
                    js['hints']=[text[max(0,m.start()-150):m.end()+350] for m in list(re.finditer(pattern,text,re.I))[:24]]
                except Exception as exc:
                    result['attempts'].append({'kind':'samco_js_error','source':url,'error':str(exc)[:200]})
        except Exception as exc:
            result['attempts'].append({'kind':'samco_error','error':str(exc)[:300]})
    print('SAMCO_DIAGNOSTIC_BEGIN')
    print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
    print('SAMCO_DIAGNOSTIC_END')

if __name__=='__main__': main()
