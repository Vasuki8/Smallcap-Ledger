"""One-time first-party AMC historical NAV row probe. Read-only."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlencode,urlparse
import httpx
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tracker import providers

ABSL_PAGE="https://mutualfund.adityabirlacapital.com/historical_nav_and_dividend"
ABSL_API="https://mutualfund.adityabirlacapital.com/postlogin/CustomApi/Shared/PostHistoricalNavandDividend"
DSP_PAGE="https://www.dspim.com/investor-centre/nav"
DSP_API="https://www.dspim.com/ajax"

def main():
    # ABSL: use exact hidden dsitem currently emitted by the public page and exact AMFI code/name.
    page,_,_=providers.fetch(ABSL_PAGE,archive=False,max_bytes=4*1024*1024)
    soup=BeautifulSoup(page,"html.parser")
    ds=soup.select_one("#hisnavdsitem")
    if not ds or not ds.get("value"):raise ValueError("ABSL historical NAV page no longer exposes dsitem")
    payload={
      "SchemeName":"Aditya Birla Sun Life Small Cap Fund - GROWTH",
      "Type":"N","SchemeCode":"105804",
      "FromDate":"31-May-2010","ToDate":"08-Jun-2010","dsitem":ds["value"],
    }
    raw,_,mime=providers.fetch(ABSL_API,body=payload,archive=False,max_bytes=3*1024*1024)
    text=raw.decode("utf-8","ignore")
    print("AMC_NAV_PROBE ABSL",ABSL_API,"mime="+str(mime),"bytes="+str(len(raw)),flush=True)
    try:
        data=json.loads(text)
        print("AMC_NAV_ABSL_META",json.dumps({k:data.get(k) for k in ("ReturnCode","ReturnMsg","SchemeCode","SchemeName")},ensure_ascii=False),flush=True)
        rows=data.get("NAVDetail") or []
        print("AMC_NAV_ABSL_ROWS",len(rows),flush=True)
        for row in rows[:50]:print("AMC_NAV_ABSL_ROW",json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
    except Exception:
        print("AMC_NAV_ABSL_RAW",re.sub(r"\s+"," ",text)[:5000],flush=True)

    # DSP: inspect first-party page markup for the exact Small Cap option value.
    page,_,_=providers.fetch(DSP_PAGE,archive=False,max_bytes=5*1024*1024)
    html=page.decode("utf-8","ignore")
    compact=re.sub(r"\s+"," ",html)
    for m in list(re.finditer(r".{0,700}DSP\s+Small\s+Cap\s+Fund.{0,1200}",compact,re.I))[:12]:
        print("AMC_NAV_DSP_SCHEME_MARKUP",m.group(0)[:2200],flush=True)

    # Candidate values are exact public AMFI code plus any option values discovered beside the fund name.
    candidates=["105989"]
    for m in re.finditer(r'<option[^>]*value=["\']([^"\']+)["\'][^>]*>\s*DSP\s+Small\s+Cap\s+Fund[^<]*</option>',html,re.I):
        if m.group(1) not in candidates:candidates.append(m.group(1))
    # Also inspect inline scheme_list-style object fragments.
    for m in re.finditer(r'["\']([^"\']{1,80})["\']\s*:\s*["\']DSP\s+Small\s+Cap\s+Fund[^"\']*["\']',html,re.I):
        if m.group(1) not in candidates:candidates.append(m.group(1))
    print("AMC_NAV_DSP_CANDIDATES",json.dumps(candidates),flush=True)

    windows=(("08-AUG-2007","16-AUG-2007"),("27-AUG-2008","04-SEP-2008"),
             ("17-MAR-2010","25-MAR-2010"),("07-APR-2010","15-APR-2010"))
    headers={"User-Agent":providers.USER_AGENT,"Referer":DSP_PAGE,"Accept":"application/json,text/javascript,*/*;q=0.01",
             "X-Requested-With":"XMLHttpRequest"}
    for scheme in candidates[:12]:
        for fr,to in windows:
            params={"type":"investment_center","sub_type":"nav","count":"true","for":"datatable",
                    "scheme_type":"EQU","scheme_code":scheme,"from_date":fr,"to_date":to}
            providers.public_url(DSP_API)
            with httpx.Client(timeout=30,headers=headers,follow_redirects=False) as client:
                resp=client.post(DSP_API,params=params,data={"draw":"1","start":"0","length":"100"})
            print("AMC_NAV_PROBE DSP",scheme,fr,to,"status="+str(resp.status_code),
                  "mime="+str(resp.headers.get("content-type")),"bytes="+str(len(resp.content)),
                  "url="+str(resp.request.url),flush=True)
            body=resp.text
            try:
                data=resp.json()
                summary={k:data.get(k) for k in ("draw","recordsTotal","recordsFiltered") if isinstance(data,dict)}
                print("AMC_NAV_DSP_META",scheme,fr,to,json.dumps(summary,ensure_ascii=False),flush=True)
                rows=(data.get("data") or data.get("aaData") or []) if isinstance(data,dict) else []
                print("AMC_NAV_DSP_ROWS",scheme,fr,to,len(rows),flush=True)
                for row in rows[:50]:print("AMC_NAV_DSP_ROW",scheme,fr,to,json.dumps(row,ensure_ascii=False),flush=True)
            except Exception:
                print("AMC_NAV_DSP_RAW",scheme,fr,to,re.sub(r"\s+"," ",body)[:5000],flush=True)

if __name__=="__main__":main()
