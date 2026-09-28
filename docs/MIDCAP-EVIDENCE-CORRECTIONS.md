# Mid Cap evidence corrections

This log distinguishes parser corrections from publisher changes. It is not a record of fund trades. Mid Cap remains staged; none of the corrections below authorizes public export.

## Mahindra issuer/sector separation — PRs #285 and #286

### Original retained audit

- Fund: **Mahindra Manulife Mid Cap Fund**.
- Reporting date: **2026-08-31**.
- Official source: https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html
- Source SHA-256: `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`.
- Original report: `docs/MIDCAP-PORTFOLIO-BATCH5.json` at commit `f9d2a1c819ad6597c06571e63c169762b4e82914`, produced after PR #284.
- Original `positions_observed`: **63**, with `complete=false`.

The corporate-keyword heuristic incorrectly classified four published sector headings as securities:

| Non-security row | Publisher's sector weight (%) |
| --- | ---: |
| Consumer Services | 0.85 |
| Healthcare | 9.70 |
| Power | 1.90 |
| Services | 2.67 |

These are sector aggregates, not additional holdings. They must not be added to their underlying issuer weights. Removing them is a classification correction, not a sale or a change in the AMC's portfolio. The original report remains accessible in Git history.

### Corrected interpretation

PR #285 introduces a pure validator in `tracker/midcap_factsheet_validation.py`:

- Read only the exact **Company / Issuer** and **% of Net Assets** columns.
- Exclude published sector and total labels while retaining actual company names containing words such as Healthcare, Power or Services.
- Require a named issuer and an explicitly reported, finite numeric weight. Missing values are not zero.
- Reject unknown row shapes, duplicate issuers and conflicting responsive copies rather than silently combining them.
- Preserve source URL, source hash, reporting date and parser version in the regenerated batch evidence.
- Keep this named-issuer view **partial**; cash is not part of the accepted issuer list.

The initial strict parser withheld Mahindra coverage because the real table contains an additional one-cell footer after Grand Total. Production run #644 completed successfully, but its Mahindra result remained an explicit parser error. That was not a recovered portfolio and must not be reported as one.

### Observed footer and verified recovery

Read-only source probe [36377130226](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377130226) identified the actual row: a colspan legend reading `( Top Ten Holdings - Issuer wise) as on August 31, 2026`, after **Grand Total 100.00%**. It explains a visual issuer marker; it is not an extra financial row or a requirement to truncate the portfolio to ten holdings.

PR #286, parser version **`mahindra-midcap-issuer-rows-v2`**, accepts only that exact legend shape after an explicitly verified 100% Grand Total. Unknown footer text, a footer before the total, a non-100% total, or financial rows after the total still fail closed. All prior issuer, sector, weight and duplicate checks remain.

A second first-party probe, [36377288373](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377288373), verified the same source hash and returned **59 genuine issuers**, totaling **97.71%** of net assets. This matches the AMC's stated equity total; its separately reported cash/receivables are **2.29%**. The result remains partial because it is an issuer-only view, not a full cash-inclusive portfolio record.

The source probe is now **manual-only**, with read-only repository permissions and no database or publication writes. It does not run on ordinary pushes or scheduled updates.

### Regression and publication evidence

- PR #285: **564 tests passed before merge**, including 22 new parser/integration tests, in [36376275507](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36376275507).
- PR #286: **570 tests passed before merge**, including six additional footer regressions, in [36377345548](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377345548).
- PR #286 merge: `399dc73a01a53b7317fd5493e141792332ccb24a`.
- Its production publication run is [#645 / 36377452770](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377452770). Consult [MIDCAP-HANDOFF.md](MIDCAP-HANDOFF.md) for the verified terminal result and regenerated readiness counts.

The current generated batch report is authoritative for the accepted issuer count, observation time and source hash. Do not turn this historical correction note into current coverage when the reporting month changes.

## Sundaram date-field interpretation — PR #285

`AUMASONDATE` is a plain date field in the official Sundaram fund-card JSON, not a document containing an `as on` sentence. The collector now first uses the existing `report_parser.dated` function for this field.

In production run #644 the date resolved to **2026-07-31**, older than the required **2026-08-31**. Sundaram therefore remained a stale-source gap; this code change did not recover its current portfolio.

This field is only discovery metadata. Any downloaded portfolio must independently prove its own exact family and reporting date. A current AUM date cannot make an older portfolio current. A PDF is an explicit unsupported-parser case until an appropriate extractor is verified, never an HTML portfolio by assumption.
