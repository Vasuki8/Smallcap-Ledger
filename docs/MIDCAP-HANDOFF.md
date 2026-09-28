# Mid Cap backend handoff

This is the focused continuation handoff for Mid Cap development. Historical README handoff entries remain implementation history; use this file together with current generated readiness reports and GitHub Actions results. Never use an older successful audit or a separate source preflight to claim that a newer production collector passed.

## Latest verified checkpoint

- Latest change: **PR #287**, building on the issuer/sector and exact post-total-footer safeguards from **PRs #285–#286**. It adds independent sector/equity-subtotal reconciliation, metric-specific reporting-date validation and Sundaram portfolio recovery.
- Code merge: `69cde3417ae8c7144d8e43b36fdf488381f52162`.
- Production: [run #646 / 36378611855](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36378611855), **completed successfully on 2026-09-28 at 04:47:17 UTC**. Both build and deploy jobs passed.
- Verified stages include staged audits, regression tests, site generation, generated-data/download validation, cumulative archive publication, status recording and Pages deployment. A successful workflow does not mean every source succeeded: the batch-5 artifact records Kotak's remaining validation failure explicitly.
- Refreshed evidence was inspected at commit `24103b816fe06f5f697b307fe173c30bfc375113`. Batch 5 was generated at **2026-09-28T04:43:43+00:00**; accepted portfolios report **2026-08-31**. `deployment/update-status.json` was generated at **04:46:33 UTC**. Reporting, observation and publication times are distinct.
- Final pre-merge branch head: `90adbef303ee62e6931cfa5817b4693e50f36ecb`. All **593 regression tests** and syntax checks passed in [branch verification 36378544116](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36378544116). This change adds 23 tests beyond main's 570-test checkpoint.
- [PR regression 36378546417](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36378546417) and [Research UI checks 36378546381](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36378546381) also passed before merge. Concurrent main changes, including the stricter footer validator, its tests, source-probe workflow and prior handoff, were preserved.

Verification scope: repository evidence, full pre-merge regressions, actual first-party responses, refreshed production reports and terminal build/deploy results. Direct public-site/browser smoke access failed in this environment; no visual/mobile pass is claimed. The production status still reports **36 Small Cap families**, AUM and fee coverage **36/36**, and latest NAV **2026-09-25**. No Mid Cap public page was enabled.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history coverage | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 families | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | 12 / 34 | At least 31 / 34 |
| Current portfolio evidence | 16 / 34 | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Separate measure; do not relabel partials |

The four complete current portfolios are **HDFC, Mirae Asset, Invesco India and Sundaram**. The generated launch report remains **data_ready=false**, **launch_ready=false** and **public_export_enabled=false**. At these production counts, the data thresholds need **19 more reported benchmark identities** and **12 more current portfolio-evidence families**, followed by the category-aware public-surface dry run.

These are product-quality thresholds, not regulatory rules. Passing counts alone does not authorize launch, especially while readiness aggregation still requires the freshness hardening below.

## Batch 5: production outcomes versus source preflight

Production run #646 recovered **4 of 5 targets**. All accepted results report **2026-08-31**:

| Family | Named positions | Completeness | Evidence |
| --- | ---: | --- | --- |
| JM Mid Cap Fund | 72 | Partial | Official monthly workbook; CCIL remains an unclassified row |
| Mahindra Manulife Mid Cap Fund | 59 | Equity-only partial | Exact issuer table; 16 sector subtotals and the reported 97.71% equity total reconcile |
| Invesco India Mid Cap Fund | 43 | Complete | Official monthly workbook; parser reconciliation passed |
| Sundaram Mid Cap Fund | 79 | Complete | Exact MC workbook, sheet MIDCAP; its own reporting date is August 31 |

**Kotak is not counted in current production coverage.** The isolated pre-merge source check succeeded with 68 equity positions, 23 sectors and a 96.48% equity total. However, the production response failed with `Factsheet lacks the exact staged scheme heading`. This demonstrates response variability, not a completed production recovery. Keep the exact identity/date gates; do not copy preflight counts into the production report or label this source healthy merely because the workflow succeeded.

### Sundaram: separate portfolio reporting from AUM metadata

The discovery card's `AUMASONDATE` is **31-Jul-2026**, while its published Mid Cap workbook independently reports **2026-08-31**. PR #287 validates the exact scheme name, fund code **MC**, category and approved first-party workbook URL, then requires the workbook parser to prove the portfolio date. It neither relabels the July AUM nor treats a newer NAV date as portfolio evidence.

Verified source: `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx`; workbook SHA-256 `7cc4431867469382f3559c54bd12e0fbecb9586d6ddcd4bc02ba2bd7941894f0`. Discovery source and its separate hash are retained in batch 5. A stale or malformed workbook still fails even when the card has a current AUM date; PDF/HTML responses are explicit parser gaps.

### Mahindra: preserve correction history and strengthen reconciliation

The original report counted **63 positions**, including four non-security sector headings: Consumer Services, Healthcare, Power and Services. PRs #285–#286 corrected this to **59 issuers**, accepted only the observed issuer-marker legend after an explicit 100% Grand Total, and continued to reject unknown post-total text, malformed weights, duplicates and conflicting responsive copies.

PR #287 preserves those guards and additionally requires the existing issuer classifier and the new structural sector-table parser to agree. Sector subtotals and the equity total must reconcile before any holdings are returned. Valid CSS sector styling is distinguished from the publisher's invalid `f ont-weight`/`fo nt-weight` issuer styling without repairing the latter into sector labels. The 59 weights sum to **97.71%**; the result remains `factsheet_equity_only`, `complete=false` because other assets are excluded.

Current versions: `mahindra-midcap-issuer-rows-v2` and `sector-equity-reconciliation-v1`. Source SHA-256: `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`. The original audit and correction history remain in [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md). This is a parser correction, not a trade or publisher portfolio change.

## Safety and operational boundaries

Mid Cap remains `stage=staged`. These audit changes promote no Mid Cap portfolios, holdings or metrics into live tables and alter no public UI or financial calculations. The full daily workflow still performs its normal Small Cap/archive maintenance; do not describe the entire production workflow as making zero database writes.

The new `.github/workflows/midcap-evidence.yml` checks Mid Cap changes before merge with read-only repository permissions, locked dependencies, syntax and full regressions. On its designated development-branch pushes it also runs `scripts/check_midcap_batch5_evidence.py`: actual AMC requests use `archive=False`, database access is forbidden, and only committed source registrations are used. The separate source-contract probe remains manual-only. Neither source check publishes financial data.

The owner's daily launch-readiness check is separately enabled in ChatGPT and cannot change code, merge or publish. Its push and email notifications were disabled when checked on 2026-09-28; do not promise delivery through those disabled channels. Do not create duplicate tasks.

## Next coherent task: make readiness freshness-safe

**Do this before another coverage expansion or reporting-month rollover. It is not fixed by PR #287.** Harden `tracker/midcap_portfolio_readiness.py` and the launch-report inputs without changing the existing launch thresholds.

The current reconciler chooses complete/larger snapshots before comparing dates and counts any non-null `as_of` as current. It also drops source hashes and observation times from the combined view. A synthetic reproduction confirmed that a complete July 31 snapshot defeats a partial August 31 snapshot when August is required. The accepted production rows inspected for this checkpoint all report August 31; this finding is not evidence that today's 16-family count is stale. The risk is misleading readiness when retained artifacts span reporting periods or an upstream audit fails.

Acceptance criteria:

1. Re-evaluate freshness against a deterministic current expected month-end. Reject future/malformed dates and stale retained artifacts from current coverage while retaining diagnostic reasons and historical evidence.
2. Add a regression proving complete July cannot defeat current partial August. Cover month/year rollover and the repository's existing grace-period policy without changing that policy.
3. Validate input shape, exact family ownership, successful evidence status and positive named-position counts. Retain source hashes, source identity and observation times. A newly generated summary must not make an older source observation new.
4. Ensure missing/failed upstream artifacts cannot silently make launch readiness green. Distinguish reported benchmark identity from actual benchmark-series availability; never silently substitute the Small Cap comparator.
5. Preserve the disabled public switch. Run full pre-merge regressions, inspect refreshed production evidence and verify the exact deployment before updating this handoff.

After this reliability slice, resume exact first-party benchmark recovery and the remaining portfolio families. Kotak requires a dependable exact fund-specific response; preserve its successful preflight as diagnostic context, not production coverage. Sundaram is now recovered and must continue to be dated by its workbook. Keep Bandhan, Bank of India and WhiteOak TER limitations explicit.

## Publication still requires a separate dry run

Before deliberate launch, implement and validate category-aware exporter/static JSON/API/UI routing, actual holdings and metric evidence, source/freshness/partial labels, benchmark handling and Small Cap non-regression. Staged audit counts are not a substitute for exportable financial records. The launch report itself never enables the category.

## Source-of-truth artifacts

- `docs/MIDCAP-PORTFOLIO-BATCH5.json`: detailed source results, reporting/observation dates, hashes, parser versions and current errors.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and `.md`: combined portfolio evidence and completeness counts.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and `docs/MIDCAP-TER-READINESS.json`.
- `docs/MIDCAP-LAUNCH-READINESS.json`: threshold evaluation, not a launch switch.
- `deployment/midcap-history-status.json`: staged NAV-history status.
- `deployment/update-status.json`: publication/build state, distinct from source coverage.
