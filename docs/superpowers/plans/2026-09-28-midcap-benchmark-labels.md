# Mid Cap primary benchmark label recovery

## Scope and approved continuation
Continue the existing benchmark audit after the Samco repair already merged in PR #293. Do not reimplement the freshness or Samco tasks from the older handoff. Base: `68774e67c80d5373d36216cc885f7ad841caef4d`.

Bounded approach: extend existing benchmark batch 2 with Axis and Mirae fund-specific HTML contracts. Do not add another producing artifact: the existing 14-input launch-integrity contract remains unchanged. Keep public export disabled, thresholds unchanged, and actual benchmark series availability separate from reported identity.

## Observed source contracts
Isolated read-only diagnostic run `36426086431`, job `108940266495` inspected four official pages with database access forbidden and `archive=False`.

- Axis: exact H1 `Axis Mid Cap Fund`; primary banner `Benchmark Returns` / `BSE Midcap 150 TRI`; explicitly labeled percentage and rupee performance columns agree. `Nifty 50 TRI` is an additional comparator, not primary. Response SHA-256 `9173f7a0ebb2f48d1777fd5f9fd94d7f849526d64b3e395da25112974691c7b7`.
- Mirae: exact H1 `Mirae Asset Midcap Fund`; `div.fund_fact_text` pairs `benchmark index` with `NIFTY Midcap 150 (TRI)`. Response SHA-256 `06163cec57d3111a57bdc4922a573987056acba795fb84b5ad46af62199c1d0d`.
- ABSL's discovered empower factsheet is older; no new coverage claim from it in this slice. Invesco's returned page lacked usable scheme/benchmark HTML; it is not counted or replaced with a category default.
- The diagnostic branch/workflow is throwaway evidence, not included in the production branch.

## Implementation and validation ledger
- [x] Write 23 parser/source-boundary tests; observe failures before the new parser exists.
- [x] Implement exact heading plus source-specific label parsing. Preserve publisher wording, role, source URL/hash, observation time and the original evidence excerpt. Do not infer TRI or take benchmark effective dates from NAV/AUM/performance timestamps.
- [x] Write seven integration/provenance tests against unchanged batch/readiness functions; observe seven failures, then wire the two sources into batch 2 and retain independent copies of source evidence.
- [x] Run all 30 focused tests and syntax checks locally. Original batch/readiness modules were blob-hash verified before modification. The local tree uses dependency shims only for legacy transport/database boundaries; it is NOT the full repository suite and the shims are not uploaded.
- [x] Run full GitHub regression and actual two-source preflight before merge.
- [x] Verify exact production reports and deployment after merge; update the focused handoff with current counts, failures and next task.

Ruling: require primary Axis banner/table agreement and both primary column roles, rather than select the first nearby index. Fail closed on conflicting responsive copies or changed source structure. The registered pages have no explicit benchmark effective date, so that field stays null; Axis performance reporting date is retained separately.

Ruling: decode these registered UTF-8 responses explicitly. A synthetic rupee-label fixture exposed BeautifulSoup's otherwise incorrect windows-1252 auto-detection; strict UTF-8 preserves the actual Benchmark(₹) role and rejects malformed encoding.

Ruling: preserve all existing legacy benchmark readers and source records in this bounded extension; do not claim the new fund-specific parser retrospectively revalidated every older benchmark. No public UI, live Mid Cap record, source permission or dependency changes.

## Verified pre-merge and integration checkpoint

PR #294 merged as `f64ce9e8c8ac07f793a9a0820990e2fbf7550adb` from exact tested head `a7ff8732ff60517b6f8f8f157993474d77f47f1e`. Branch verification [36427288099](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427288099), job 108944267193, passed syntax and **687 full repository tests** (`Ran 687 tests in 12.350s` / `OK`), then recovered **both** registered sources with no preflight errors and database access forbidden. The benchmark identity is not a verified time series.

Both [PR regression 36427676746](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427676746) and [Research UI checks 36427676753](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427676753) passed before merge. The unrelated batch-5 and Samco live preflights were skipped on this benchmark branch, not silently claimed. Final diff review confirmed eight intended files and no temporary diagnostic workflow, local dependency shim, daily publisher change or public UI change.

The final local rerun passed all 30 focused tests; extra boundary checks rejected a future Axis performance date and preserved unspecified/PRI/TRI distinctions without inventing effective dates. Full repository results come from CI, not the dependency-shim scratch tree.

## Verified production checkpoint

Production [#649 / 36427820049](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427820049) passed build and deployment. Deploy job 108949383232 completed at **2026-09-28T13:30:11Z**. Refreshed artifacts were read at `c516a97799bbb3005ca407477bd417ff5bea399a`; benchmark batch 2 was generated at 13:22:55 UTC and the launch report evaluated at 13:24:35.217505 UTC.

Both new sources recovered in the actual production batch: Axis `BSE Midcap 150 TRI` with additional `Nifty 50 TRI`, Mirae `NIFTY Midcap 150 (TRI)`. The combined benchmark report now counts **14/34** and retains the source hashes/excerpts/roles. Current production source SHA-256: Axis `36609a27cdcbb819b30442671b6d79e8c41a52865b28451b3bfa4ea5b12bfa72`; Mirae `06163cec57d3111a57bdc4922a573987056acba795fb84b5ad46af62199c1d0d`. No effective date or verified time series is inferred. Batch 2 recovered 6/7 including the four unchanged successful legacy sources; JM still fails the exact-family page gate.

All 14 launch input checks passed with no integrity issues. NAV remains 135/135, AUM 34/34 and TER 31/34. The actual current portfolio result is **15/34, 3 complete**, not the preceding 16/34 and four complete: Invesco's monthly-holdings API returned HTTP 502 in this run, so its earlier evidence is not passed off as a fresh recovery. The benchmark patch changed no portfolio source logic. The handoff records the exact failure and next recheck rather than assert a permanent outage or fabricate coverage.

Mid Cap remains staged/non-public; data and launch readiness remain false. Seventeen additional benchmark identities and thirteen current portfolio families are needed under unchanged thresholds, then the separate category-aware exporter/API/UI dry run. Public browser access was unavailable in this environment; no fresh visual/mobile pass is claimed.
