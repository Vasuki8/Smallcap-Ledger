"""Read-only extraction of exact ABSL/DSP historical NAV browser request contracts."""
from __future__ import annotations
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tracker import providers

SOURCES=(
 ("ABSL","https://mutualfund.adityabirlacapital.com/Content/js/global.js",
  ("function getHistoNav","GetSchemeCategory","PostHistoricalNavandDividend")),
 ("DSP","https://www.dspim.com/assets/js/investment-center.js?v=1789985673",
  ("function get_host_url","function get_sub_url","get_sub_url=function","get_host_url=function","scheme_type","ajaxurl")),
 ("DSP_COMMON","https://www.dspim.com/assets/js/common_page.js?v=1789985673",
  ("function get_host_url","get_host_url=function","api_host","host_url")),
)
def main():
    for label,url,needles in SOURCES:
        body,_,_=providers.fetch(url,archive=False,max_bytes=5*1024*1024)
        text=body.decode("utf-8","ignore")
        print("NAV_CONTRACT_SOURCE",label,url,"bytes="+str(len(body)),flush=True)
        emitted=set()
        for needle in needles:
            start=0
            while True:
                i=text.find(needle,start)
                if i<0:break
                snippet=re.sub(r"\s+"," ",text[max(0,i-1800):min(len(text),i+6500)]).strip()
                key=snippet[:500]
                if key not in emitted:
                    emitted.add(key)
                    print("NAV_CONTRACT",label,needle,snippet,flush=True)
                start=i+len(needle)
                if len(emitted)>=12:break
            if len(emitted)>=12:break
if __name__=="__main__":main()
