"""Targeted read-only source discovery for the final three Mid Cap TER gaps."""
from __future__ import annotations

import argparse,hashlib,json,re
from pathlib import Path
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers


def fetch_text(url,max_bytes=8*1024*1024):
    body,_,typ=providers.fetch(url,archive=False,max_bytes=max_bytes)
    return body,body.decode("utf-8","replace"),typ


def bandhan():
    base="https://cmsnew.bandhanmutual.com"
    urls=[
        base+"/wp-json/wp/v2/search?search=150401&per_page=100",
        base+"/wp-json/wp/v2/posts?search=150401&per_page=100",
        base+"/wp-json/wp/v2/posts?search=Bandhan%20Mid%20Cap%20Fund&per_page=100",
    ]
    out={"family":"BANDHAN MID CAP FUND","attempts":[]}
    for url in urls:
        try:
            body,text,typ=fetch_text(url,4*1024*1024)
            item={"url":url,"status":"ok","content_type":typ,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest()}
            try:item["json"]=json.loads(text)
            except Exception:item["text_snippets"]=re.findall(r".{0,160}(?:150401|Bandhan Mid Cap Fund).{0,260}",text,re.I|re.S)[:30]
            out["attempts"].append(item)
        except Exception as exc:
            out["attempts"].append({"url":url,"status":"error","error":(str(exc) or type(exc).__name__)[:500]})
    return out


def boi():
    page="https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund"
    out={"family":"BANK OF INDIA MID CAP FUND","page":page}
    body,text,typ=fetch_text(page,8*1024*1024)
    out.update({"status":"ok","content_type":typ,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest()})
    soup=BeautifulSoup(text,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        src=urljoin(page,tag.get("src"))
        if "boimf" in src or "boiaxamf" in src:
            scripts.append(src)
    out["scripts"]=scripts
    findings=[]
    for src in scripts[:30]:
        try:
            b,t,_=fetch_text(src,5*1024*1024)
            snippets=re.findall(r".{0,220}(?:expense_ratio|total.?expense|scheme.?expense|TER).{0,500}",t,re.I|re.S)
            if snippets:
                findings.append({"url":src,"sha256":hashlib.sha256(b).hexdigest(),"snippets":snippets[:20]})
        except Exception as exc:
            findings.append({"url":src,"error":(str(exc) or type(exc).__name__)[:300]})
    out["script_findings"]=findings
    out["page_snippets"]=re.findall(r".{0,220}(?:expense_ratio|Total Expense Ratio|november-2025\.xlsx).{0,500}",text,re.I|re.S)[:30]
    return out


def whiteoak():
    urls=[
        "https://mf.whiteoakamc.com/WOC/regulatory-disclosures/total-expense-ratio",
        "https://mf.whiteoakcapital.com/WOC/regulatory-disclosures/total-expense-ratio",
        "https://mf.whiteoakamc.com/WOC/regulatory-disclosures",
    ]
    out={"family":"WhiteOak Capital Mid Cap Fund","attempts":[]}
    for url in urls:
        try:
            body,text,typ=fetch_text(url,8*1024*1024)
            soup=BeautifulSoup(text,"html.parser")
            links=[]
            for tag in soup.find_all(["a","script"],href=True):
                href=urljoin(url,tag.get("href"))
                if re.search(r"(?:ter|expense|\.xlsx?|\.xls|\.csv|\.json)",href,re.I):
                    links.append(href)
            for tag in soup.find_all("script",src=True):
                src=urljoin(url,tag.get("src"))
                if re.search(r"(?:api|ter|expense|whiteoak)",src,re.I):links.append(src)
            snippets=re.findall(r".{0,220}(?:WhiteOak Capital Mid Cap Fund|Mid Cap Fund|expense ratio|TER).{0,500}",text,re.I|re.S)
            out["attempts"].append({"url":url,"status":"ok","content_type":typ,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"links":sorted(set(links))[:80],"snippets":snippets[:30]})
        except Exception as exc:
            out["attempts"].append({"url":url,"status":"error","error":(str(exc) or type(exc).__name__)[:500]})
    return out


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    result={"mode":"read_only","production_writes":0,"public_export_enabled":False,
            "targets":[bandhan(),boi(),whiteoak()]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"targets":3,"ok":sum(any(x.get("status")=="ok" for x in t.get("attempts",[])) or t.get("status")=="ok" for t in result["targets"])},indent=2))

if __name__=="__main__":main()
