"""Read-only recovery queue for incomplete Small Cap portfolios.

The queue ranks work by source actionability, not by number of retained positions.
It never fetches a source, changes a portfolio, or estimates a missing weight.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

from . import coverage, db


# Reviewed recovery policy for the currently verified source boundaries.
# Exact URLs are evidence/watch points, not alternate download guesses.
_POLICY = {
    "Axis Small Cap Fund": {
        "action": "search_fuller_first_party_disclosure",
        "score": 90,
        "actionable_now": True,
        "retry_condition": (
            "Search first-party Axis statutory/monthly portfolio disclosures for a "
            "constituent-level source that identifies holdings hidden by the current aggregate."
        ),
    },
    "Bajaj Finserv Small Cap Fund": {
        "action": "retry_after_source_change",
        "reviewed_at": "2026-09-25T03:10:32+00:00",
        "watch_mode": "exact_route",
        "score": 40,
        "actionable_now": False,
        "recovery_url": "https://www.bajajamc.com/downloads",
        "retry_condition": (
            "Retry only when the AMC Downloads transport becomes usable from the production "
            "runner or an exact current monthly Small Cap attachment URL is exposed first-party."
        ),
    },
    "Edelweiss Small Cap Fund": {
        "action": "retry_after_source_change",
        "reviewed_at": "2026-09-25T03:24:35+00:00",
        "watch_mode": "exact_route",
        "score": 40,
        "actionable_now": False,
        "recovery_url": "https://www.edelweissmf.com/statutory/portfolio-of-schemes",
        "retry_condition": (
            "Retry only when the statutory portfolio route/static application transport becomes "
            "reachable again or it exposes an exact monthly portfolio attachment."
        ),
    },
    "ICICI Prudential Small Cap Fund": {
        "action": "retry_after_source_change",
        "reviewed_at": "2026-09-25T04:23:12+00:00",
        "watch_mode": "exact_route",
        "score": 40,
        "actionable_now": False,
        "recovery_url": (
            "https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/"
            "2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip"
        ),
        "retry_condition": (
            "Retry only when the first-party monthly ZIP stops redirecting to an unresolved "
            "archive host or ICICI exposes the same archive through another working first-party route."
        ),
    },
    "Union Small Cap Fund": {
        "action": "retry_after_source_change",
        "reviewed_at": "2026-09-25T03:10:32+00:00",
        "watch_mode": "host_transport",
        "score": 40,
        "actionable_now": False,
        "recovery_url": "https://www.unionmf.com/about-us/downloads/monthly-portfolio",
        "retry_condition": (
            "Retry only after Union's official Downloads/portfolio transport is reachable from "
            "the production collection network or an exact first-party attachment is exposed."
        ),
    },
    "Bandhan Small Cap Fund": {
        "action": "requires_more_precise_amc_disclosure",
        "score": 20,
        "actionable_now": False,
        "retry_condition": (
            "Revisit only when the AMC publishes exact numeric NAV weights for positions currently "
            "disclosed with a less-than-0.01% marker."
        ),
    },
    "Sundaram Small Cap Fund": {
        "action": "requires_more_precise_amc_disclosure",
        "score": 20,
        "actionable_now": False,
        "retry_condition": (
            "Revisit only when the AMC publishes an exact numeric weight for the written-off "
            "holding currently disclosed only as less than 0.01%."
        ),
    },
    "UTI Small Cap Fund": {
        "action": "requires_more_precise_amc_disclosure",
        "score": 20,
        "actionable_now": False,
        "retry_condition": (
            "Revisit only when the AMC publishes exact numeric NAV weights for the censored tiny "
            "security and short-term deposits."
        ),
    },
}

_ACTION_DEFAULTS = {
    "partial_reason_unclassified": {
        "action": "review_changed_partial_source",
        "score": 100,
        "actionable_now": True,
        "retry_condition": (
            "Review the changed first-party source and classify its exact disclosure boundary "
            "before any further recovery work."
        ),
    },
    "undisclosed_constituents": {
        "action": "search_fuller_first_party_disclosure",
        "score": 90,
        "actionable_now": True,
        "retry_condition": (
            "Search first-party statutory/monthly disclosures for a fuller constituent-level source."
        ),
    },
    "named_subset_only": {
        "action": "search_fuller_first_party_disclosure",
        "score": 85,
        "actionable_now": True,
        "retry_condition": (
            "Search first-party statutory/monthly disclosures for a fuller constituent-level source."
        ),
    },
    "non_numeric_source_weight": {
        "action": "requires_more_precise_amc_disclosure",
        "score": 20,
        "actionable_now": False,
        "retry_condition": (
            "Revisit only when the AMC publishes the currently censored/non-numeric weights exactly."
        ),
    },
    "upstream_source_unavailable": {
        "action": "retry_after_source_change",
        "score": 40,
        "actionable_now": False,
        "retry_condition": (
            "Retry only after first-party source transport materially changes."
        ),
    },
}


def _amc_source_pages(amc):
    return db.rows(
        """SELECT url,label,status,last_checked,detail
           FROM source_pages
           WHERE enabled=1
             AND (instr(lower(?),lower(amc_match))>0
                  OR instr(lower(amc_match),lower(?))>0)
           ORDER BY COALESCE(last_checked,'') DESC,id DESC""",
        (amc, amc),
    )


def _host(url):
    return (urlparse(str(url or "")).hostname or "").lower().removeprefix("www.")


def _source_page_evidence(amc, watched_urls):
    """Prefer an exact/same-host source page; fall back to the AMC's latest check."""
    rows = _amc_source_pages(amc)
    if not rows:
        return None
    watched = [u for u in watched_urls if u]
    for row in rows:
        if row["url"] in watched:
            return {**row, "match": "exact_url"}
    watched_hosts = {_host(u) for u in watched if _host(u)}
    for row in rows:
        h = _host(row["url"])
        if h and h in watched_hosts:
            return {**row, "match": "same_host"}
    return {**rows[0], "match": "latest_amc_check"}


def _latest_fetch(watched_urls):
    """Return the newest retained exact-URL fetch among watched first-party URLs."""
    best = None
    for url in dict.fromkeys(u for u in watched_urls if u):
        row = db.one(
            """SELECT url,fetched_at,status,hash,detail
               FROM fetches WHERE url=?
               ORDER BY fetched_at DESC,id DESC LIMIT 1""",
            (url,),
        )
        if row and (best is None or row["fetched_at"] > best["fetched_at"]):
            best = row
    return best


def _exact_source_page(url):
    if not url:
        return None
    return db.one(
        """SELECT url,label,status,last_checked,detail
           FROM source_pages
           WHERE enabled=1 AND url=?
           ORDER BY COALESCE(last_checked,'') DESC,id DESC LIMIT 1""",
        (url,),
    )


def _host_source_page(amc, url):
    """Newest retained source-page check on the watched host."""
    watched_host=_host(url)
    if not watched_host:
        return None
    rows=_amc_source_pages(amc)
    for row in rows:
        if _host(row.get("url"))==watched_host:
            return row
    return None


def _exact_fetch(url):
    if not url:
        return None
    return db.one(
        """SELECT url,fetched_at,status,hash,detail
           FROM fetches WHERE url=?
           ORDER BY fetched_at DESC,id DESC LIMIT 1""",
        (url,),
    )


def _new_portfolio_document(family, reviewed_at, ignore_urls):
    """Find a newly retained first-party portfolio document after blocker review."""
    if not reviewed_at:
        return None
    ignored={u for u in ignore_urls if u}
    rows=db.rows(
        """SELECT d.title,d.kind,d.url,d.last_seen,v.hash,v.observed_at
           FROM documents d
           LEFT JOIN document_versions v ON v.id=(
             SELECT id FROM document_versions
             WHERE document_id=d.id ORDER BY observed_at DESC,id DESC LIMIT 1)
           WHERE d.family=? AND d.origin='AMC' AND d.kind='portfolio'
             AND COALESCE(v.observed_at,d.last_seen)>?
           ORDER BY COALESCE(v.observed_at,d.last_seen) DESC,d.id DESC""",
        (family,reviewed_at),
    )
    return next((row for row in rows if row.get("url") not in ignored),None)


def _blocked_status(status):
    value=str(status or "").strip().lower()
    return value in {"gap","limited","partial","error","failed","blocked","unavailable"}


def _source_change_watch(family, amc, policy, source_url, recovery_url):
    """Detect retained evidence of a material source/transport change without fetching."""
    reviewed_at=policy.get("reviewed_at")
    mode=policy.get("watch_mode")
    if policy.get("action")!="retry_after_source_change" or not reviewed_at or not recovery_url:
        return None

    exact_fetch=_exact_fetch(recovery_url)
    exact_page=_exact_source_page(recovery_url)
    host_page=_host_source_page(amc,recovery_url) if mode=="host_transport" else None
    new_document=_new_portfolio_document(
        family,reviewed_at,(source_url,recovery_url)
    )
    changed=False;reason=None

    if exact_fetch and exact_fetch.get("fetched_at","")>reviewed_at and exact_fetch.get("status")=="ok":
        changed=True;reason="recovery_url_fetch_succeeded"
    elif exact_page and exact_page.get("last_checked","")>reviewed_at and not _blocked_status(exact_page.get("status")):
        changed=True;reason="recovery_url_source_check_recovered"
    elif (mode=="host_transport" and host_page
          and host_page.get("last_checked","")>reviewed_at
          and not _blocked_status(host_page.get("status"))):
        changed=True;reason="watched_host_transport_recovered"
    elif new_document:
        changed=True;reason="new_first_party_portfolio_document"

    evidence_times=[
        (exact_fetch or {}).get("fetched_at"),
        (exact_page or {}).get("last_checked"),
        (host_page or {}).get("last_checked"),
        (new_document or {}).get("observed_at"),
        (new_document or {}).get("last_seen"),
    ]
    return {
        "reviewed_at":reviewed_at,
        "watch_mode":mode,
        "changed":changed,
        "change_reason":reason,
        "exact_recovery_fetch":exact_fetch,
        "exact_recovery_source_page":exact_page,
        "watched_host_source_page":host_page,
        "new_portfolio_document":new_document,
        "latest_watch_evidence_at":max((x for x in evidence_times if x),default=None),
    }


def _latest_document(family, source_url):
    if not source_url:
        return None
    return db.one(
        """SELECT d.title,d.kind,d.url,d.last_seen,v.hash,v.observed_at
           FROM documents d
           LEFT JOIN document_versions v ON v.id=(
             SELECT id FROM document_versions
             WHERE document_id=d.id ORDER BY observed_at DESC,id DESC LIMIT 1)
           WHERE d.family=? AND d.url=? ORDER BY d.id DESC LIMIT 1""",
        (family, source_url),
    )


def _policy_for(family, limitation):
    if family in _POLICY:
        return dict(_POLICY[family])
    code=(limitation or {}).get("code")
    if code in _ACTION_DEFAULTS:
        return dict(_ACTION_DEFAULTS[code])
    return {
        "action": "investigate_retained_source_evidence",
        "score": 70,
        "actionable_now": True,
        "retry_condition": (
            "Review retained first-party source/fetch evidence and define the exact recovery boundary."
        ),
    }


def _rank_key(item):
    # Actionability dominates. Staleness/missing state break ties; position count never does.
    state_bonus = 2 if item["state"] == "missing" else 1 if item["stale"] else 0
    return (-item["actionability_score"], -state_bonus, item["family"].lower())


def report(today=None):
    """Build the deterministic read-only queue from retained coverage/evidence."""
    today = today or date.today()
    expected = coverage.expected_portfolio_as_of(today)
    current = coverage.report()
    items = []
    for row in current["funds"]:
        portfolio = row.get("portfolio")
        limitation = row.get("portfolio_limitation")
        if portfolio and row.get("portfolio_complete"):
            continue
        if not portfolio and not limitation:
            continue

        stale = bool(portfolio and portfolio["as_of"] < expected)
        state = "missing" if not portfolio else "partial_stale" if stale else "partial_current"
        policy = _policy_for(row["family"], limitation)
        recovery_url = policy.get("recovery_url")
        source_url = (portfolio or {}).get("source") or recovery_url
        if not source_url:
            gap = row.get("portfolio_gap") or {}
            source_url = ((gap.get("document") or {}).get("url")
                          or (gap.get("source_page") or {}).get("url"))
        watched = [source_url, recovery_url]
        fetch = _latest_fetch(watched)
        source_page = _source_page_evidence(row["amc"], watched)
        document = _latest_document(row["family"], (portfolio or {}).get("source"))
        watch = _source_change_watch(
            row["family"],row["amc"],policy,source_url,recovery_url
        )
        if watch and watch["changed"]:
            policy["action"]="review_source_change"
            policy["actionable_now"]=True
            policy["score"]=95
            policy["retry_condition"]=(
                "Review the newly retained first-party source/transport evidence before "
                "retrying portfolio recovery; do not assume the prior blocker is resolved."
            )
        latest_times = [
            (portfolio or {}).get("observed_at"),
            (fetch or {}).get("fetched_at"),
            (source_page or {}).get("last_checked"),
            (document or {}).get("observed_at"),
            (document or {}).get("last_seen"),
        ]
        latest_evidence_at = max((x for x in latest_times if x), default=None)

        items.append({
            "family": row["family"],
            "amc": row["amc"],
            "state": state,
            "stale": stale,
            "reporting_date": (portfolio or {}).get("as_of"),
            "positions": (portfolio or {}).get("positions"),
            "source_url": source_url,
            "recovery_url": recovery_url,
            "limitation": limitation,
            "action": policy["action"],
            "actionable_now": bool(policy["actionable_now"]),
            "actionability_score": int(policy["score"]),
            "retry_condition": policy["retry_condition"],
            "source_change_watch": watch,
            "evidence": {
                "latest_fetch": fetch,
                "latest_source_page_check": source_page,
                "latest_document": document,
                "latest_evidence_at": latest_evidence_at,
            },
        })

    items.sort(key=_rank_key)
    for index,item in enumerate(items,1):
        item["rank"] = index

    next_item = next((x for x in items if x["actionable_now"]), None)
    action_counts = {}
    for item in items:
        action_counts[item["action"]] = action_counts.get(item["action"],0)+1
    return {
        "built_at": db.now(),
        "portfolio_expected_as_of": expected,
        "summary": {
            "items": len(items),
            "actionable_now": sum(x["actionable_now"] for x in items),
            "stale_partial": sum(x["state"]=="partial_stale" for x in items),
            "missing": sum(x["state"]=="missing" for x in items),
            "source_changes_detected": sum(
                bool((x.get("source_change_watch") or {}).get("changed")) for x in items
            ),
            "actions": action_counts,
        },
        "next_recovery_target": (
            {
                "family": next_item["family"],
                "action": next_item["action"],
                "retry_condition": next_item["retry_condition"],
            } if next_item else None
        ),
        "items": items,
        "notes": [
            "Read-only prioritization: generating this queue never fetches sources or mutates portfolio data.",
            "Actionability score determines rank before stale/missing tie-breakers; retained position count is never a ranking input.",
            "retry_after_source_change entries should not be re-probed until source_change_watch.changed becomes true from newly retained first-party evidence.",
            "requires_more_precise_amc_disclosure entries cannot be completed by estimating censored weights.",
            "A changed partial source that no longer matches a reviewed limitation is prioritized for explicit review.",
        ],
    }


def markdown(queue):
    """Render a compact operator handoff without changing the underlying queue."""
    def esc(value):
        return str(value or "").replace("|","\\|").replace("\n"," ")
    def evidence_text(item):
        evidence=item.get("evidence") or {}
        fetch=evidence.get("latest_fetch")
        page=evidence.get("latest_source_page_check")
        parts=[]
        if fetch:
            parts.append(
                f"fetch {esc(fetch.get('status'))} · {esc(fetch.get('fetched_at'))}"
            )
        if page:
            parts.append(
                f"source page {esc(page.get('status'))} · {esc(page.get('last_checked'))}"
            )
        if not parts and evidence.get("latest_evidence_at"):
            parts.append("retained evidence · "+esc(evidence["latest_evidence_at"]))
        return "; ".join(parts) if parts else "No retained timestamped check"

    lines=[
        "# Portfolio recovery queue",
        "",
        f"Prepared: {queue['built_at']}",
        "",
        "**Read-only:** this queue ranks retained evidence only. It does not fetch sources, "
        "retry blocked hosts, estimate missing weights, or mutate portfolio data.",
        "",
    ]
    target=queue.get("next_recovery_target")
    if target:
        lines.extend([
            "## Next actionable recovery target",
            "",
            f"**{esc(target['family'])}** — `{esc(target['action'])}`",
            "",
            esc(target["retry_condition"]),
            "",
        ])
    summary=queue["summary"]
    lines.extend([
        "## Queue",
        "",
        f"Items: **{summary['items']}** · actionable now: **{summary['actionable_now']}** · "
        f"source changes: **{summary.get('source_changes_detected',0)}** · "
        f"stale partial: **{summary['stale_partial']}** · missing: **{summary['missing']}**",
        "",
        "| Rank | Fund | State | Action | Source change | Reporting date | Limitation | Exact source / recovery URL | Last retained evidence | Retry condition |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for item in queue["items"]:
        source=item.get("recovery_url") or item.get("source_url") or "Gap"
        limitation=(item.get("limitation") or {}).get("code") or "none"
        watch=item.get("source_change_watch") or {}
        watch_text=(watch.get("change_reason") if watch.get("changed") else "none")
        lines.append("| "+" | ".join([
            str(item["rank"]),
            esc(item["family"]),
            esc(item["state"]),
            esc(item["action"]),
            esc(watch_text),
            esc(item.get("reporting_date") or "Gap"),
            esc(limitation),
            esc(source),
            evidence_text(item),
            esc(item["retry_condition"]),
        ])+" |")
    lines.extend(["","## Notes",""])
    for note in queue.get("notes",[]):lines.append("- "+esc(note))
    lines.append("")
    return "\n".join(lines)
