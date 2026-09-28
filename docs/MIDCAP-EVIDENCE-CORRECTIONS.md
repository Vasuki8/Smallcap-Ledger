# Mid Cap evidence corrections

This log distinguishes parser corrections from publisher changes. It is not a record of fund trades. Mid Cap remains staged; none of the corrections below authorizes public export.

## Mahindra issuer/sector separation — PR #285

### Original retained evidence

- Fund: **Mahindra Manulife Mid Cap Fund**.
- Reporting date: **2026-08-31**.
- Official source: https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html
- Source SHA-256: `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`.
- Previous audit: `docs/MIDCAP-PORTFOLIO-BATCH5.json` at commit `f9d2a1c819ad6597c06571e63c169762b4e82914`, produced after PR #284.
- Previous `positions_observed`: **63**, with `complete=false`.

The previous corporate-keyword heuristic incorrectly classified these four published sector headings as securities:

| Non-security row | Publisher's sector weight (%) |
| --- | ---: |
| Consumer Services | 0.85 |
| Healthcare | 9.70 |
| Power | 1.90 |
| Services | 2.67 |

These values are sector aggregates, not additional positions. They must not be added to the weights of their underlying named issuers. Removing them is a classification correction, not a sale or a change in the AMC's portfolio.

### Corrected interpretation

PR #285 introduces `tracker/midcap_factsheet_validation.py`, parser version `mahindra-midcap-issuer-rows-v1`:

- Read only the exact **Company / Issuer** and **% of Net Assets** portfolio columns.
- Exclude the published sector and total labels while retaining actual company names containing words such as Healthcare, Power or Services.
- Require a named issuer and an explicitly reported, finite numeric weight. Missing values are not zero.
- Reject unknown row shapes, duplicate issuers and conflicting responsive copies rather than silently merging them.
- Preserve source URL, content hash, reporting date and parser version in the regenerated batch evidence.
- Keep the named-issuer view **partial**. Excluding sector totals does not prove a complete cash-inclusive portfolio.

The original audit remains accessible in Git history. The regenerated report, not this correction log, is authoritative for the current accepted issuer count and current source hash.

### Regression evidence

The PR regression workflow passed **564 tests**, including **22 new parser/integration tests**, before merge. Verification run: https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36376275507 .

The production refresh for merge commit `240176139b40abce7cf7710f9ea7a09b17f91d9f` is tracked separately in workflow run https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36376355823 . Consult `MIDCAP-HANDOFF.md` for the verified terminal result.

## Sundaram date-field interpretation — PR #285

`AUMASONDATE` is a plain date field in the official Sundaram fund-card JSON, not an entire document containing an `as on` sentence. The collector now first uses the existing `report_parser.dated` function for this field.

This is only source discovery metadata. The downloaded portfolio must independently pass exact-family and current-reporting-date validation. A current AUM date cannot make an older portfolio current. A PDF remains an explicit parser gap until an appropriate source-specific extractor is verified; it is not parsed as HTML.
