# Smallcap Ledger backend handoff

Updated: 2026-09-24, after production deployment. Read this file, README.md, current COVERAGE-AS-OF.json and the latest Actions/deployment state before continuing. This handoff supersedes the older Quant/SBI backlog paragraphs retained in README.md. Live repository and source evidence override summaries.

## Latest completed task: SBI monthly portfolio recovery

Merged PR #86 as commit `12307fefd86bce92f34b5c56d6f47302acd5cc03`. Production workflow **#456**, run **35965260621**, successfully built, validated, saved cumulative history and deployed GitHub Pages. Deployment completed **2026-09-24T06:37:13Z**. The published coverage was built at **2026-09-24T06:36:16Z**.

Before this batch, SBI's latest portfolio was a **68-position partial snapshot dated 2026-07-31**. It is now a **73-position complete snapshot dated 2026-08-31**, with the **74-position complete July workbook** retained as its prior-month comparator. Both workbooks reconcile to 100.00% using explicitly disclosed rows, actual values and the stated grand total. No balancing holding was invented.

| Reporting date | Positions | Completeness | Weight sum | SHA-256 |
| --- | ---: | --- | ---: | --- |
| 2026-08-31 | 73 | Complete | 100.00% | `71b589984c9b3db4bbb1baf7365072e0e6f604cf18ccfc215a1dc9c1d3183b48` |
| 2026-07-31 | 74 | Complete | 100.00% | `b080c169962567f08b34dc4117368dcfb0fe4e49c182a2f60da842682e6dd1c1` |

Exact official sources:
- August: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---august-2026.xlsx?sfvrsn=9c20b052_2
- July: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---july-2026.xlsx?sfvrsn=e69601db_2

## Implementation and safety boundaries

`tracker/sbi_portfolios.py` uses the public endpoint called by SBI's Portfolios.js: `POST https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets`, with `FundId: 0`, `PSYear`, `PSMonth` and `PSFrequency: Monthly`. It checks only the latest two closed calendar months. It accepts the exact SBI Small Cap Fund monthly workbook title and rejects passive Smallcap index funds/ETFs, mismatched periods, non-workbooks and unregistered hosts. The separate recent-portfolios endpoint returned a server error; do not revert to it or guess attachment filenames.

The verified workbooks contain the exact leaf `Margin amount for Derivative positions`. The parser now recognizes that explicit SBI row as cash/margin. Unknown rows, duplicate holdings, and value/weight mismatches still prevent completeness. Negative receivables are retained; supplementary derivative turnover after the grand total is not added to portfolio assets.

`amc_discovery` includes SBI in normal nightly collection. `scripts/refresh_sbi_portfolios.py` runs a one-time push recovery, with setting `source_upgrade_sbi-monthly-portfolio-v1`. It is marked complete only after successful collection and a current complete portfolio. Failure preserves prior data and a retryable state. The source-scoped extraction key `sbi-monthly-portfolio-v1` retains older extraction audit rows without superseding the independent Quant upgrade. Future scheduled collection remains active after the one-time key is set.

The existing daily schedule remains **18:30 UTC / midnight Asia/Kolkata**. No UI, dependency, permission, paid-service or archive-retention changes were made.

## Validation and publication evidence

Eight new regression tests cover exact source identity/period/host filtering, two-month/year rollover, nightly integration, explicit margin and negative receivables, reconciliation failure cases, source-scoped replay, and retry/idempotency behavior. **All 188 tests passed** with locked dependencies in successful validation run **35965069569**; both real official workbooks also passed live end-to-end ingestion and an idempotent second invocation. Production run #456 passed its full regression gate, generated-site/download validation, cumulative-history save and Pages deployment.

The exact deployed Pages artifact was downloaded and independently checked: artifact **10794395282**, ZIP SHA-256 `db97a0e8916c008381d98654231ac9b610c1dc296d51a8b3721b11833cf89ec8`. It contains SBI snapshot **243** (August, 73 positions, complete, 100.00%) and prior snapshot **244** (July, 74 positions, complete), with the official source hashes above. The August payload has **69 reported equity quantities with prior-month/share-change values**. Its CSV export has 73 rows and the comparison columns. All SBI plan/option entries use the current complete family portfolio.

Verification boundary: the successful Pages deployment and the exact published artifact/data/CSV were verified. Direct HTTP/browser inspection of the public Pages URL was unavailable through this environment's web tool; do not claim a visual browser check was performed. Temporary investigation workflow and encoded patch transport were removed before merge. An initial runner push was rejected for workflow-write permissions after its tests had passed; publication was completed using the authorized connector for workflow edits, without changing permissions or credentials.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/86 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965069569 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965260621 . This final handoff-only commit intentionally skips CI; it does not change deployed code or data.

## Verified coverage after this batch

Coverage at 2026-09-24T06:36:16Z: **36 funds; 143 NAV series; 281,300 NAV observations; latest NAV 2026-09-23**. AUM, a dated Direct fee figure and reported benchmark identity each have **36/36** coverage. These are coverage counts, not a claim that every metric has the latest reporting date or that every fee is TER.

Portfolios: **34/36 with holdings; 24 complete; 33 current; 24 current and complete; 10 partial**. The expected month-end is **2026-08-31**. SBI alone improved complete portfolios **23 -> 24** and current portfolios **32 -> 33** relative to the immediately preceding published build. Quant had already been repaired by the separate workstream to **120 complete positions dated 2026-08-31**; do not repeat or attribute that repair to this SBI batch.

## Next backend task and remaining blockers

1. **Axis Small Cap Fund: investigate its official complete monthly workbook/disclosure source next.** Current coverage is only 10 positions, dated 2026-09-16 and explicitly partial. Recover a full, explicitly dated and reconciled portfolio rather than promoting the top-holdings list. Re-read source state before work; do not infer a month-end from an observation date.
2. Other current partial portfolios remain **Edelweiss, ICICI Prudential, Invesco India, JM, Sundaram, Tata, TRUSTMF and UTI**, all currently dated 2026-08-31. Prefer reusable exact first-party structured discovery over one-off filename guesses.
3. **Bajaj Finserv** is now the only stale portfolio: 13 partial positions dated 2026-07-31. Its established official-source access blocker remains. Retry only with a genuinely new first-party route or changed access evidence.
4. **Bandhan and Union** remain the two zero-portfolio gaps (`document_not_archived`). Bandhan requires an obtainable official attachment/API route; Union remains an official-host transport blocker, not a reason to weaken its tested parser.

Continue backend/data work only unless UI changes are explicitly requested. Preserve exact source URL/hash/report date, units, nulls, conflicts and original archive bytes. Retain the current plus immediately previous calendar-month holdings window and cumulative original evidence. Never mark partial holdings complete to improve counts. Do not rerun completed SBI/Quant repair work or a broad historical reparse unnecessarily. Update this handoff after the next completed batch.
