"""Read-only probe for Franklin article API call signature."""
from pathlib import Path
import re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

MAIN="https://www.franklintempletonindia.com/main.290c50984c6d19c0.js"

def main():
    raw,_,_=providers.fetch(MAIN,archive=False,max_bytes=6*1024*1024)
    text=raw.decode("utf-8","ignore")
    print("ARTICLE_BUNDLE_BYTES",len(raw),flush=True)
    for needle in ("getFTIArticleListUrl","api/articleApi","articleList","latest-commentaries","referenceDate"):
        start=0;n=0
        while n<25:
            i=text.find(needle,start)
            if i<0:break
            print("ARTICLE_CONTEXT","needle="+needle,"index="+str(i),
                  repr(text[max(0,i-4500):min(len(text),i+9000)]),flush=True)
            start=i+len(needle);n+=1

if __name__=="__main__":main()
