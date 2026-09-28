# Mid Cap backend handoff

Read this alongside the latest generated artifacts and their exact production run. A green workflow, a fresh summary or an isolated source preflight does not establish coverage for every family. Mid Cap remains staged and non-public.

## Latest verified checkpoint

- **Code: PR #298**, primary-role and whole-value validation for the existing ABSL/SBI benchmark readers. Squash merge: `a4897813090a5645f5a28e14252980629046b14e`. This is a correctness repair to PR #296, not an additional source batch.
- **Final tested head:** `725944fb5f3483e8dc45bc989686b0bec1c35e35`. [Branch verification 36435196302](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36435196302), job `108971187721`, passed syntax checks and **723 full repository tests** (`Ran 723 tests in 13.686s`, `OK`). The same head's actual read-only benchmark preflight recovered **4/4** sources with `errors=[]`.
- [PR regression 36435362641](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36435362641) and [Research UI checks 36435362637](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36435362637) both passed before merge. The PR-triggered run skips source preflights; the exact-head push run above is the source-preflight evidence. Samco and batch-5 preflights were not rerun on this benchmark branch.
- **Production:** [run #652 / 36435504460](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36435504460), **build and deploy completed successfully on 2026-09-28**. Build job `108972258393` completed at **14:31:03 UTC**; deploy job `108975912337` completed at **14:31:32 UTC**. Staged audits, repository regressions, generated-site validation, archive publication and status recording passed. The normal full daily collector was skipped on this push, as designed.
- **Evidence commit:** `c0982fe4ac4b5231a3fdf5556b86ec4161c00fd0`. Benchmark batch 2: `2026-09-28T14:25:42+00:00`. Portfolio evaluation: `2026-09-28T14:27:23.921354+00:00`. Launch evaluation: `2026-09-28T14:27:23.988550+00:00`. Required portfolio reporting month-end: `2026-08-31`.
- **Input integrity:** **14/14 input checks passed; `input_issues=[]` and `audit_input_integrity=true`**. Source observation, source document period, report-generation time, status-build time and terminal deployment time are distinct clocks.

Verification scope: local bug reproductions and focused tests, full repository CI, direct read-only AMC source preflight, self-review of the exact diff, and the production evidence above. No independent human/subagent review or new visual/mobile browser pass is claimed. No public UI, dependencies, thresholds, source permissions or Mid Cap publication switch changed.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | 16 / 34 | At least 31 / 34 |
| Current portfolio evidence | 16 / 34 | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Separate measure; never relabel partials |

No additional families were added by PR #298. Benchmark batch 2 recovered **8/9** targets; JM's existing exact-page identity failure remains explicit. Both v2 readers recovered their previously observed publisher benchmark names in production, with ABSL's document period and SBI's page/date metadata retained. ABSL was observed at **14:25:40.916704 UTC**, SBI at **14:25:42.992664 UTC**; both source hashes match those recorded below.

All 16 current portfolio rows report **2026-08-31**. The four complete portfolios are **HDFC (81 positions), Mirae Asset (68), Invesco India (43) and Sundaram (79)**. Invesco's current workbook was freshly observed at **2026-09-28T14:27:18+00:00**, not retimestamped from #650. Kotak remains unavailable in the combined portfolio report.

Keep `data_ready=false`, `launch_ready=false` and `public_export_enabled=false` until the actual separate requirements are satisfied. The remaining deficits are **15 more reported benchmark identities and 12 more current portfolio-evidence families**, then the category-aware public-surface dry run. Thresholds are tracker product-quality policy, not regulatory rules. Benchmark-identity counts do not establish available index series, benchmark effective dates, or complete/exportable financial records.

## Completed: primary-role and whole-value correction

The prior v1 parser used expected-name regexes over flattened text. Adversarial fixtures reproduced ABSL `Additional Benchmark` and `Previous Benchmark` being accepted as primary, conflicting or unknown primary values being ignored, and compound/suffixed values being truncated. SBI could likewise ignore competing Tier-I blocks. These are parser failure modes, not evidence that the previously observed publisher benchmark names were wrong.

The initial structural suite produced **22 failures out of 26 tests against the exact original parser**. Two additional date-scope tests failed against the first repair before correction. The final local focused suite passed **30 tests**; it was an isolated source-module suite, not the full repository. Full CI increased from 693 to 723 tests. Existing fixtures now model the observed HTML table and PDF riskometer structure rather than unscoped prose. Real PDF generation/extraction and combined-evidence retention are tested.

### ABSL: exact table role and explicit document period

Source: `https://mutualfund.adityabirlacapital.com/empower/Equity-Funds/Midcap-Fund.html`.

Require one unambiguous exact scheme heading and the actual **Fund Snapshot** table. Parse the entire cell beginning with `Benchmark:`. Additional/historical labels and unrelated tables cannot supply the primary value. Every primary-labelled cell is checked: unknown, conflicting, composite or suffixed values fail closed instead of disappearing from consideration. Identical values in the one reviewed table may agree; competing snapshot tables are ambiguous.

The accepted publisher wording is **Nifty Midcap 150 TRI**. The observed source's scheme banner explicitly says **July 2026**. Store `source_document_period=2026-07`, not a September financial date just because the page was fetched in September. Only a scoped scheme banner may supply that period; unscoped page/body paragraphs cannot. Missing document-period evidence remains null.

Source hash verified in the source preflight: `c21d367231006606430cdb2bb34970a44fca211115b31a93b5d39a15c8b67c14`. Use the latest production artifact for the exact current observation and hash. `benchmark_effective_as_of` and `source_data_as_of` remain null. This is a reported benchmark identity in that document, not proof of a benchmark effective date or that the document is the newest available AMC disclosure.

### SBI: bounded first-page Tier-I block

Source: `https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-midcap-fund.pdf?sfvrsn=f93cc0ce_0`.

Preserve extracted PDF line boundaries. Require one exact full **KIM – SBI Midcap Fund** heading, KIM identity, and exactly one Tier-I role in the first-page **Benchmark Riskometer** block. Its value ends at the reviewed investor-footnote boundary. Historical prefixes, duplicate Tier-I roles, missing boundaries, extra suffixes and composite values fail closed. A line-wrapped valid value still works. Retain `source_page=1`, the structural locator and actual evidence excerpt.

Accepted publisher wording: **Nifty Midcap 150 Index TRI**. The document itself is dated **2025-10-31**, retained as `source_document_as_of`, not a current financial reporting or benchmark effective date. Preflight source hash: `1340f3e97b4c90c9efd0a0623468c81011d4c2532a7ecb223335b1e6b5db66e6`.

Both readers now identify `parser_version=explicit-benchmark-documents-v2`. Their registrations, transport, publisher wording and existing batch membership remain unchanged. Both keep `benchmark_series_verified=false`; no TRI variant, benchmark effective date or historical series is invented.

### Diagnostic and production boundaries

The read-only structure diagnostic was [36433460967](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36433460967), job `108965272970`, on isolated branch `diag/midcap-benchmark-role-20260928`. Its workflow was **not merged**. It made source requests with `archive=False` and forbade `db.connect`. The normal four-source benchmark preflight has the same read-only boundaries.

PR #298 changes one parser and three test files only. It does not add an upstream report, modify `UPSTREAM_FILES`, or change the existing 14-file integrity contract. Legacy benchmark readers and reconciliation precedence were not retrospectively revalidated. Do not generalize these two readers' stronger validation to every older benchmark record.

## Prior work that must not be reimplemented

**Axis/Mirae, PR #294:** exact non-navigation scheme headings and reviewed primary roles. Axis requires its primary banner and percentage/rupee performance columns to agree; BSE Midcap 150 TRI is distinct from its additional Nifty 50 TRI comparator. Mirae requires the exact `benchmark index` fund-fact card and preserves `NIFTY Midcap 150 (TRI)`. Performance/AUM/NAV dates are not benchmark effective dates. Original proof is deep-copied into the combined report. These existing readers are unchanged here.

**Samco TER, PR #293:** the exact AMC-scoped fallback repaired category-17 omission and AMFI's plural category wording. Dynamically resolve the AMC, preserve complete bounded pagination, exact name/NSDL `SAMC/O/E/MIF/25/10/0013`, category/type, current-month non-future dates and both plans' published TER/component reconciliation. BER is not substituted for TER. Historical September 25 observations are not constants to paste into future results. Bandhan, Bank of India and WhiteOak remain the previously documented TER limitations unless a later artifact proves recovery.

**Freshness, PR #290:** select portfolio reporting month before completeness. A newer valid partial displaces an older complete snapshot. Preserve the 10-day grace rule, exact family/AMC, valid named-position counts, boolean completeness, source hashes and reporting/observation clocks. Keep stale/alternate/excluded evidence explicit. Establish `MIDCAP_AUDIT_STARTED_AT` before staged audits and verify five core inputs plus nine producing batches; a new summary cannot conceal old, malformed or failed input. Independently recalculate portfolio counts at launch evaluation. Missing inputs must produce a fresh blocked report.

**Portfolio corrections, PRs #285–#287:** Mahindra's original 63-position extraction included sector headings; the corrected source has 59 issuers with 16 sector subtotals reconciling to 97.71% equity. Preserve `factsheet_equity_only`, `complete=false`, the issuer/footer/duplicate guards and [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md). Sundaram's discovery-card AUM date does not date its workbook: verify exact scheme/code MC and workbook reporting date independently. Do not borrow NAV/AUM dates to label a portfolio current.

**Invesco/Kotak:** #649's Invesco 502 was followed by normal recovery in #650, with 43 positions in the exact August workbook. Use the latest batch outcome; a past successful fetch is not a fresh observation, and one upstream failure is not evidence of permanent outage or a parser defect. Kotak's earlier isolated 68-issuer preflight is not production coverage when the exact scheme gate fails. Never copy it into a report or weaken identity rules merely to increase coverage.

Earlier full checkpoint detail is preserved in [the pre-#298 handoff](https://github.com/Vasuki8/Smallcap-Ledger/blob/a4897813090a5645f5a28e14252980629046b14e/docs/MIDCAP-HANDOFF.md) and its linked plans/runs. This document replaces those older counts as the latest checkpoint only where fresh evidence is explicitly recorded above.

## Next coherent task

Resume **exact first-party reported benchmark recovery** for **ICICI Prudential and Invesco**, using the current `remaining_families` list. The attempted Invesco product-page route did not expose a usable primary value; do not broaden name/proximity matching, treat NA as identity, or infer the category's usual benchmark. Review a genuinely usable fund-specific AMC factsheet/API/scheme-document contract. Then address Franklin, UTI and JM only with exact publisher-proven identities/aliases and designated primary roles.

ABSL/SBI recovery and the v2 role repair are complete. Do not repeat them from the old handoff or claim this correctness slice recovered additional funds. Preserve primary/additional roles, PRI/TRI wording, whole values, source URLs/hashes, evidence location, observation times, document periods and unknown effective dates. Retained publication proof is not a substitute for verifying index-series availability.

Continue current portfolio source recovery toward the 28-family gate, using actual unavailable-family/error lists. Require repeatable first-party source evidence before changing a transport contract. Preserve the freshness-safe current-run gate, partial labels and original observations. Verify Taurus/WhiteOak source registration before claiming category-wide AMC document coverage. Keep access-blocked routes explicit.

Only after data and input-integrity gates pass should the separate category-aware **exporter/static JSON/API/UI dry run** proceed. Verify actual exportable metrics/holdings, correct index series or explicit absence, dates/source/partial/unavailable labels, routing and Small Cap non-regression. Never silently substitute the Small Cap comparator. The launch report itself never enables Mid Cap.

## Operations and source-of-truth artifacts

Mid Cap stays `stage=staged`, `public_export_enabled=false`. Source audits do not promote staged financial data to live tables. The overall publisher still performs its normal Small Cap/archive maintenance; do not describe the entire workflow as making zero database writes. No source-access bypass, spending, subscription change, archive deletion or automatic promotion is authorized by this task.

The existing daily ChatGPT launch-readiness check is unchanged; do not create a duplicate. It cannot change code, merge or publish. Push/email settings were previously recorded disabled and were not rechecked here.

- `docs/MIDCAP-LAUNCH-READINESS.json`: actual/required counts, per-input health, remaining gates and evaluation date; not a launch switch.
- `docs/MIDCAP-BENCHMARK-BATCH2.json` and `docs/MIDCAP-BENCHMARK-READINESS.json`: v2 source evidence, dates/periods/page/roles and source errors. Batch 1 contains the unchanged legacy evidence.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and portfolio batches 1–5: current/stale/unavailable rows, completeness, source proof, alternate/excluded evidence.
- `docs/MIDCAP-TER-READINESS.json`, both TER batches and `docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json`: AUM/TER proof and explicit gaps.
- `deployment/midcap-history-status.json`: staged NAV history; `deployment/update-status.json`: separate build/publication status.

For any future added producing batch, update its CLI and `tracker/midcap_launch_readiness.py::UPSTREAM_FILES` together, and test missing/stale/malformed artifacts. Keep read-only source preflight separate from exact production verification and update this handoff after each completed slice.


The documentation-only handoff merge uses `[skip ci]` to avoid replaying the full collector/deployment for prose alone. No workflow is disabled, no schedule is changed, and application-code tests/preflights/production verification were not skipped.
