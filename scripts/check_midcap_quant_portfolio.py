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
from tracker.coverage import expected_portfolio_as_of
from tracker.midcap_portfolio_structured import _parse_workbook

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
    literal_calls=[]
    for match in re.finditer(
        r"""(?:PageMethods\.)?(displaydisclouser2|displaydisclouser1|displaydisclouser|displaydisfundname)\s*\(\s*(['"][^'"]*['"]|\d+)\s*,\s*(['"][^'"]*['"]|\d+)(?:\s*,\s*(['"][^'"]*['"]|\d+))?""",
        html,re.I,
    ):
        literal_calls.append({
            "method":match.group(1),
            "id":match.group(2),
            "cat":match.group(3),
            "tab":match.group(4),
        })
    event_attrs=[]
    for tag in soup.find_all(True):
        for name,value in tag.attrs.items():
            raw=" ".join(value) if isinstance(value,list) else str(value)
            if "displaydis" in raw.casefold():
                event_attrs.append({"tag":tag.name,"attr":name,"value":clean(raw)[:1800]})
    disclosure_blocks=[]
    for node in soup.find_all(string=lambda value: value and "MONTHLY PORTFOLIO - FUND - WISE" in clean(value).upper()):
        current=node.parent
        ancestors=[]
        for parent in list(current.parents)[:7]:
            if getattr(parent,"name",None):
                ancestors.append({"tag":parent.name,"html":str(parent)[:9000]})
        disclosure_blocks.append({"node":str(current)[:3000],"ancestors":ancestors})
    submit_defs=[]
    for name in ("submit_event1","submit_event2","submit_event"):
        for hit in re.finditer(r"function\s+"+re.escape(name)+r"\s*\(",html,re.I):
            submit_defs.append(clean(html[max(0,hit.start()-400):hit.start()+5200])[:5600])
    script_srcs=[
        urljoin(SOURCE,str(tag.get("src") or "").strip())
        for tag in soup.find_all("script",src=True)
        if str(tag.get("src") or "").strip()
    ]
    year_endpoint="https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser1"
    year_raw,_,year_type=providers.fetch(
        year_endpoint,
        body={"id":"2026","cat":"MONTHLY PORTFOLIO - FUND - WISE"},
        archive=False,
        max_bytes=4*1024*1024,
        headers={"Referer":SOURCE},
    )
    year_payload=json.loads(year_raw)
    year_html=str(year_payload.get("d") or "")
    year_soup=BeautifulSoup(year_html,"html.parser")
    year_controls=[]
    for tag in year_soup.find_all(True):
        attrs={k:(" ".join(v) if isinstance(v,list) else str(v)) for k,v in tag.attrs.items()}
        rendered=clean(tag.get_text(" ",strip=True))
        if rendered or any("submit_event" in value for value in attrs.values()):
            year_controls.append({"tag":tag.name,"text":rendered[:240],"attrs":attrs})
    month_endpoint="https://quantmutual.com/statutorydisclosures.aspx/displaydisclouser2"
    month_raw,_,month_type=providers.fetch(
        month_endpoint,
        body={"id":"8","cat":"MONTHLY PORTFOLIO - FUND - WISE","tab":"2026"},
        archive=False,
        max_bytes=8*1024*1024,
        headers={"Referer":SOURCE},
    )
    month_payload=json.loads(month_raw)
    month_html=str(month_payload.get("d") or "")
    month_soup=BeautifulSoup(month_html,"html.parser")
    month_links=[
        {"text":clean(a.get_text(" ",strip=True))[:300],
         "href":urljoin(SOURCE,str(a.get("href") or "").strip())[:900]}
        for a in month_soup.find_all("a",href=True)
    ]
    exact=[x for x in month_links if clean(x["text"]).casefold()=="quant mid cap fund"]
    if len(exact)!=1:
        raise ValueError(f"Quant August disclosure exposed {len(exact)} exact Mid Cap links")
    workbook_url=exact[0]["href"]
    workbook,_,workbook_type=providers.fetch(
        workbook_url,archive=False,max_bytes=30*1024*1024,headers={"Referer":SOURCE}
    )
    parsed=_parse_workbook(workbook,"Quant Mid Cap Fund",expected_portfolio_as_of())
    print(json.dumps({
        "mode":"read_only_quant_midcap_portfolio_discovery_probe",
        "source":SOURCE,
        "content_type":typ,
        "anchor_candidates":anchors[:120],
        "script_endpoint_candidates":list(dict.fromkeys(scripts))[:80],
        "endpoint_script_snippets":list(dict.fromkeys(snippets))[:20],
        "literal_method_calls":literal_calls[:120],
        "event_attributes":event_attrs[:120],
        "monthly_fundwise_dom":disclosure_blocks[:4],
        "submit_function_snippets":list(dict.fromkeys(submit_defs))[:20],
        "script_sources":script_srcs,
        "year_endpoint_content_type":year_type,
        "year_response_controls":year_controls[:160],
        "year_response_html":year_html[:12000],
        "month_endpoint_content_type":month_type,
        "august_links":month_links[:200],
        "month_response_html":month_html[:18000],
        "workbook_source":workbook_url,
        "workbook_content_type":workbook_type,
        "parsed_portfolio":{
            "as_of":parsed.get("as_of"),
            "positions_observed":parsed.get("positions_observed"),
            "complete":parsed.get("complete"),
            "unknown_rows":parsed.get("unknown_rows"),
            "aum":parsed.get("aum"),
            "sheet":parsed.get("sheet"),
        },
        "production_writes":0,
        "public_export_enabled":False,
    },indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
