# Mid Cap backend handoff

Use this handoff together with the latest generated readiness reports and the exact GitHub Actions run. Older successful audits and isolated source preflights are history, not proof that the latest production collector passed.

## Latest verified checkpoint

- Latest code change: **PR #290**, freshness-safe portfolio reconciliation and launch-input validation. Code merge: `85642b293bd496e827eac3aa6ad50c5f59a13426`.
- Production: [run #647 / 36380625528](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380625528), **completed successfully on 2026-09-28**. Both build and deploy jobs passed. Verified stages include the audit-generation boundary, staged audits, regressions, site generation, generated-data/download validation, cumulative archive publication, status recording and Pages deployment.
- Refreshed production artifacts were inspected at commit **`9a370aa85e67936d016659b7d2c1ebd5fc62d372`**. Portfolio readiness was evaluated at **2026-09-28T05:15:45.365686+00:00**; launch readiness at **2026-09-28T05:15:45.442468+00:00**. The expected portfolio reporting month-end is **2026-08-31**. `deployment/update-status.json` was built at **05:18:54 UTC**; that is a status-build timestamp, not a source observation or the terminal deployment time.
- Final pre-merge head: `0632014d2b8672f91057c5a54b0254f3bfd6dd24`. [PR regression run 36380319806](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319806) passed **631 tests** and syntax checks. This is 38 additional tests beyond the prior 593-test checkpoint. The earlier 42-test local focused suite was not the full repository suite.
- [Research UI checks 36380319795](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319795) also passed. The dedicated batch-5 public-source preflight was **skipped** in this PR run; do not claim it was rerun. This patch changes readiness code, tests and one workflow-boundary step, not the AMC collectors or the public UI.
- The generated launch report has **14/14 input-health checks passing**, **`input_issues=[]`**, and **`audit_input_integrity=true`**. The five portfolio batch inputs also pass reconciliation integrity. These are current-run artifact checks, not a claim that every fund/source has coverage.

Verification scope: repository changes, full pre-merge regressions, production workflow results, generated source/readiness evidence and terminal build/deploy success. Direct public-site/browser access failed in this environment; no fresh visual/mobile pass is claimed. Production still reports **36 Small Cap families**, **143 plans**, AUM and fee coverage **36/36**, and latest NAV **2026-09-25**. Mid Cap remains non-public.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history coverage | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 families | 34 / 34 |
| Direct TER | **30 / 34** | At least 31 / 34 |
| Reported benchmark identity | 12 / 34 | At least 31 / 34 |
| Current portfolio evidence | 16 / 34 | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Separate measure; do not relabel partials |

The complete current portfolios are **HDFC, Mirae Asset, Invesco India and Sundaram**. All 16 current portfolio rows report **2026-08-31**. There are 18 families without current portfolio evidence, of which at least 12 additional families are needed to reach the existing launch threshold.

The launch report remains **`data_ready=false`**, **`launch_ready=false`** and **`public_export_enabled=false`**. The remaining numerical requirements are **1 more Direct TER family**, **19 more reported benchmark identities** and **12 more current portfolio-evidence families**, followed by the separate category-aware public-surface dry run. Thresholds are product-quality policy, not regulatory rules.

### New TER gap: Samco

**Do not repeat the previous 31/34 TER count as current.** Run #647 reports **30/34**, with these four missing families: **Bandhan, Bank of India, Samco and WhiteOak Capital**. Samco is the newly missing family; both Regular and Direct TER, their reporting date and source are null in the current reconciled report.

The dedicated first-party TER batches themselves recovered **7/7** and **3/3** targets with no recorded errors. None of those ten targets is Samco. The verified finding is a newly missing Samco TER evidence row, not a proven AMC withdrawal, transport failure or bug introduced by PR #290. The exact underlying AMFI/source cause still needs investigation. Keep the gap explicit and the TER gate false; do not copy an older observation into current coverage or lower the threshold.

## Completed: freshness-safe readiness

The previously listed reliability task is implemented and production-verified in **PR #290**. Do not re-implement it from an older handoff.

1. **Reporting freshness precedes completeness.** A complete July snapshot cannot displace a valid August partial snapshot when August is required. Completeness and position count break ties only for the same reporting date. The existing 10-day grace policy is unchanged; a newer closed month may count during that grace window. Future, malformed and intramonth reporting dates do not count.
2. **Validate source rows and preserve evidence.** Accepted portfolio evidence requires exact staged family/AMC ownership, recovered status, a valid named-position count, boolean completeness, source URL/hash and valid observation/reporting times. Valid stale records stay visible as stale; excluded and alternate records remain diagnostic evidence. Source hashes, workbook/member identity, observation timestamps, scope and partial flags are retained rather than replaced by the summary timestamp.
3. **Verify current-run audit inputs.** `MIDCAP_AUDIT_STARTED_AT` is established before staged audits. Missing, malformed, explicitly failed or older retained input files are reported as integrity problems. An explicitly supplied missing optional batch is not silently omitted. The launch command checks five core reports and all nine producing TER/benchmark/portfolio batches.
4. **Recalculate at the launch boundary.** The launch evaluator independently re-evaluates portfolio rows at its evaluation clock. Retained current flags, inflated summary counts, mismatched universes and unverified inputs cannot produce a green data gate. Missing or malformed core inputs produce a fresh, blocked report rather than leaving an old green report as the result.
5. **Keep publication separate.** Existing numerical thresholds and the disabled public switch are unchanged. Reported benchmark identity is not benchmark-series availability. No silent Small Cap comparator or automatic category promotion is authorized.

Regression coverage includes older-complete/newer-partial precedence, stale/future/malformed dates, month/year/leap-year boundaries, the existing grace period, ownership/status/count errors, retained provenance, immutable inputs, missing or retained files, false-green summaries and file-to-launch integration. The implementation plan and completed execution ledger are in [2026-09-28-midcap-freshness.md](superpowers/plans/2026-09-28-midcap-freshness.md).

## Portfolio source corrections retained from PRs #285–#287

Latest production batch 5 continues to cover **JM (72 positions, partial)**, **Mahindra (59, equity-only partial)**, **Invesco India (43, complete)** and **Sundaram (79, complete)**. Kotak remains unavailable in production portfolio readiness. The earlier isolated Kotak preflight found 68 equity positions, 23 sectors and 96.48% equity weight, but that result is not current production coverage and must not be copied into the report. Preserve the exact identity/date gates and investigate the variable fund-page response before calling Kotak recovered.

### Sundaram: portfolio date is independent of AUM metadata

The previously verified discovery card had `AUMASONDATE=31-Jul-2026`, while its Mid Cap workbook independently reported **2026-08-31**. PR #287 validates exact scheme identity, code **MC**, category and approved first-party workbook URL, then requires the workbook itself to prove its reporting date. It does not relabel the older AUM date or borrow a newer NAV date. Stale/malformed workbooks still fail; PDF/HTML responses remain explicit parser gaps.

Verified workbook identity from the preceding source-recovery checkpoint: `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx`, SHA-256 `7cc4431867469382f3559c54bd12e0fbecb9586d6ddcd4bc02ba2bd7941894f0`. Use the latest batch artifact for the current observation and discovery hashes.

### Mahindra: sector headings are not holdings

The original 63-position result incorrectly included Consumer Services, Healthcare, Power and Services. PRs #285–#286 corrected that to **59 issuers** and accepted only the observed issuer-marker legend after an explicit 100% Grand Total. Unknown post-total text, malformed weights, duplicates and conflicting responsive copies still fail closed.

PR #287 preserves those guards and additionally requires issuer classification and structural sector-table parsing to agree. Sixteen sector subtotals and the **97.71%** equity total reconcile. Valid CSS sector styling is distinguished from the publisher's invalid `f ont-weight`/`fo nt-weight` issuer styling without repairing those issuer styles into sectors. The result remains `factsheet_equity_only`, `complete=false`; non-equity assets are excluded.

Current parser/validation versions remain `mahindra-midcap-issuer-rows-v2` and `sector-equity-reconciliation-v1`. Original source SHA-256: `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`. Preserve the audit and correction history in [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md). This was a parser correction, not a trade or a publisher portfolio change.

## Safety and operational boundaries

Mid Cap remains `stage=staged`. Readiness/source audits do not promote Mid Cap metrics, portfolios or holdings into live tables. No public UI, category switch, financial calculations or source-access permissions were changed in PR #290. The full production workflow still performs normal Small Cap/archive maintenance; do not describe the entire workflow as making zero database writes.

Read-only regression and source-contract workflows remain separate from publication. Source preflights use `archive=False` and must not be treated as production results. The owner's existing daily ChatGPT launch-readiness check is unchanged and cannot change code, merge or publish; do not create a duplicate task. Its push/email notification settings last recorded in the preceding handoff were disabled, not rechecked in this verification slice.

## Next coherent task: recover the newly missing TER evidence, then benchmarks

First investigate **Samco Mid Cap TER** against the latest source-audit/AMFI response and its exact family/plan/date evidence. Compare with the prior successful checkpoint without retimestamping or copying old figures. Add an exact first-party Samco source only when its scheme identity and complete Regular/Direct TER pair are independently verified. Preserve BER versus TER distinctions, source hashes and reporting/observation times. Verify the next production report before restoring a 31/34 claim. Keep the other Bandhan, Bank of India and WhiteOak limitations explicit.

After that, resume first-party benchmark-identity recovery. Existing portfolio-covered families with missing benchmark identities include **Invesco India, Mirae Asset, ICICI Prudential, Axis, Aditya Birla Sun Life, SBI, Tata/UTI only where the latest benchmark report actually marks them missing**; use the machine-readable remaining-family list rather than assume every portfolio source proves a benchmark. Prefer a coherent batch with verified fund-specific AMC disclosures. Distinguish the designated primary benchmark from additional comparators and TRI from price-return variants. Retain evidence and do not infer the category's usual benchmark.

Then continue the remaining current portfolio families, including the unreliable Kotak response. Every new slice must retain the current-run integrity gate, run full pre-merge regressions, verify its exact production run and update this handoff. A successful workflow is not proof that an individual source gap is resolved.

## Publication still requires a separate dry run

Before deliberate launch, implement and validate category-aware exporter/static JSON/API/UI routing, actual exportable holdings and metric evidence, source/freshness/partial labels, benchmark handling and Small Cap non-regression. Staged audit counts are not a substitute for financial records or usable benchmark series. The launch report itself never enables the category.

## Source-of-truth artifacts

- `docs/MIDCAP-LAUNCH-READINESS.json`: current threshold evaluation, 14 input checks, integrity issues and reporting/evaluation dates; never a launch switch.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and `.md`: current/stale/unavailable rows, completeness, provenance and diagnostic alternatives.
- `docs/MIDCAP-PORTFOLIO-BATCH1.json` through `BATCH5.json`: source-level portfolio evidence and errors.
- `docs/MIDCAP-TER-READINESS.json`, its two first-party batches and `docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json`: current TER/AUM evidence and gaps.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and its producing batches: benchmark identities, not proof of available series.
- `deployment/midcap-history-status.json`: staged NAV-history status.
- `deployment/update-status.json`: build/publication status, distinct from source coverage.
