"""First-party Tata Mutual Fund and The Wealth Company communication collectors."""
from __future__ import annotations

import json
import re
from datetime import date,datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import db,providers

TATA_FAMILY="Tata Small Cap Fund"
TATA_OUTLOOK="https://info.tatamutualfund.com/combined/TATA/Equity-Marketoutlook.html"
TATA_SOURCE_TITLE="Equity Market Outlook"

WEALTH_FAMILY="The Wealth Company Small Cap Fund"
WEALTH_INSIGHTS="https://www.wealthcompanyamc.in/knowledge-center/current-insights/"
WEALTH_SOURCE_TITLE="Current Insights"

_WEALTH_TITLE=re.compile(
    r"^(Daily Wealth Recap|The NewsMaker)\s*-\s*(\d{1,2}\s+[A-Za-z]+\s+20\d{2})$",
    re.I,
)


def parse_tata(content):
    soup=BeautifulSoup(content,"html.parser")
    text=" ".join(soup.stripped_strings)
    if "MARKET OUTLOOK" not in text.upper() or "Equity market" not in text:
        raise ValueError("Tata Equity Market Outlook identity changed")
    if "Tata Mutual Fund" not in text and "tatamutualfund" not in str(soup).lower():
        # The dedicated info.tatamutualfund.com page may omit the brand from visible copy.
        # Its exact reviewed host/path is validated by ingest_tata.
        pass
    m=re.search(r"\bAs\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})\b",text,re.I)
    as_of=None
    if m:
        try:
            as_of=datetime.strptime(" ".join(m.groups()),"%d %B %Y").date().isoformat()
        except ValueError:
            as_of=None
    return {"title":"Equity Market Outlook","as_of":as_of,"published_at":None}


def ingest_tata(fetch_fn=providers.fetch):
    parsed=urlparse(TATA_OUTLOOK)
    if (parsed.hostname or "").lower()!="info.tatamutualfund.com":
        raise ValueError("Tata Outlook URL escaped reviewed first-party host")
    providers.can_crawl(TATA_OUTLOOK)
    body,h,_=fetch_fn(TATA_OUTLOOK,archive=True,max_bytes=10*1024*1024)
    row=parse_tata(body)
    did=providers.save_document(
        TATA_FAMILY,row["title"],TATA_OUTLOOK,"market view","AMC",
        published=None,origin="AMC")
    providers.doc_version(did,h)
    return {
        "retained":1,
        "as_of":row["as_of"],
        "detail":(
            "1 Tata Equity Market Outlook page retained"
            + (f"; source reports as on {row['as_of']}" if row["as_of"] else "")
            + "; publication day not inferred; 0 download/parser gaps"
        ),
    }


def _wealth_day(raw):
    value=str(raw or "").strip()
    try:
        day=date.fromisoformat(value[:10])
    except ValueError:
        day=None
    if day is None:
        for fmt in ("%d %B %Y","%d %b %Y"):
            try:
                day=datetime.strptime(value,fmt).date()
                break
            except ValueError:
                pass
    return day.isoformat() if day and day<=date.today() else None


def _wealth_asset(url):
    parsed=urlparse(str(url or "").strip())
    return (
        parsed.scheme=="https"
        and (parsed.hostname or "").lower() in ("www.wealthcompanyamc.in","wealthcompanyamc.in")
        and parsed.path.startswith("/uploads/")
        and parsed.path.lower().endswith((".pdf",".png",".jpg",".jpeg"))
    )


def _structured_wealth_rows(content):
    """Parse the server-rendered Next.js Current Insights initialData payload."""
    soup=BeautifulSoup(content,"html.parser")
    rows=[];seen=set()
    for script in soup.find_all("script"):
        raw=script.string or script.get_text() or ""
        start=0
        while True:
            marker=raw.find("self.__next_f.push(",start)
            if marker<0:break
            try:
                frame=json.JSONDecoder().raw_decode(raw[marker+len("self.__next_f.push("):])[0]
            except (TypeError,ValueError):
                start=marker+1
                continue
            start=marker+1
            if not isinstance(frame,list) or len(frame)!=2 or not isinstance(frame[1],str):
                continue
            payload=frame[1]
            token='"initialData":'
            pos=payload.find(token)
            if pos<0:continue
            try:
                items=json.JSONDecoder().raw_decode(payload[pos+len(token):].lstrip())[0]
            except (TypeError,ValueError):
                continue
            if not isinstance(items,list):continue
            for item in items:
                if not isinstance(item,dict):continue
                base_title=str(item.get("title") or "").strip()
                if base_title not in ("Daily Wealth Recap","The NewsMaker"):
                    continue
                published=_wealth_day(item.get("date"))
                translations=item.get("pdfTranslations")
                if not published or not isinstance(translations,list):continue
                eligible=[
                    x for x in translations
                    if isinstance(x,dict) and _wealth_asset(x.get("url"))
                ]
                if not eligible:continue
                chosen=next(
                    (x for x in eligible if str(x.get("language") or "").strip().lower()=="english"),
                    eligible[0],
                )
                target=str(chosen.get("url") or "").strip()
                title=f"{base_title} - {datetime.fromisoformat(published).strftime('%d %B %Y')}"
                key=(target,title,published)
                if key in seen:continue
                seen.add(key)
                rows.append({
                    "title":title,
                    "url":target,
                    "published_at":published,
                })
    return rows


def wealth_candidates(content):
    rows=_structured_wealth_rows(content)
    if not rows:
        # Preserve the simple-anchor fallback for older/static page variants.
        soup=BeautifulSoup(content,"html.parser")
        links=providers.candidate_links(soup,WEALTH_INSIGHTS)
        seen=set()
        for target,label in links.items():
            if not _wealth_asset(target):continue
            title=re.sub(r"\s+"," ",str(label or "").strip())
            match=_WEALTH_TITLE.fullmatch(title)
            if not match:continue
            published=_wealth_day(match.group(2))
            if not published:continue
            key=(target,title,published)
            if key in seen:continue
            seen.add(key)
            rows.append({"title":title,"url":target,"published_at":published})
    rows.sort(key=lambda r:(r["published_at"],r["title"]),reverse=True)
    if not rows:
        raise ValueError("The Wealth Company Current Insights exposed no eligible recap/news-maker assets")
    return rows


def _valid_wealth_asset(url,body,media_type):
    path=urlparse(url).path.lower()
    typ=str(media_type or "").lower()
    if path.endswith(".pdf"):
        return body.startswith(b"%PDF")
    if path.endswith(".png"):
        return body.startswith(b"\x89PNG\r\n\x1a\n")
    if path.endswith((".jpg",".jpeg")):
        return body.startswith(b"\xff\xd8\xff")
    return False


def _archive_wealth_asset(url,body,media_type):
    h=db.archive(body,media_type)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO fetches(url,fetched_at,status,hash) VALUES(?,?,?,?)",
            (url,db.now(),"ok",h),
        )
    return h


def ingest_wealth(fetch_fn=providers.fetch):
    providers.can_crawl(WEALTH_INSIGHTS)
    listing,h,_=fetch_fn(WEALTH_INSIGHTS,archive=True,max_bytes=12*1024*1024)
    text=" ".join(BeautifulSoup(listing,"html.parser").stripped_strings)
    if "Current Insights" not in text:
        raise ValueError("The Wealth Company Current Insights identity changed")
    sid=providers.save_document(
        WEALTH_FAMILY,WEALTH_SOURCE_TITLE,WEALTH_INSIGHTS,
        "source page","AMC",origin="AMC")
    providers.doc_version(sid,h)

    rows=wealth_candidates(listing)
    retained=0;errors=[];accepted=[]
    for row in rows[:20]:
        try:
            providers.can_crawl(row["url"])
            body,_,typ=fetch_fn(row["url"],archive=False,max_bytes=12*1024*1024)
            if not _valid_wealth_asset(row["url"],body,typ):
                raise ValueError("The Wealth Company insight returned unexpected asset content")
            ch=_archive_wealth_asset(row["url"],body,typ)
            did=providers.save_document(
                WEALTH_FAMILY,row["title"],row["url"],"market view","AMC",
                published=row["published_at"],origin="AMC")
            providers.doc_version(did,ch)
            retained+=1;accepted.append(row)
        except Exception as exc:
            errors.append((str(exc) or type(exc).__name__).splitlines()[0][:220])
    if not retained:
        raise ValueError("The Wealth Company Current Insights yielded no retained communications")
    return {
        "retained":retained,
        "rows":accepted,
        "errors":errors,
        "detail":(
            f"{retained} The Wealth Company recap/news-maker assets retained; "
            f"{len(errors)} download/parser gaps"
        ),
    }
