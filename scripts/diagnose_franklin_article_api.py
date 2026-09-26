"""Read-only live probe for Franklin's public article API."""
from pathlib import Path
import json,sys
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

ENDPOINT="https://www.franklintempletonindia.com/api/articleApi"

def main():
    providers.public_url(ENDPOINT)
    try:
        providers.can_crawl(ENDPOINT)
    except Exception as exc:
        print("ARTICLE_API_ROBOTS_ERROR",(str(exc) or type(exc).__name__)[:1000],flush=True)
        return

    filters=json.dumps([
        {"fieldName":"documentType.exact","fieldValue":["INDVideoArticles","INDArticleDetails"]},
        {"fieldName":"pageType","fieldValue":["latest-commentaries"]},
    ],separators=(",",":"))
    form={
        "query":"*",
        "audience":"investor",
        "locale":"en-in-new",
        "filters":filters,
        "collection":"pages",
        "start":"0",
        "number":"40",
        "loggedIn":"n",
        "articleType":"",
        "env":"prod",
    }
    headers={
        "User-Agent":providers.USER_AGENT,
        "Accept":"*/*",
        "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
        "Referer":"https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries",
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(30,connect=15),follow_redirects=False,headers=headers) as client:
            r=client.post(ENDPOINT,data=form)
        print("ARTICLE_API_HTTP",r.status_code,len(r.content),r.headers.get("content-type",""),flush=True)
        if r.is_redirect:
            print("ARTICLE_API_REDIRECT",r.headers.get("location",""),flush=True)
            return
        r.raise_for_status()
        obj=r.json()
        print("ARTICLE_API_TOP",repr(list(obj) if isinstance(obj,dict) else type(obj).__name__),flush=True)
        hits=(((obj.get("results") or {}).get("response") or {}).get("hits") or {}).get("hits") or []
        print("ARTICLE_API_HITS",len(hits),flush=True)
        for hit in hits[:40]:
            src=hit.get("_source") or {}
            print("ARTICLE_API_HIT",json.dumps({
                "title":src.get("title") or src.get("pageTitle"),
                "pageTitle":src.get("pageTitle"),
                "pageType":src.get("pageType"),
                "documentType":src.get("documentType"),
                "articleType":src.get("articleType"),
                "referenceDate":src.get("referenceDate"),
                "publishDate":src.get("publishDate"),
                "pdfURL":src.get("pdfURL"),
                "documentPath":src.get("documentPath"),
                "navigationUrl":src.get("navigationUrl"),
                "widenAssetJson":src.get("widenAssetJson"),
            },ensure_ascii=False,sort_keys=True)[:7000],flush=True)
    except Exception as exc:
        print("ARTICLE_API_ERROR",(str(exc) or type(exc).__name__).splitlines()[0][:1500],flush=True)

if __name__=="__main__":
    main()
