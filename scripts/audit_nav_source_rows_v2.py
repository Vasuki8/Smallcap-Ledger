"""One-time first-party AMC historical NAV row probe v2. Read-only."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tracker import providers

ABSL_PAGE="https://mutualfund.adityabirlacapital.com/historical_nav_and_dividend"
ABSL_JSON_ROUTES=(
 "https://mutualfund.adityabirlacapital.com/api/sitecore/Shared/PostHistoricalNavandDividend",
 "https://mutualfund.adityabirlacapital.com/postlogin/CustomApi/Shared/PostHistoricalNavandDividend",
)
ABSL_FILE="https://mutualfund.adityabirlacapital.com/api/sitecore/Shared/PostHistoricalNavandDividendFile"
DSP_PAGE="https://www.dspim.com/investor-centre/nav"
DSP_API="https://www.dspim.com/ajax"

def probe_absl():
    page,_,_=providers.fetch(ABSL_PAGE,archive=False,max_bytes=4*1024*1024)
    soup=BeautifulSoup(page,"html.parser")
    ds=soup.select_one("#hisnavdsitem")
    if not ds or not ds.get("value"):raise ValueError("ABSL historical NAV page no longer exposes dsitem")
    payload={
      "SchemeName":"Aditya Birla Sun Life Small Cap Fund - GROWTH",
      "Type":"N","SchemeCode":"105804",
      "FromDate":"31-May-2010","ToDate":"08-Jun-2010","dsitem":ds["value"],
    }
    headers={"User-Agent":providers.USER_AGENT,"Referer":ABSL_PAGE,
             "Accept":"application/json,text/javascript,*/*;q=0.01","X-Requested-With":"XMLHttpRequest"}
    for url in ABSL_JSON_ROUTES:
        try:
            providers.public_url(url)
            with httpx.Client(timeout=30,headers=headers,follow_redirects=False) as client:
                resp=client.post(url,json=payload)
            print("AMC_NAV_ABSL_JSON",url,"status="+str(resp.status_code),
                  "mime="+str(resp.headers.get("content-type")),"bytes="+str(len(resp.content)),flush=True)
            if resp.status_code!=200:
                print("AMC_NAV_ABSL_JSON_RAW",url,re.sub(r"\s+"," ",resp.text)[:1200],flush=True)
                continue
            data=resp.json()
            print("AMC_NAV_ABSL_META",url,json.dumps({k:data.get(k) for k in ("ReturnCode","ReturnMsg","SchemeCode","SchemeName")},ensure_ascii=False),flush=True)
            rows=data.get("NAVDetail") or []
            print("AMC_NAV_ABSL_ROWS",url,len(rows),flush=True)
            for row in rows[:60]:print("AMC_NAV_ABSL_ROW",url,json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
        except Exception as exc:
            print("AMC_NAV_ABSL_ERR",url,(str(exc) or type(exc).__name__)[:500],flush=True)
    query=urlencode({k:payload[k] for k in ("SchemeName","Type","SchemeCode","FromDate","ToDate")})
    url=ABSL_FILE+"?"+query
    try:
        providers.public_url(url)
        with httpx.Client(timeout=30,headers={"User-Agent":providers.USER_AGENT,"Referer":ABSL_PAGE},follow_redirects=False) as client:
            resp=client.get(url)
        print("AMC_NAV_ABSL_FILE",url,"status="+str(resp.status_code),
              "mime="+str(resp.headers.get("content-type")),"bytes="+str(len(resp.content)),
              "disposition="+str(resp.headers.get("content-disposition")),flush=True)
        if len(resp.content)<12000:
            print("AMC_NAV_ABSL_FILE_RAW",re.sub(rb"\s+",b" ",resp.content)[:6000].decode("utf-8","ignore"),flush=True)
    except Exception as exc:
        print("AMC_NAV_ABSL_FILE_ERR",(str(exc) or type(exc).__name__)[:500],flush=True)

def probe_dsp():
    page,_,_=providers.fetch(DSP_PAGE,archive=False,max_bytes=5*1024*1024)
    html=page.decode("utf-8","ignore")
    compact=re.sub(r"\s+"," ",html)
    candidates=["157"]
    patterns=(
      r'<option[^>]*value=["\']([^"\']+)["\'][^>]*>\s*DSP\s+Small\s+Cap\s+Fund[^<]*</option>',
      r'["\']([^"\']{1,80})["\']\s*:\s*["\']DSP\s+Small\s+Cap\s+Fund[^"\']*["\']',
      r'DSP\s+Small\s+Cap\s+Fund.{0,400}?value=["\']([^"\']+)["\']',
    )
    for pat in patterns:
        for m in re.finditer(pat,html,re.I|re.S):
            if m.group(1) not in candidates:candidates.append(m.group(1))
    for m in list(re.finditer(r".{0,600}DSP\s+Small\s+Cap\s+Fund.{0,900}",compact,re.I))[:8]:
        print("AMC_NAV_DSP_SCHEME_MARKUP",m.group(0)[:1600],flush=True)
    print("AMC_NAV_DSP_CANDIDATES",json.dumps(candidates),flush=True)
    windows=(("08-AUG-2007","16-AUG-2007"),("27-AUG-2008","04-SEP-2008"),
             ("17-MAR-2010","25-MAR-2010"),("07-APR-2010","15-APR-2010"),
             ("01-SEP-2026","10-SEP-2026"))
    headers={"User-Agent":providers.USER_AGENT,"Referer":DSP_PAGE,"Accept":"application/json,text/javascript,*/*;q=0.01",
             "X-Requested-With":"XMLHttpRequest"}
    for scheme in candidates[:12]:
        for fr,to in windows:
            params={"type":"investment_center","sub_type":"nav","count":"true","for":"datatable",
                    "scheme_type":"EQU","scheme_code":scheme,"from_date":fr,"to_date":to}
            providers.public_url(DSP_API)
            try:
                with httpx.Client(timeout=30,headers=headers,follow_redirects=False) as client:
                    resp=client.post(DSP_API,params=params,data={"draw":"1","start":"0","length":"100"})
                print("AMC_NAV_PROBE DSP",scheme,fr,to,"status="+str(resp.status_code),
                      "mime="+str(resp.headers.get("content-type")),"bytes="+str(len(resp.content)),
                      "url="+str(resp.request.url),flush=True)
                try:
                    data=resp.json()
                    summary={k:data.get(k) for k in ("draw","recordsTotal","recordsFiltered") if isinstance(data,dict)}
                    print("AMC_NAV_DSP_META",scheme,fr,to,json.dumps(summary,ensure_ascii=False),flush=True)
                    rows=(data.get("data") or data.get("aaData") or []) if isinstance(data,dict) else []
                    print("AMC_NAV_DSP_ROWS",scheme,fr,to,len(rows),flush=True)
                    for row in rows[:60]:print("AMC_NAV_DSP_ROW",scheme,fr,to,json.dumps(row,ensure_ascii=False),flush=True)
                except Exception:
                    print("AMC_NAV_DSP_RAW",scheme,fr,to,re.sub(r"\s+"," ",resp.text)[:2500],flush=True)
            except Exception as exc:
                print("AMC_NAV_DSP_ERR",scheme,fr,to,(str(exc) or type(exc).__name__)[:500],flush=True)

def main():
    try:probe_absl()
    except Exception as exc:print("AMC_NAV_ABSL_FATAL",(str(exc) or type(exc).__name__)[:500],flush=True)
    try:probe_dsp()
    except Exception as exc:print("AMC_NAV_DSP_FATAL",(str(exc) or type(exc).__name__)[:500],flush=True)

if __name__=="__main__":main()
