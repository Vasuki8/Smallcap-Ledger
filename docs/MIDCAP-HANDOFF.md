# Mid Cap backend handoff

Use this handoff with the latest generated reports and the exact code/workflow checkpoint. An older successful audit, a source preflight, or a newly generated summary is not proof that the latest individual source collection passed. Mid Cap is still non-public.

## Latest verified checkpoint

- Latest code: **PR #294**, exact primary benchmark-label recovery for Axis and Mirae. Merge: `f64ce9e8c8ac07f793a9a0820990e2fbf7550adb`. The existing Samco repair in **PR #293** and freshness safeguards in **PR #290** are preserved; do not repeat those completed tasks from an older handoff.
- Tested head: `a7ff8732ff60517b6f8f8f157993474d77f47f1e`. [Branch verification 36427288099](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427288099) passed syntax, **687 full repository tests**, and the actual two-source preflight. Job 108944267193 logged `Ran 687 tests in 12.350s` / `OK`. This adds 30 tests beyond main's 657-test Samco checkpoint.
- Both [PR regression 36427676746](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427676746) and [Research UI checks 36427676753](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427676753) passed before merge. Unrelated batch-5 and Samco source preflights were not rerun for this benchmark branch.
- Production: [run #649 / 36427820049](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36427820049), **build and deploy completed successfully on 2026-09-28**. Build job 108946047304 passed all staged audit steps, repository regressions, generated-site validation, archive publication and status recording. Deploy job 108949383232 completed successfully at **13:30:11 UTC**. The individual Invesco portfolio source failed as documented below; overall workflow success does not erase that gap.
- Refreshed evidence commit: `c516a97799bbb3005ca407477bd417ff5bea399a`. Benchmark batch 2 built at **2026-09-28T13:22:55+00:00**; launch evaluated at **2026-09-28T13:24:35.217505+00:00**. Portfolio reporting month-end: **2026-08-31**. Original source observations and hashes remain separate from report generation and deployment times.
- Latest input integrity: **14/14 required input checks passed; `input_issues=[]` and `audit_input_integrity=true`**. A successful artifact-generation or deployment check does not mean every fund source is covered.

Verification scope: 30 focused local red-to-green tests, final source/diff review, full repository CI, actual read-only Axis/Mirae responses, and the exact production reports and terminal deployment above. The local scratch tests used dependency shims only at legacy/database boundaries; those shims are not in the repository and the local set is not the full suite. No new browser-level visual/mobile pass is claimed. No public UI or Mid Cap publication switch changed.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | 14 / 34 | At least 31 / 34 |
| Current portfolio evidence | 15 / 34 | At least 28 / 34 |
| Complete current portfolios | 3 / 34 | Separate measure; never relabel partials |

The two new benchmark identities are accepted in production: batch 2 recovered **6/7** targets, with the existing JM exact-page identity failure remaining explicit. Combined benchmark coverage increased from 12 to **14/34**. Samco's prior repair remains effective and TER coverage is **31/34**.

**Do not repeat the earlier 16/34 portfolio and 4/34 complete counts as current.** In this run Invesco's official `api/CompleteMonthlyHoldings?year=2026&classification=equity` endpoint returned **502 Bad Gateway**; batch 5 recovered JM, Mahindra and Sundaram (3/5) and also retained Kotak's exact-heading failure. Current portfolio evidence is **15/34**, with **HDFC, Mirae Asset and Sundaram** the three complete portfolios. All accepted current rows report August 31. The older Invesco 43-position complete snapshot remains historical evidence, not a successful current-run observation. #294 changes no portfolio collector; no root cause beyond the observed upstream HTTP response or permanent outage is claimed.

The launch report remains **`data_ready=false`**, **`launch_ready=false`**, and **`public_export_enabled=false`**. The numerical deficits are **17 reported benchmark identities** and **13 current portfolio-evidence families**; AUM/NAV/TER gates pass. The separate category-aware public-surface dry run is still required after those data gates pass. These are tracker product-quality thresholds, not regulatory rules. Counts and benchmark names alone do not establish available comparison series or exportable holdings/metrics.

## Completed: two additional explicit primary benchmark sources

PR #294 extends **existing benchmark batch 2**, not a new producing batch. Daily artifact paths and the existing **14-file input-integrity contract** are unchanged. Only the new registrations use the stricter fund-specific label parser; legacy readers are preserved, not retrospectively revalidated.

### Axis Midcap Fund

Registered source: `https://www.axismf.com/mutual-funds/equity-funds/axis-mid-cap-fund/mc-gp/regular`.

Require an exact non-navigation H1 `Axis Mid Cap Fund`, exact scheme/plan performance heading, the primary `Benchmark Returns` banner, and both `Benchmark(%)` and `Benchmark(₹)` table roles. The designated index must agree across those structures. The publisher reports **BSE Midcap 150 TRI** as primary; **Nifty 50 TRI** is retained separately as an additional comparator, not silently promoted to primary even when it appears first.

Conflicting responsive copies, an ambiguous primary designation, missing role columns or a changed scheme heading fail closed. Historical marketing performance statements are not used as current primary evidence. The performance reporting date is stored separately in `source_performance_as_of`; it is not an invented benchmark effective date.

### Mirae Asset Midcap Fund

Registered source: `https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-midcap-fund`.

Require exact non-navigation H1 `Mirae Asset Midcap Fund` and the reviewed `div.fund_fact_text` card pairing `benchmark index` with its single value. The publisher reports **NIFTY Midcap 150 (TRI)**. An additional-benchmark card, neighbouring value, generic navigation mention, conflicting duplicate or missing value cannot qualify.

### Evidence and boundaries

Both new readers preserve publisher wording, the actual primary role, additional indices, source URL/SHA-256/content type, original observation timestamp, scheme heading, structural locator and evidence excerpt. Parser: `explicit-primary-benchmark-labels-v1`. UTF-8 is decoded explicitly so the rupee-denominated role is not misdecoded.

The pages do not explicitly establish a benchmark effective date. `benchmark_effective_as_of` and `source_data_as_of` therefore stay null; AUM/NAV/performance dates are not borrowed. TRI is retained only where stated. `benchmark_series_verified=false` remains explicit: this work recovers reported identity, not the index time series.

The combined benchmark report now retains `source_sha256` and an independent `source_evidence` copy. Original evidence, dates, parser version and role no longer disappear from that combined view. The existing first-batch precedence is unchanged; future revisions/conflicts need explicit handling, not a claim that all old evidence was revalidated here.

Read-only source preflight passed **2/2** on the tested branch with `db.connect` forbidden and every request using `archive=False`. Source preflight is not production coverage; use the current batch artifact for final source outcomes. The temporary four-site diagnostic workflow remained on its isolated branch and was not merged.

## Completed earlier: Samco TER recovery

The old #647 checkpoint's 30/34 TER count reflected a newly missing Samco row, not an AMC withdrawal. **PR #293** already repaired this before #294 began, and [production #648 / 36384128565](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36384128565) completed successfully at **2026-09-28T06:05:16Z**. Its generated evidence at `68774e67c80d5373d36216cc885f7ad841caef4d` restored TER to 31/34.

Observed cause: the category-17 request omitted Samco while the broader exact-AMC feed returned it on page 2 under the plural label `Equity Schemes - Mid Cap Fund`. AMFI's internal reason for that discrepancy is unknown. The repair dynamically resolves the AMC, keeps the category-scoped request primary and applies fallback only to unresolved exactly owned Samco. It requires exact name, NSDL `SAMC/O/E/MIF/25/10/0013`, category/type, the complete bounded server-reported page set, current-month non-future dates and both plans' finite published TER/component reconciliation. BER is not substituted for total TER.

The previous discovery observed September 25 Direct TER 1.58% and Regular TER 3.00%; those are historical observations, not constants to paste into future reports. Use the latest current-run evidence. Bandhan, Bank of India and WhiteOak remain the prior first-party TER limitations; do not infer values or weaken thresholds to fill them.

## Completed earlier: freshness-safe readiness

PR #290's safeguards remain in place:

1. Reporting freshness precedes completeness. A complete July snapshot cannot displace a valid August partial when August is required. Completeness and position count break same-date ties only. The existing 10-day grace policy is unchanged; future, malformed and intramonth portfolio dates do not count.
2. Accepted portfolio rows require exact staged family/AMC, recovered status, valid named-position count, boolean completeness, source/hash and valid reporting/observation times. Valid stale evidence remains visible but non-current; alternatives and exclusions stay diagnostic evidence.
3. `MIDCAP_AUDIT_STARTED_AT` marks the current run before staged collection. Missing, malformed, explicitly failed or older retained input artifacts cannot silently qualify as newly generated. An explicitly supplied missing optional batch is not omitted.
4. The launch evaluator independently recalculates current portfolio coverage rather than trust saved flags/counts. It checks five core inputs and all nine producing TER/benchmark/portfolio batches. A new summary cannot conceal a failed older upstream file. Missing inputs produce a fresh blocked report.
5. Launch thresholds and the disabled public switch remain separate from collection. A valid benchmark name does not authorize a Small Cap comparator fallback or establish a usable benchmark series.

When a future change adds a producing batch, update its CLI and `tracker/midcap_launch_readiness.py::UPSTREAM_FILES` together and test missing/stale artifacts. This two-source extension intentionally uses an existing batch, so it changes neither required input names nor their count.

## Portfolio corrections and limitations retained

The preceding verified portfolio checkpoint has JM **72** positions (partial), Mahindra **59** (equity-only partial), Invesco **43** (complete) and Sundaram **79** (complete) in batch 5. Kotak's isolated preflight once found 68 issuers but the production response failed exact scheme identity; do not copy a preflight into current coverage. Use current batch outcomes if a later source varies.

**Sundaram:** the older discovery card's `AUMASONDATE=31-Jul-2026` does not date the portfolio. Exact scheme/code **MC**, category and approved workbook URL are checked, then the workbook itself must prove its portfolio date. The earlier complete August source was `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx`, SHA-256 `7cc4431867469382f3559c54bd12e0fbecb9586d6ddcd4bc02ba2bd7941894f0`. Stale/malformed workbooks still fail even with current-looking AUM/NAV metadata.

**Mahindra:** the original 63 positions incorrectly included Consumer Services, Healthcare, Power and Services as holdings. PRs #285–#287 corrected this to 59 issuers and require issuer classification, 16 sector subtotals and the 97.71% equity total to agree. Only the observed post-total issuer-marker legend is accepted; unknown footer text, malformed weights, duplicates and conflicting responsive copies fail. Keep `factsheet_equity_only`, `complete=false`: non-equity assets are excluded. Parser/validator versions remain `mahindra-midcap-issuer-rows-v2` and `sector-equity-reconciliation-v1`. Original source SHA-256 `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`; [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md) preserves the correction. This was a parser correction, not a trade.

## Next coherent task

First **recheck the newly failed Invesco monthly portfolio endpoint** against its exact source contract and latest error. The recorded failure is HTTP 502, not an identity/parser failure; confirm whether a normal subsequent official fetch recovers before changing code. A bounded transport repair needs an observed repeatable failure and regression evidence, not retimestamping the last-good workbook or relaxing date/identity gates. Do not introduce another long-running diagnostic on every production push.

Then continue **exact first-party reported benchmark recovery** for a small, verified group of still-missing families. Start with fund-specific **ICICI Prudential and Invesco** factsheet/API contracts, then ABSL, SBI, Franklin, UTI and JM according to the latest `remaining_families` list. Do not repeat Axis/Mirae recovery, Samco fallback or freshness work from an older handoff.

The latest exploratory boundary is recorded in `docs/superpowers/plans/2026-09-28-midcap-benchmark-labels.md`: ABSL's discovered empower factsheet was older, and the returned Invesco product-page HTML exposed no usable exact benchmark block. Neither was counted in #294. Use a genuinely new official factsheet/API route, not a broader name match or presumed category benchmark. Preserve explicit primary/additional roles, price/total-return variants, unknown effective dates and source evidence. No result from these exploratory pages was promoted into the live tables.

Continue current portfolio coverage and dependable Kotak source recovery after each source batch's full tests and exact production verification. Verify Taurus/WhiteOak source registration before claiming category-wide AMC document coverage. Keep known access blockers explicit and do not repeat unchanged blocked TER routes without a new official path.

Only after data coverage and input integrity pass should the separate **category-aware public exporter/static JSON/API/UI dry run** begin. Validate actual exportable financial records, correct series or explicit series absence, source/freshness/partial/unavailable labels, routing, and Small Cap non-regression. An audit count is not a public fund page and the launch report never flips the switch.

## Safety and operations

Mid Cap remains `stage=staged`, `public_export_enabled=false`. This benchmark audit changes no live Mid Cap financial record, public UI, fee/performance calculation, source access, spending or dependencies. The full publisher still performs its existing Small Cap/archive maintenance; do not describe that whole workflow as making zero database writes.

Read-only pre-merge source verification is separate from production. The new benchmark preflight is selected only for `fix/midcap-benchmark-*` development branches; the established Samco and batch-5 preflight branches retain their own behavior. Source failures remain visible even when a non-blocking audit step allows Small Cap publication.

The existing daily ChatGPT launch-readiness check remains unchanged; do not create a duplicate. Its push/email settings were last recorded as disabled and were not rechecked in this slice. The check cannot modify code, merge or publish.

## Source-of-truth artifacts

- `docs/MIDCAP-LAUNCH-READINESS.json`: numerical gates, reporting/evaluation dates and current-run input checks; not a launch switch.
- `docs/MIDCAP-BENCHMARK-BATCH2.json`: the two new source results and explicit errors for any legacy targets; `docs/MIDCAP-BENCHMARK-READINESS.json` retains original evidence.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` / `.md` and portfolio batches 1–5: current/stale/unavailable coverage, completeness, source proofs and exclusions.
- `docs/MIDCAP-TER-READINESS.json`, both first-party TER batches and `docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json`: current AUM/TER evidence, Samco fallback identity and gaps.
- `deployment/midcap-history-status.json`: staged NAV history; `deployment/update-status.json`: build/publication status, distinct from source observation.
- `docs/superpowers/plans/2026-09-28-midcap-benchmark-labels.md`: implementation, source-contract and verification ledger.
