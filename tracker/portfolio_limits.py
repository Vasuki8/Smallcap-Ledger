"""Canonical machine-readable reasons why a portfolio snapshot is partial or missing.

These classifications never create or estimate holdings. Retained-snapshot reasons are
assigned only when the fund and exact first-party source family match evidence already
validated by the tracker. Unknown partials remain explicitly unclassified.
"""
from __future__ import annotations

from urllib.parse import urlparse

KNOWN_CODES = frozenset({
    "undisclosed_constituents",
    "named_holdings_only",
    "non_numeric_weight",
    "upstream_transport_unavailable",
    "source_not_exposing_portfolio",
    "unsupported_source_layout",
    "partial_unclassified",
})


def _host_path(source):
    parsed = urlparse(str(source or ""))
    return (parsed.hostname or "").lower(), parsed.path.lower()


def retained_limitation(family, source, complete):
    """Return a canonical limitation for one retained snapshot, or None if complete."""
    if complete:
        return None
    host, path = _host_path(source)

    if family == "ICICI Prudential Small Cap Fund":
        if host.endswith("icicipruamc.com") and path.endswith("/blob/knowledgecentre/factsheet-complete/complete.pdf"):
            return {
                "code": "undisclosed_constituents",
                "detail": "AMC factsheet leaves part of equity exposure in an aggregate for constituents below the disclosure threshold.",
            }

    if family == "Axis Small Cap Fund":
        if host.endswith("axismf.com") and (
            "/axis-small-cap-fund/" in path
            or "/efactsheet/" in path
            or path.endswith("/small-cap.html")
        ):
            return {
                "code": "undisclosed_constituents",
                "detail": "AMC disclosure does not identify every constituent behind its thresholded/aggregate equity exposure.",
            }

    if family == "Edelweiss Small Cap Fund":
        if host.endswith("edelweissmf.com") and "factsheet" in path:
            return {
                "code": "named_holdings_only",
                "detail": "AMC factsheet publishes only a named/top-holdings subset for this retained snapshot.",
            }

    if family == "Bajaj Finserv Small Cap Fund":
        if host.endswith("bajajamc.com") and path.endswith(".pdf"):
            return {
                "code": "named_holdings_only",
                "detail": "AMC factsheet publishes only a named/top-holdings subset for this retained snapshot.",
            }

    if family == "Bandhan Small Cap Fund":
        if host == "storage.googleapis.com" and path.startswith("/nonprod-static-assets-121to59kaawfgfi7bol/"):
            return {
                "code": "non_numeric_weight",
                "detail": "AMC workbook contains one or more holdings whose NAV weight is disclosed only with a non-numeric threshold marker.",
            }

    if family == "Sundaram Small Cap Fund":
        if host.endswith("sundarammutual.com") and path.endswith("/smile.xlsx"):
            return {
                "code": "non_numeric_weight",
                "detail": "AMC workbook contains a holding whose NAV weight is disclosed only as less than 0.01%.",
            }

    if family == "UTI Small Cap Fund":
        if host.endswith("cloudfront.net") and path.endswith(".zip"):
            return {
                "code": "non_numeric_weight",
                "detail": "AMC exposure file contains one or more positions or short-term deposits without an exact numeric NAV weight.",
            }

    return {
        "code": "partial_unclassified",
        "detail": "Snapshot is partial, but no source-specific limitation classification has been established.",
    }


def missing_limitation(gap):
    """Classify a no-portfolio coverage gap from retained source/audit evidence."""
    if not gap:
        return None
    source_page = gap.get("source_page") or {}
    reason = str(gap.get("reason") or "")
    if source_page.get("status") == "Gap" or reason == "source_unavailable":
        detail = str(source_page.get("detail") or "").strip()
        return {
            "code": "upstream_transport_unavailable",
            "detail": ("First-party source transport is unavailable"
                       + (": " + detail if detail else ".")),
        }
    if reason in {"source_not_exposing_portfolio", "no_portfolio_document",
                  "facts_only_no_portfolio", "no_holdings_extracted"}:
        return {
            "code": "source_not_exposing_portfolio",
            "detail": "Retained first-party source evidence does not expose a usable portfolio constituent table.",
        }
    if reason in {"unsupported_document_layout", "document_not_parsed", "extraction_error"}:
        return {
            "code": "unsupported_source_layout",
            "detail": "A first-party document exists, but the retained evidence is not currently supported as an unambiguous portfolio table.",
        }
    if reason == "document_not_archived" and source_page.get("status") == "Gap":
        return {
            "code": "upstream_transport_unavailable",
            "detail": "First-party source transport is unavailable.",
        }
    return None


def validate_limitation(code, detail, complete):
    """Validate caller-supplied storage values without relaxing completeness rules."""
    if complete:
        if code is not None or detail is not None:
            raise ValueError("Complete portfolio cannot carry a partial limitation")
        return
    if code not in KNOWN_CODES:
        raise ValueError("Unknown portfolio limitation code")
    if not str(detail or "").strip():
        raise ValueError("Partial portfolio limitation detail is required")
