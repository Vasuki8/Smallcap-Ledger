# Mid Cap backend handoff

Use this handoff with the latest generated reports and the exact code/workflow checkpoint. An older successful audit, a source preflight, or a newly generated summary is not proof that the latest individual source collection passed. Mid Cap is still non-public.

## Latest verified checkpoint

- Latest code: **PR #296**, exact first-party primary benchmark recovery for Aditya Birla Sun Life and SBI. Squash merge: `50056ef4b87ddc90bb25a2b40716efc6117a4e71`. The Axis/Mirae repair in **PR #294**, Samco TER repair in **PR #293**, and freshness safeguards in **PR #290** remain in place.
- Tested head: `6a06af3a2f13f5847757312d3c098bfaab4446d8`. [Branch verification 36430545254](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36430545254) passed syntax, **693 full repository tests**, and the actual four-source benchmark preflight. The first full-head run exposed one test-selection assertion bug; after that test was corrected, all 693 tests passed.
- Both [PR regression 36430707700](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36430707700) and [Research UI checks 36430707642](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36430707642) passed before merge. The pull-request run did not repeat the push-only source preflight; the successful exact-head branch run is the source-preflight evidence.
- Production: [run #650 / 36430789202](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36430789202), **build and deploy completed successfully on 2026-09-28**. Build job 108956132153 passed the staged audits, full repository regressions, generated-site validation, cumulative archive publication and status recording. Deploy job 108959611299 also completed successfully.
- Refreshed evidence commit: `a4d968ea5484635a026dc21273ce3b71afa910a3`. Benchmark batch 2 built at **2026-09-28T13:47:49+00:00**; portfolio readiness at **2026-09-28T13:49:30.864567+00:00**; launch readiness at **2026-09-28T13:49:30.938880+00:00**. Portfolio reporting month-end remains **2026-08-31**.
- Latest input integrity: **14/14 required input checks passed; `input_issues=[]` and `audit_input_integrity=true`**. A successful workflow still does not imply every family/source has coverage.

Verification scope: source-specific parser tests, full repository CI, actual read-only first-party responses, refreshed production reports and terminal Pages deployment. No public Mid Cap UI, live financial records, launch thresholds or publication switch changed.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | **16 / 34** | At least 31 / 34 |
| Current portfolio evidence | **16 / 34** | At least 28 / 34 |
| Complete current portfolios | **4 / 34** | Separate measure; never relabel partials |

Benchmark batch 2 now recovers **8/9** targets. The remaining batch-2 error is **JM Mid Cap Fund**, whose current registered product page still fails the exact staged-family identity gate. Combined benchmark coverage increased from 14 to **16/34**. The two new verified identities are **Aditya Birla Sun Life Midcap Fund — Nifty Midcap 150 TRI** and **SBI MIDCAP FUND — Nifty Midcap 150 Index TRI**.

The earlier Invesco HTTP 502 did **not** repeat. Run #650 recovered **Invesco India Mid Cap Fund** from the official complete-monthly-holdings workbook with **43 positions**, `complete=true`, reporting date **2026-08-31**, source SHA-256 `7940a64e15b08842147fe16320c143a02fec6033617c305a64c92113d0649bbe`, observed at **2026-09-28T13:49:25+00:00**. Treat the #649 502 as a transient observed upstream failure, not a permanent outage or parser defect. The four current complete portfolios are now **HDFC, Mirae Asset, Invesco India and Sundaram**.

The launch report remains **`data_ready=false`**, **`launch_ready=false`**, and **`public_export_enabled=false`**. AUM, NAV/history and Direct TER gates pass. The remaining numerical deficits are **15 reported benchmark identities** and **12 current portfolio-evidence families**, followed by the separate category-aware public-surface dry run. These thresholds are product-quality policy, not regulatory rules.

## Completed: Aditya Birla Sun Life and SBI primary benchmark recovery

PR #296 extends the **existing benchmark batch 2** and therefore keeps the existing daily artifact names and **14-file input-integrity contract** unchanged. New source-specific parsers fail closed rather than broaden legacy name/proximity matching.

### Aditya Birla Sun Life Midcap Fund

Registered source: `https://mutualfund.adityabirlacapital.com/empower/Equity-Funds/Midcap-Fund.html`.

The parser requires one exact scheme heading and the explicit Fund Snapshot `Benchmark:` label. Production reports **Nifty Midcap 150 TRI** as the primary benchmark. Unlabelled nearby indices, an altered scheme heading, a missing TRI statement or an ambiguous label do not qualify.

Production source SHA-256: `c21d367231006606430cdb2bb34970a44fca211115b31a93b5d39a15c8b67c14`. Parser: `explicit-benchmark-documents-v1`. `benchmark_effective_as_of` remains null and `benchmark_series_verified=false`.

### SBI MIDCAP FUND

Registered source: `https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-midcap-fund.pdf?sfvrsn=f93cc0ce_0`.

The parser reads the official KIM first page and requires the exact SBI Midcap Fund KIM identity plus the explicit **Tier I Benchmark** role. Production reports **Nifty Midcap 150 Index TRI**. Tier-II or other comparison indices are not promoted.

The KIM itself is dated **2025-10-31**; that date is retained separately as `source_document_as_of` and is **not** treated as a benchmark effective date or a current market observation. Production source SHA-256: `1340f3e97b4c90c9efd0a0623468c81011d4c2532a7ecb223335b1e6b5db66e6`. `benchmark_effective_as_of` remains null and `benchmark_series_verified=false`.

### Evidence and boundaries

The exact-head push preflight recovered Axis, Mirae, ABSL and SBI **4/4 with `errors=[]`**, while `db.connect` was forbidden and every source request used `archive=False`. This is read-only source validation, not a claim of benchmark-series availability. Publisher wording, source URL/hash/content type, observation time, source locator, evidence excerpt, primary role and parser version are retained.

## Completed earlier: Axis and Mirae explicit primary benchmark sources

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

The current verified portfolio checkpoint has JM **72** positions (partial), Mahindra **59** (equity-only partial), Invesco **43** (complete) and Sundaram **79** (complete) in batch 5. Run #650 re-established Invesco as current after #649's transient 502. Kotak's isolated preflight once found 68 issuers but production continues to fail the exact scheme-identity contract; do not copy a preflight into current coverage. Use current batch outcomes if a later source varies.

**Sundaram:** the older discovery card's `AUMASONDATE=31-Jul-2026` does not date the portfolio. Exact scheme/code **MC**, category and approved workbook URL are checked, then the workbook itself must prove its portfolio date. The earlier complete August source was `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx`, SHA-256 `7cc4431867469382f3559c54bd12e0fbecb9586d6ddcd4bc02ba2bd7941894f0`. Stale/malformed workbooks still fail even with current-looking AUM/NAV metadata.

**Mahindra:** the original 63 positions incorrectly included Consumer Services, Healthcare, Power and Services as holdings. PRs #285–#287 corrected this to 59 issuers and require issuer classification, 16 sector subtotals and the 97.71% equity total to agree. Only the observed post-total issuer-marker legend is accepted; unknown footer text, malformed weights, duplicates and conflicting responsive copies fail. Keep `factsheet_equity_only`, `complete=false`: non-equity assets are excluded. Parser/validator versions remain `mahindra-midcap-issuer-rows-v2` and `sector-equity-reconciliation-v1`. Original source SHA-256 `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`; [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md) preserves the correction. This was a parser correction, not a trade.

## Next coherent task

Continue **exact first-party reported benchmark recovery** for a small verified group from the current `remaining_families` list. Start with **ICICI Prudential and Invesco** using fund-specific factsheet/API/document contracts that explicitly identify the primary benchmark; the earlier Invesco product-page HTML did not expose a usable exact benchmark block, so do not reuse that failed route. Then address **Franklin, UTI and JM** with explicit scheme-name aliases or alternate official documents only when the publisher's source proves the same staged scheme and primary role. ABSL and SBI are complete; do not repeat them.

Keep benchmark identity separate from benchmark-series availability. Preserve primary versus additional roles, TRI/PRI wording, document/reporting/effective dates as distinct fields, source hashes and observation times. Never infer the category's usual benchmark, borrow a NAV/AUM/performance date as a benchmark effective date, or treat a KIM/factsheet identity as proof that a usable historical index series is already imported.

In parallel, continue **current portfolio source coverage** toward 28/34, but do not modify Invesco merely because #649 returned one 502: #650 recovered the exact official August workbook normally. Prioritize currently unavailable families and dependable Kotak recovery only when a repeatable official contract is observed. Preserve the freshness-safe current-run gate and never retimestamp a retained prior snapshot.

Only after the benchmark and current-portfolio data gates pass should the separate **category-aware public exporter/static JSON/API/UI dry run** begin. Validate actual exportable metrics/holdings, correct benchmark series or explicit series absence, source/freshness/partial/unavailable labels, category routing, and Small Cap non-regression. The launch report itself never enables Mid Cap.

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
