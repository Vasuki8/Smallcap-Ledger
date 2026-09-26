"""Read-only probe for Franklin article/search endpoint configuration."""
from pathlib import Path
import json,re,sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

SHELL="https://www.franklintempletonindia.com/sebi-circular/current"
MAIN="https://www.franklintempletonindia.com/main.290c50984c6d19c0.js"

def show(label,text):
    print(label,repr(text[:16000]),flush=True)

def main():
    raw,_,_=providers.fetch(MAIN,archive=False,max_bytes=6*1024*1024)
    text=raw.decode("utf-8","ignore")
    print("ARTICLE_BUNDLE_BYTES",len(raw),flush=True)

    patterns=(
        r'getFTIArticleListUrl\(\)\{[^}]{0,2500}\}',
        r'getFTIArticleListUrl[^;]{0,2500}',
        r'ftiApiDomain[^;]{0,2500}',
        r'searchArticleContent[^;]{0,2500}',
        r'articleApi[^;]{0,2500}',
        r'articleList[^;]{0,2500}',
    )
    for pat in patterns:
        seen=set()
        for m in re.finditer(pat,text,re.I):
            chunk=m.group(0)
            if chunk in seen:continue
            seen.add(chunk)
            show("ARTICLE_REGEX "+pat+" @"+str(m.start()),chunk)

    strings=set()
    for m in re.finditer(r'["\']([^"\']{1,500})["\']',text):
        value=m.group(1)
        low=value.lower()
        if any(k in low for k in ("article","search","api")) and (
            value.startswith(("http://","https://","/")) or
            "article" in low or "search" in low):
            strings.add(value)
    for value in sorted(strings):
        if any(k in value.lower() for k in ("article","search","fti")):
            print("ARTICLE_STRING",repr(value[:800]),flush=True)

    shell,_,_=providers.fetch(SHELL,archive=False,max_bytes=8*1024*1024)
    soup=BeautifulSoup(shell,"html.parser")
    for tag in soup.find_all(True):
        for name,val in tag.attrs.items():
            vals=val if isinstance(val,list) else [val]
            for item in vals:
                if not isinstance(item,str):continue
                if item.endswith(".json") or "config" in item.lower() or "environment" in item.lower():
                    print("ARTICLE_SHELL_ATTR",tag.name,name,repr(item[:1000]),flush=True)
    for script in soup.select("script"):
        raw=(script.string or script.get_text() or "")
        if "config" in raw.lower() or "environment" in raw.lower():
            show("ARTICLE_SHELL_INLINE",raw)

if __name__=="__main__":
    main()
