# Smallcap Ledger backend handoff

Updated: 2026-09-24. Repository, live coverage, Actions and cumulative history override older summaries.

## SBI monthly portfolio recovery

This batch adds first-party SBI monthly portfolio discovery, independent of guessed factsheet filenames. The public SBI Portfolios.js uses `POST /ajaxcall/CMS/GetSchemePortfolioSheets` with `FundId: 0`, `PSYear`, `PSMonth` and `PSFrequency: Monthly`. Discovery checks only the latest two closed calendar months and accepts the exact SBI Small Cap Fund monthly workbook title. Passive Smallcap index funds/ETFs, mismatched periods, non-workbooks and unregistered hosts are rejected.

The verified August and July workbooks both contain an explicit `Margin amount for Derivative positions` leaf row. That exact SBI label is recognized as cash/margin. No residual holding is inferred. Completeness still requires the workbook's actual values, weights and grand total to reconcile, with no unknown or duplicate positions.

Source-byte validation before production:

| Reporting date | Positions | Completeness | Weight sum | SHA-256 |
| --- | ---: | --- | ---: | --- |
| 2026-08-31 | 73 | Complete | 100.00% | `71b589984c9b3db4bbb1baf7365072e0e6f604cf18ccfc215a1dc9c1d3183b48` |
| 2026-07-31 | 74 | Complete | 100.00% | `b080c169962567f08b34dc4117368dcfb0fe4e49c182a2f60da842682e6dd1c1` |

Exact source URLs:
- August: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---august-2026.xlsx?sfvrsn=9c20b052_2
- July: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---july-2026.xlsx?sfvrsn=e69601db_2

`tracker/sbi_portfolios.py` handles source discovery. `amc_discovery` includes SBI in nightly collection. `scripts/refresh_sbi_portfolios.py` performs a one-time push upgrade, marked complete only after successful collection and a current complete portfolio. Source failure retains old observations and a retryable upgrade state. Extraction version `sbi-monthly-portfolio-v1` preserves older extraction audit rows and does not supersede the separate Quant upgrade.

Eight new regression tests cover listing identity/date/host filtering, bounded month/year rollover, nightly wiring, explicit margin and negative receivables, reconciliation failure cases, scoped cache replay, and retry/idempotency behavior. Two real downloaded official workbooks also passed local end-to-end ingestion. The locked GitHub runner release checks and production deployment are still to be verified; do not treat these source-byte results as a published coverage change yet.

## Continuation rules and queue

Do backend/data work only unless UI changes are requested. Do not duplicate the concurrently advancing Quant recovery: re-read current main, coverage and its latest Actions results. Once SBI is published, choose the next fresh-partial portfolio with a genuinely accessible structured first-party source. Bajaj remains the established source-access blocker; Bandhan and Union remain the known zero-portfolio discovery/access gaps until production evidence changes. Preserve every source URL/hash/report date, financial units, nulls, conflicts and original archive bytes. Never label partial holdings complete merely to improve coverage counts.
