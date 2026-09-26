"""Read-only transport diagnostic for Wealth Company and UTI communication shells."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import db,providers

OUT=ROOT/"deployment"/"communication-transport-wealth-uti.json"

TARGETS=(
    ("Wealth","https://www.wealthcompanyamc.in/knowledge-center/current-insights/"),
    ("UTI","https://www.utimf.com/learn"),
    ("UTI","https://www.utimf.com/leadership-desk/seeking-opportunity-uncrowded-market-segments"),
    ("UTI","https://www.utimf.com/leadership-desk/dont-get-swayed-distractions-markets"),
)

TOKENS=(
    "Daily Wealth Recap",
    "The NewsMaker",
    "uploadDate",
    ".pdf",
    "leadership-desk",
    "market-insight",
    "investment-insight",
    "/api/",
    "__NEXT_DATA__",
    "self.__next_f.push",
    "leadership",
    "marketInsight",
    "investmentInsight",
    "knowledge",
    "article",
    "api/",
)


def same_owner(label,url):
    host=(urlparse(url).hostname or "").lower().removeprefix("www.")
    if label=="Wealth":
        return host=="wealthcompanyamc.in" or host.endswith(".wealthcompanyamc.in")
    if label=="UTI":
        return host=="utimf.com" or host.endswith(".utimf.com")
    return False


def contexts(raw):
    low=raw.lower()
    out=[];seen=set()
    for token in TOKENS:
        start=0
        for _ in range(8):
            i=low.find(token.lower(),start)
            if i<0:break
            key=(token,i)
            if key not in seen:
                seen.add(key)
                out.append({
                    "token":token,
                    "index":i,
                    "context":raw[max(0,i-900):i+2200],
                })
            start=i+len(token)
            if len(out)>=40:return out
    return out


def inspect_script(url):
    item={"url":url}
    try:
        providers.can_crawl(url)
        body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
        raw=body.decode("utf-8","replace")
        item.update({
            "ok":True,
            "bytes":len(body),
            "media_type":typ,
            "contexts":contexts(raw),
        })
        candidates=[];seen=set()
        for match in re.finditer(
            r'''["']([^"'\\]{0,240}(?:leadership|market.?insight|investment.?insight|knowledge|api/)[^"'\\]{0,240})["']''',
            raw,
            re.I,
        ):
            value=match.group(1).strip()
            if value in seen:continue
            seen.add(value);candidates.append(value)
            if len(candidates)>=120:break
        item["candidate_strings"]=candidates
        exact={}
        patterns={
            "cms_urls":r'''cmsUrl\s*:\s*["']([^"']+)["']''',
            "knowledge_center_getters":r'''get\s+knowledgeCenter\(\)\{return([^}]{0,600})\}''',
            "knowledge_center_refs":r'''knowledgeCenter[^,;}{]{0,500}''',
            "cms_api_literals":r'''["']([^"']*/api/[^"']*(?:knowledge|learn|leadership|insight)[^"']*)["']''',
        }
        for name,pattern in patterns.items():
            values=[];matched=set()
            for m in re.finditer(pattern,raw,re.I):
                value=(m.group(1) if m.groups() else m.group(0)).strip()
                if value in matched:continue
                matched.add(value);values.append(value)
                if len(values)>=40:break
            exact[name]=values
        for needle in ("get knowledgeCenter","knowledgeCenter(){return","_urls.knowledgeCenter",
                       "field_knowledge_hub_category","cmsUrl"):
            hits=[];start=0
            low=raw.lower()
            while len(hits)<20:
                idx=low.find(needle.lower(),start)
                if idx<0:break
                hits.append({"index":idx,"context":raw[max(0,idx-1000):idx+2600]})
                start=idx+len(needle)
            exact[needle]=hits
        item["exact_transport"]=exact
    except Exception as exc:
        item.update({
            "ok":False,
            "error":(str(exc) or type(exc).__name__).splitlines()[0][:1000],
        })
    return item


def inspect(label,url):
    item={"label":label,"url":url}
    try:
        providers.can_crawl(url)
        body,_,typ=providers.fetch(url,archive=False,max_bytes=15*1024*1024)
        item.update({"ok":True,"bytes":len(body),"media_type":typ})
        raw=body.decode("utf-8","replace")
        soup=BeautifulSoup(body,"html.parser")
        item["title"]=soup.title.get_text(" ",strip=True)[:500] if soup.title else ""
        item["text_prefix"]=" ".join(soup.stripped_strings)[:2500]
        item["scripts"]=[
            urljoin(url,s.get("src",""))
            for s in soup.select("script[src]")
            if s.get("src")
        ][:80]
        links=[]
        for target,name in providers.candidate_links(soup,url).items():
            combined=f"{name} {target}"
            if not re.search(
                r"daily wealth recap|newsmaker|leadership|market.?insight|investment.?insight|\.pdf",
                combined,re.I,
            ):
                continue
            links.append({
                "label":str(name or "")[:500],
                "url":target,
                "same_owner":same_owner(label,target),
            })
        item["candidate_links"]=links[:120]
        item["contexts"]=contexts(raw)
    except Exception as exc:
        item.update({
            "ok":False,
            "error":(str(exc) or type(exc).__name__).splitlines()[0][:1000],
        })
    return item


UTI_CMS_ENDPOINTS=(
    "https://www.utimf.com/api/CMSDATA_knowledge_hub",
    "https://www.utimf.com/api/homepage-market-insights",
    "https://www.utimf.com/api/homepage-from-cios-desk",
    "https://www.utimf.com/api/cios-desk",
)


def _sample_rows(value):
    if isinstance(value,dict):
        rows=value.get("rows")
        if isinstance(rows,list):return rows
        data=value.get("data")
        if isinstance(data,list):return data
        if isinstance(data,dict):
            nested=data.get("rows")
            if isinstance(nested,list):return nested
    if isinstance(value,list):return value
    return []


def inspect_uti_cms(url):
    item={"url":url}
    try:
        providers.can_crawl(url)
        body,_,typ=providers.fetch(
            url,archive=False,max_bytes=12*1024*1024,
            headers={"Accept":"application/json"},
        )
        item.update({"ok":True,"bytes":len(body),"media_type":typ})
        parsed=json.loads(body.decode("utf-8","replace"))
        item["top_type"]=type(parsed).__name__
        item["top_keys"]=sorted(parsed.keys())[:100] if isinstance(parsed,dict) else []
        rows=_sample_rows(parsed)
        item["row_count"]=len(rows)
        samples=[]
        for row in rows[:30]:
            if not isinstance(row,dict):continue
            samples.append({
                "keys":sorted(row.keys())[:120],
                "nid":row.get("nid"),
                "title":row.get("title") or row.get("content_title") or row.get("field_title"),
                "category":row.get("field_knowledge_hub_category"),
                "asset_type":row.get("field_asset_type"),
                "pdf":row.get("pdf"),
                "s3pdf":row.get("s3pdf"),
                "view_node":row.get("view_node"),
                "date":row.get("date") or row.get("created") or row.get("field_date"),
            })
        item["samples"]=samples
    except Exception as exc:
        item.update({
            "ok":False,
            "error":(str(exc) or type(exc).__name__).splitlines()[0][:1000],
        })
    return item


def main():
    targets=[inspect(label,url) for label,url in TARGETS]
    uti_scripts=[]
    for item in targets:
        if item.get("label")!="UTI" or item.get("url")!="https://www.utimf.com/learn":
            continue
        for src in item.get("scripts",[]):
            parsed=urlparse(src)
            if ((parsed.hostname or "").lower() not in ("www.utimf.com","utimf.com")
                or not parsed.path.rsplit("/",1)[-1].startswith("main.")):
                continue
            uti_scripts.append(inspect_script(src))
    report={
        "prepared_at":db.now(),
        "mode":"read_only_non_fatal",
        "targets":targets,
        "uti_scripts":uti_scripts,
        "uti_cms":[inspect_uti_cms(url) for url in UTI_CMS_ENDPOINTS],
        "notes":[
            "No response bytes are archived by this diagnostic.",
            "Raw contexts are bounded around known communication/API markers only.",
            "UTI root main.*.js is inspected read-only for first-party content/API transport strings.",
            "UTI CMS probes persist only response shape and selected communication fields; response bytes are not archived.",
            "Candidate links/strings still require source-specific validation before collection.",
        ],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Wrote",OUT,flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
