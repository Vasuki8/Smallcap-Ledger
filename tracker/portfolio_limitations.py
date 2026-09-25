"""Machine-readable reasons why a retained or missing portfolio is incomplete.

These are evidence classifications, not estimates. They never change holdings,
weights, dates, or the existing `complete` flag.
"""
from __future__ import annotations

# Current verified partial-source boundaries.  Source anchors deliberately keep a
# future source change from inheriting an old limitation without review.
_PARTIAL = {
    "Axis Small Cap Fund": {
        "source_contains": "axismf.com/mutual-funds/equity-funds/axis-small-cap-fund",
        "code": "undisclosed_constituents",
        "kind": "source_aggregate",
        "basis": "related_first_party_disclosure",
        "source_marker": "Other Domestic Equity (Less than 0.50% of the corpus)",
        "detail": "The AMC disclosure aggregates undisclosed smaller equity constituents, so exact names and weights are not available.",
    },
    "Bajaj Finserv Small Cap Fund": {
        "source_contains": "media.bajajamc.com/",
        "code": "named_subset_only",
        "kind": "source_subset",
        "basis": "first_party_factsheet",
        "source_marker": "Name (Top 10 Holdings) / Other Equities",
        "detail": "The retained factsheet names only a subset of holdings and aggregates the remaining equities.",
    },
    "Bandhan Small Cap Fund": {
        "source_contains": "bandhan-small-cap-fund-31-august-2026.xlsx",
        "code": "non_numeric_source_weight",
        "kind": "source_precision",
        "basis": "first_party_workbook",
        "source_marker": "$ = Less Than 0.01% of NAV",
        "detail": "The AMC workbook publishes one or more security weights only as less than 0.01% of NAV; no numeric estimate is stored.",
    },
    "Edelweiss Small Cap Fund": {
        "source_contains": "Edelweiss_Factsheet_September_2026",
        "code": "named_subset_only",
        "kind": "source_subset",
        "basis": "first_party_factsheet",
        "source_marker": "Top 10 Holdings / Top 10 stocks: 23.00%",
        "detail": "The current AMC factsheet publishes only the Top 10 named holdings, not the full constituent portfolio.",
    },
    "ICICI Prudential Small Cap Fund": {
        "source_contains": "icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf",
        "code": "undisclosed_constituents",
        "kind": "source_aggregate",
        "basis": "first_party_factsheet",
        "source_marker": "Equity less than 1% of corpus",
        "detail": "The AMC factsheet separately aggregates equity below 1% of corpus, so those constituent names and exact weights are undisclosed.",
    },
    "Sundaram Small Cap Fund": {
        "source_contains": "Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx",
        "code": "non_numeric_source_weight",
        "kind": "source_precision",
        "basis": "first_party_workbook",
        "source_marker": "# percentage to NAV of security is less than 0.01%",
        "detail": "The AMC workbook publishes a written-off holding with a less-than-0.01% marker rather than an exact numeric weight.",
    },
    "UTI Small Cap Fund": {
        "source_contains": "fw_uti_mf_scheme_portfolios_31.08.2026",
        "code": "non_numeric_source_weight",
        "kind": "source_precision",
        "basis": "first_party_workbook",
        "source_marker": "* / SHORT TERM DEPOSITS without exact % TO NAV",
        "detail": "The AMC source censors at least one tiny security weight and omits an exact NAV percentage for short-term deposits.",
    },
}

_MISSING = {
    "Union Small Cap Fund": {
        "code": "upstream_source_unavailable",
        "kind": "upstream_transport",
        "basis": "first_party_transport",
        "source_marker": "Official Downloads routes refuse the production runner connection",
        "detail": "No retained portfolio exists because the AMC portfolio transport is unavailable from the production collection network.",
    },
}

_GAP_CODES = {
    "source_unavailable": ("upstream_source_unavailable", "upstream_transport"),
    "source_not_exposing_portfolio": ("source_not_exposing_portfolio", "upstream_source"),
    "no_portfolio_document": ("no_portfolio_document", "upstream_source"),
    "no_official_document": ("no_official_portfolio_document", "upstream_source"),
    "document_not_archived": ("portfolio_document_not_archived", "collection"),
    "extraction_error": ("portfolio_extraction_error", "parser"),
    "unsupported_document_layout": ("unsupported_portfolio_layout", "parser"),
    "facts_only_no_portfolio": ("document_contains_no_supported_portfolio", "parser"),
    "document_not_parsed": ("portfolio_document_not_parsed", "parser"),
    "no_holdings_extracted": ("no_holdings_extracted", "parser"),
}


def _with_scope(value, scope):
    out={k:v for k,v in value.items() if k!="source_contains"}
    out["scope"]=scope
    return out


def portfolio_limitation(family, portfolio=None, gap=None):
    """Return a stable evidence classification, or None for a complete snapshot."""
    if portfolio:
        if bool(portfolio.get("complete")):
            return None
        rule=_PARTIAL.get(family)
        source=str(portfolio.get("source") or "")
        if rule and rule["source_contains"] in source:
            return _with_scope(rule, "partial_portfolio")
        return {
            "code": "partial_reason_unclassified",
            "kind": "unclassified",
            "basis": "retained_partial_snapshot",
            "source_marker": None,
            "detail": "The retained snapshot is partial, but no verified limitation rule matches this exact source.",
            "scope": "partial_portfolio",
        }

    if family in _MISSING:
        return _with_scope(_MISSING[family], "missing_portfolio")

    reason=(gap or {}).get("reason")
    if reason in _GAP_CODES:
        code,kind=_GAP_CODES[reason]
        return {
            "code": code,
            "kind": kind,
            "basis": "coverage_gap_audit",
            "source_marker": reason,
            "detail": "No retained portfolio is available; see portfolio_gap for the underlying collection evidence.",
            "scope": "missing_portfolio",
        }
    return None
