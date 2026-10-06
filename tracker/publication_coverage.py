"""Read-only AMC communication/publication coverage audit.

The public fund page is intentionally limited to AMC-origin material. This audit
measures whether retained documents include the communication classes requested
for the tracker (newsletters/market or CIO views and letters to unitholders)
without treating factsheets, portfolios or third-party news as communications.
"""
from __future__ import annotations

import re
from collections import Counter

from . import db
from .publications import exclusion_reason
from .disclosures import resolve_registered_amc,registered_source_rows

COMMUNICATION_KINDS=("market view","unitholder letter")
_DOCUMENTED_SOURCE_LIMITATIONS={
    "Trustmf Small Cap Fund":{
        "code":"market_outlook_embedded_in_factsheets_only",
        "reason":(
            "TRUST Mutual Fund currently publishes identifiable Market Outlook commentary "
            "inside monthly factsheets; factsheets are intentionally excluded from "
            "communication coverage until a standalone AMC communication source is found."
        ),
    },
    "Union Small Cap Fund":{
        "code":"first_party_host_connection_refused_from_runner",
        "reason":(
            "Union Mutual Fund publishes qualifying first-party Research Notes / State of the "
            "Market & Outlook documents, but repeated reviewed GitHub production-runner "
            "requests to unionmf.com fail at connection establishment. Keep the registered "
            "source visible and retry in future runs without treating the current transport "
            "failure as missing source discovery."
        ),
    },
}
_DOCUMENTED_ARCHIVE_LIMITATIONS={
    "Franklin India Small Cap Fund":{
        "code":"original_asset_blocked_by_robots_policy",
        "reason":"Franklin commentary metadata and article identity are retained from the first-party API, but the original Widen-hosted binaries remain link-only because automatic access is disallowed by robots policy.",
    },
    "Kotak Small Cap Fund":{
        "code":"original_asset_blocked_by_robots_policy",
        "reason":"Kotak Monthly Market Update metadata and the first-party PDF URL are retained, but the original PDF remains link-only when Kotak robots policy disallows automatic retrieval.",
    },
    "Samco Small Cap Fund":{
        "code":"original_asset_blocked_by_robots_policy",
        "reason":"Samco's retained Small Cap Fund scheme presentation is a qualifying AMC communication, but its media1.samco.in original remains link-only because automatic access is disallowed by robots policy.",
    },
    "LIC Mf Small Cap Fund":{
        "code":"first_party_asset_returns_empty_response",
        "reason":"LIC Mutual Fund's current Market Update page still lists the retained 2025 Monthly Market Outlooks, but their exact first-party PDF endpoints return application/pdf responses with zero bytes under reviewed automated retrieval, including with the Market Update page as same-site referer.",
    },
}
_COMMUNICATION_SOURCE=re.compile(
    r"newsletter|letter.*unitholder|unitholder.*letter|"
    r"market[\s_\-]*(?:outlook|update|view|insights?|commentar(?:y|ies))|equity[\s_\-]*outlook|"
    r"latest[\s_\-]*commentar|investment[\s_\-]*(?:view|outlook)|"
    r"(?:cio|ceo)[\s_\-]*(?:letter|view)|outlooks?\s*&\s*economy|"
    r"product[\s_\-]*note|presentation",
    re.I,
)


def _source_key(amc):
    """Use the collector's canonical AMC/source-key resolver."""
    return resolve_registered_amc(amc,registered_source_rows())


def _source_pages(amc):
    key=_source_key(amc)
    if not key:return []
    rows=db.rows("""SELECT amc_match,url,label,status,last_checked,detail
      FROM source_pages WHERE enabled=1 AND lower(amc_match)=lower(?)
      ORDER BY COALESCE(last_checked,'' ) DESC,id DESC""",(key,))
    return [
        row for row in rows
        if _COMMUNICATION_SOURCE.search((row.get("label") or "")+" "+(row.get("url") or ""))
    ]


def _documents(family,amc):
    docs=db.rows("""SELECT d.id,d.title,d.kind,d.scope,d.url,d.published_at,
                           d.first_seen,d.last_seen,
                           COUNT(v.id) version_count,MAX(v.observed_at) latest_observed_at
                    FROM documents d
                    LEFT JOIN document_versions v ON v.document_id=d.id
                    WHERE d.family=? AND d.origin='AMC'
                      AND d.kind IN ('market view','unitholder letter')
                    GROUP BY d.id
                    ORDER BY COALESCE(d.published_at,d.first_seen) DESC,d.id DESC""",
                 (family,))
    return [d for d in docs if not exclusion_reason(amc,d["url"],d["title"],d["kind"])]


def report():
    """Audit retained AMC communication evidence without fetching or mutating data."""
    funds=[]
    for scheme in db.rows("SELECT DISTINCT family,amc FROM schemes ORDER BY family"):
        family=scheme["family"];amc=scheme["amc"]
        docs=_documents(family,amc)
        source_pages=_source_pages(amc)
        kinds=Counter(d["kind"] for d in docs)
        archived=sum(bool(d["version_count"]) for d in docs)
        published=[d["published_at"] for d in docs if d.get("published_at")]
        observed=[d["latest_observed_at"] for d in docs if d.get("latest_observed_at")]
        issues=[]
        source_limitation=_DOCUMENTED_SOURCE_LIMITATIONS.get(family)
        archive_limitation=_DOCUMENTED_ARCHIVE_LIMITATIONS.get(family)
        if not docs:issues.append("no_amc_communications_collected")
        if not docs and source_limitation:issues.append("communication_source_limitation")
        if docs and archived<len(docs):
            issues.append("communication_document_not_archived")
            if archive_limitation:issues.append("communication_archive_limitation")
        if docs and len(published)<len(docs):issues.append("publication_date_missing")
        row={
            "family":family,
            "amc":amc,
            "communication_count":len(docs),
            "archived_communication_count":archived,
            "market_view_count":kinds.get("market view",0),
            "unitholder_letter_count":kinds.get("unitholder letter",0),
            "published_date_count":len(published),
            "latest_published_at":max(published) if published else None,
            "latest_observed_at":max(observed) if observed else None,
            "registered_communication_sources":source_pages,
            "source_limitation":source_limitation,
            "archive_limitation":archive_limitation,
            "issues":issues,
        }
        funds.append(row)

    no_docs=[r for r in funds if "no_amc_communications_collected" in r["issues"]]
    with_registered=[r for r in no_docs
                     if r["registered_communication_sources"]
                     and not r.get("source_limitation")]
    without_registered=[r for r in no_docs
                        if not r["registered_communication_sources"]
                        and not r.get("source_limitation")]
    limited=[r for r in no_docs if r.get("source_limitation")]
    unarchived=[r for r in funds
                if "communication_document_not_archived" in r["issues"]
                and not r.get("archive_limitation")]
    archive_limited=[r for r in funds
                     if "communication_archive_limitation" in r["issues"]]

    priorities=[]
    if with_registered:
        priorities.append({
            "priority":1,
            "code":"review_registered_communication_sources",
            "actionable":True,
            "affected_funds":[r["family"] for r in with_registered],
            "reason":"A registered first-party communication/news source exists, but no AMC communication document has been retained for the fund.",
        })
    if without_registered:
        priorities.append({
            "priority":2,
            "code":"discover_first_party_communication_sources",
            "actionable":True,
            "affected_funds":[r["family"] for r in without_registered],
            "reason":"No AMC communication has been retained and no dedicated newsletter/market-view/unitholder-letter source page is registered.",
        })
    if limited:
        priorities.append({
            "priority":2,
            "code":"documented_communication_source_limitation",
            "actionable":False,
            "affected_funds":[r["family"] for r in limited],
            "reason":"A qualifying first-party communication source is known, but current collection is limited by an explicit source/transport constraint; retain the visible gap and retry only when that constraint changes.",
        })
    if archive_limited:
        priorities.append({
            "priority":3,
            "code":"documented_communication_archive_limitation",
            "actionable":False,
            "affected_funds":[r["family"] for r in archive_limited],
            "reason":"The original AMC communication asset cannot currently be archived under reviewed automated access constraints (for example robots-policy blocking or an empty first-party asset response); keep the metadata/source link and do not treat this as an ordinary repairable fetch failure.",
        })
    if unarchived:
        priorities.append({
            "priority":3,
            "code":"repair_unarchived_communication_documents",
            "actionable":True,
            "affected_funds":[r["family"] for r in unarchived],
            "reason":"AMC communication metadata is retained but one or more original document versions are not archived.",
        })

    return {
        "built_at":db.now(),
        "policy":{
            "origin":"AMC only",
            "communication_kinds":list(COMMUNICATION_KINDS),
            "third_party_news_included":False,
            "factsheets_and_portfolios_count_as_communications":False,
        },
        "summary":{
            "funds":len(funds),
            "funds_with_amc_communications":sum(bool(r["communication_count"]) for r in funds),
            "funds_without_amc_communications":len(no_docs),
            "communication_documents":sum(r["communication_count"] for r in funds),
            "archived_communication_documents":sum(r["archived_communication_count"] for r in funds),
            "market_views":sum(r["market_view_count"] for r in funds),
            "unitholder_letters":sum(r["unitholder_letter_count"] for r in funds),
            "documents_with_published_date":sum(r["published_date_count"] for r in funds),
            "funds_with_registered_communication_sources":sum(bool(r["registered_communication_sources"]) for r in funds),
            "issue_counts":dict(sorted(Counter(i for r in funds for i in r["issues"]).items())),
        },
        "repair_priorities":priorities,
        "funds":funds,
        "notes":[
            "This audit counts only AMC-origin documents classified as market view or unitholder letter.",
            "Newsletters, CIO/investment/market outlooks and product presentations are normalized to market view by the existing document classifier.",
            "Factsheets, scheme documents, portfolios and generic disclosures remain available on fund pages but do not satisfy communication coverage.",
            "A missing published_at value is reported as missing metadata; first_seen is never substituted as the publication date.",
            "Documented source limitations remain visible as zero communication coverage and are not silently promoted from excluded source classes.",
            "Unavailable originals remain visible as link-only archive limitations when reviewed automated retrieval is blocked or the first-party endpoint returns no document bytes; they are not queued as ordinary repairable download failures.",
            "The audit is read-only and performs no source fetch, document mutation or UI change.",
        ],
    }


def markdown(audit):
    def esc(value):
        return str(value or "").replace("|","\\|").replace("\n"," ")
    s=audit["summary"]
    lines=[
        "# AMC communication coverage audit","",
        f"Prepared: {audit['built_at']}","",
        "**Read-only:** AMC-origin communications only; third-party news is excluded. Factsheets and portfolio files do not count as communications.","",
        "## Summary","",
        f"- Funds with at least one retained AMC communication: **{s['funds_with_amc_communications']} / {s['funds']}**.",
        f"- Funds with no retained AMC communication: **{s['funds_without_amc_communications']}**.",
        f"- Retained communication documents: **{s['communication_documents']}**; archived originals: **{s['archived_communication_documents']}**.",
        f"- Market/newsletter/CIO/product-view documents: **{s['market_views']}**; letters to unitholders: **{s['unitholder_letters']}**.",
        f"- Communication documents with an explicit published date: **{s['documents_with_published_date']}**.",
        f"- Funds with a registered communication-oriented source page: **{s['funds_with_registered_communication_sources']}**.","",
    ]
    if audit["repair_priorities"]:
        lines.extend(["## Repair priorities","",
                      "| Priority | Repair | Actionable | Affected funds | Reason |",
                      "| ---: | --- | --- | ---: | --- |"])
        for p in audit["repair_priorities"]:
            lines.append("| "+" | ".join([
                str(p["priority"]),esc(p["code"]),
                "yes" if p["actionable"] else "no",
                str(len(p["affected_funds"])),esc(p["reason"])
            ])+" |")
        lines.extend(["","### Affected funds",""])
        for p in audit["repair_priorities"]:
            lines.append(f"- **{esc(p['code'])}:** "+", ".join(esc(x) for x in p["affected_funds"]))
        lines.append("")

    lines.extend([
        "## Per-fund audit","",
        "| Fund | Communications | Market views | Unitholder letters | Archived | Published-date docs | Latest published | Registered communication sources | Issues |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ])
    for row in audit["funds"]:
        lines.append("| "+" | ".join([
            esc(row["family"]),
            str(row["communication_count"]),
            str(row["market_view_count"]),
            str(row["unitholder_letter_count"]),
            str(row["archived_communication_count"]),
            str(row["published_date_count"]),
            esc(row["latest_published_at"] or "Gap"),
            str(len(row["registered_communication_sources"])),
            esc(", ".join(row["issues"]) or "none"),
        ])+" |")

    lines.extend(["","## Notes",""])
    for note in audit["notes"]:lines.append("- "+esc(note))
    lines.append("")
    return "\n".join(lines)
