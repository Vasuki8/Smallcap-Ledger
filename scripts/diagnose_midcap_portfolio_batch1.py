"""Read-only source diagnostic for first staged Mid Cap portfolio batch."""
from __future__ import annotations

import argparse,hashlib,json,re
from pathlib import Path
import sys
from urllib.parse import urljoin,unquote

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tracker import providers


TARGETS={
    "HDFC Mid Cap Fund":"https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio",
    "DSP Midcap Fund":"https://www.dspim.com/mandatory-disclosures/portfolio-disclosures",
    "Baroda BNP Paribas Mid Cap Fund":"https://www.barodabnpparibasmf.in/downloads/monthly-portfolio-scheme",
    "Canara Robeco Mid Cap Fund":"https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html",
    "Kotak Mid Cap Fund":"https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html",
}

FILE_RE=re.compile(r"""(?P<url>https?://[^"'<>\s\\]+\.(?:xlsx?|xls|zip|csv|pdf)(?:\?[^"'<>\s\\]*)?|/[^"'<>\s\\]+\.(?:xlsx?|xls|zip|csv|pdf)(?:\?[^"'<>\s\\]*)?)""",re.I)


def clean(value):
    return re.sub(r"\s+"," ",str(value or "")).strip()


def inspect(family,url):
    body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
    text=body.decode("utf-8","replace")
    soup=BeautifulSoup(text,"html.parser")
    links={}
    for href,label in providers.candidate_links(soup,url).items():
        context=clean(label)
        if family.casefold().replace(" ","") in (href+" "+context).casefold().replace(" ","") or re.search(r"portfolio|monthly|31.?august.?2026|august.?31.?2026",href+" "+context,re.I):
            links[href]=context
    for m in FILE_RE.finditer(text):
        raw=m.group("url").replace("\\/","/")
        absolute=urljoin(url,raw)
        around=clean(text[max(0,m.start()-250):min(len(text),m.end()+350)])
        if family.casefold().replace(" ","") in (absolute+" "+around).casefold().replace(" ","") or re.search(r"portfolio|31.?august.?2026|august.?31.?2026",absolute+" "+around,re.I):
            links.setdefault(absolute,around[:700])
    family_norm=family.casefold().replace(" ","")
    tables=[]
    for ti,table in enumerate(soup.find_all("table")):
        rows=[]
        raw_table=clean(table.get_text(" ",strip=True))
        if family_norm not in raw_table.casefold().replace(" ","") and not re.search(r"portfolio|%\s*to\s*(?:nav|net)|name of.*(?:issuer|instrument)",raw_table,re.I):
            continue
        for ri,tr in enumerate(table.find_all("tr")):
            vals=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
            if vals: rows.append(vals)
            if len(rows)>=140:break
        if rows:
            tables.append({"index":ti,"rows":rows[:140]})
    snippets=[]
    flat=clean(soup.get_text(" ",strip=True))
    for pat in (family,r"portfolio",r"31(?:st)?\s+August\s+2026",r"August\s+31,\s*2026"):
        for m in re.finditer(pat,flat,re.I):
            snippets.append(flat[max(0,m.start()-220):min(len(flat),m.end()+500)])
            if len(snippets)>=20:break
        if len(snippets)>=20:break
    return {
        "family":family,"url":url,"status":"ok","bytes":len(body),
        "content_type":typ,"sha256":hashlib.sha256(body).hexdigest(),
        "candidate_links":[{"url":u,"label":v} for u,v in sorted(links.items())[:120]],
        "tables":tables[:12],"snippets":snippets,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    result={"mode":"read_only","production_writes":0,"public_export_enabled":False,"targets":[]}
    for family,url in TARGETS.items():
        try: result["targets"].append(inspect(family,url))
        except Exception as exc:
            result["targets"].append({"family":family,"url":url,"status":"error","error":(str(exc) or type(exc).__name__)[:500]})
    result["summary"]={
        "targets":len(TARGETS),
        "ok":sum(x["status"]=="ok" for x in result["targets"]),
        "errors":sum(x["status"]=="error" for x in result["targets"]),
        "candidate_links":sum(len(x.get("candidate_links",[])) for x in result["targets"]),
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result["summary"],indent=2))

if __name__=="__main__":
    main()
