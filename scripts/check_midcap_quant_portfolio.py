"""Read-only discovery probe for quant Mid Cap monthly portfolio disclosures."""
from __future__ import annotations

import json
import re
from pathlib import Path
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers

SOURCE="https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser"


def clean(value):
    return " ".join(str(value or "").split())


def main():
    body,_,typ=providers.fetch(SOURCE,archive=False,max_bytes=12*1024*1024)
    html=body.decode("utf-8","replace")
    soup=BeautifulSoup(html,"html.parser")
    anchors=[]
    for a in soup.find_all("a",href=True):
        text=clean(a.get_text(" ",strip=True))
        href=urljoin(SOURCE,str(a.get("href") or "").strip())
        combined=(text+" "+href).casefold()
        if any(token in combined for token in ("portfolio","mid cap","midcap","2026","aug")):
            anchors.append({"text":text[:220],"href":href[:700]})
    scripts=[]
    snippets=[]
    for script in soup.find_all("script"):
        text=str(script.string or script.get_text(" ",strip=True) or "")
        if re.search(r"portfolio|disclos|ajax|mid.?cap",text,re.I):
            for match in re.findall(r"""(?:url|href|action)\s*[:=]\s*["']([^"']+)["']""",text,re.I):
                scripts.append(urljoin(SOURCE,match)[:700])
            for endpoint in ("displaydisclouser","displaydisclouser1","displaydisclouser2","displaydisfundname"):
                for hit in re.finditer(endpoint,text,re.I):
                    snippets.append(clean(text[max(0,hit.start()-1200):hit.end()+1800])[:3200])
    print(json.dumps({
        "mode":"read_only_quant_midcap_portfolio_discovery_probe",
        "source":SOURCE,
        "content_type":typ,
        "anchor_candidates":anchors[:120],
        "script_endpoint_candidates":list(dict.fromkeys(scripts))[:80],
        "endpoint_script_snippets":list(dict.fromkeys(snippets))[:20],
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
