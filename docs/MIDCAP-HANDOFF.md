# Mid Cap backend handoff

This is the focused continuation handoff for Mid Cap development. Historical README handoff entries remain implementation history; use this file together with current generated readiness reports and GitHub Actions results. Never use an older successful audit to claim that a newer collector passed.

## Latest verified checkpoint

- Code changes: **PR #285** (issuer/sector separation and Sundaram date-field parsing) and **PR #286** (the verified Mahindra post-total legend).
- Latest code merge: `399dc73a01a53b7317fd5493e141792332ccb24a`.
- Production: [run #645 / 36377452770](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377452770), **completed successfully on 2026-09-28 at 04:30:48 UTC**.
- Both build and deploy jobs passed. Checked stages include regression tests, site generation, generated-data/download validation, cumulative archive publication, status recording and Pages deployment.
- Generated evidence commit: `a3895a2ef254fd0f2043bddee51b26669f0e7282`.
- Batch-5 and combined portfolio reports were generated at **2026-09-28T04:27:15+00:00**; their reporting month-end is **2026-08-31**. Observation, reporting and publication times are distinct.
- Final PR regression verification: [36377345548](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36377345548), **570 tests passed before merge**. This slice adds **28 tests** across the two corrective PRs. A separate first-party source probe verified the actual HTML before PR #286 was merged.

Verification scope: repository evidence, full PR regressions, actual first-party source response, generated production reports and terminal build/deploy results. Direct browser-level website smoke testing was unavailable in this environment; no visual/mobile pass is claimed.

## Current staged readiness

| Measure | Verified count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history coverage | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 families | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | 12 / 34 | At least 31 / 34 |
| Current portfolio evidence | 15 / 34 | At least 28 / 34 |
| Complete current portfolios | 3 / 34 | Separate measure; do not relabel partials |

The three complete current portfolios are **HDFC, Mirae Asset and Invesco India**. The latest generated launch report remains **data_ready=false**, **launch_ready=false** and **public_export_enabled=false**. At current counts, the data thresholds need **19 more reported benchmark identities** and **13 more current portfolio-evidence families**, followed by the category-aware public-surface dry run.

These are product-quality thresholds, not regulatory rules. Passing counts alone does not authorize launch, especially while freshness aggregation still requires hardening below.

## Batch 5: verified outcomes and remaining gaps

All accepted batch-5 results report **2026-08-31**:

| Family | Named positions | Completeness | Evidence |
| --- | ---: | --- | --- |
| JM Mid Cap Fund | 72 | Partial | Official monthly workbook; CCIL remains an unclassified row |
| Mahindra Manulife Mid Cap Fund | 59 | Partial | Exact digital factsheet issuer table; sectors and totals excluded |
| Invesco India Mid Cap Fund | 43 | Complete | Official monthly workbook; parser reconciliation passed |

**Kotak** remains unresolved because the runner's returned factsheet page does not pass the exact staged-family identity gate. **Sundaram** remains unresolved because the fund-card reporting field resolves to **2026-07-31**, not August 31. Do not describe either as recovered merely because the workflow step completed successfully.

### Mahindra correction

The earlier report counted **63 positions**, including four non-security sector headings: Consumer Services, Healthcare, Power and Services. The corrected list has **59 actual issuers** and their weights total **97.71%**, matching the source's equity total. It remains partial because it is an issuer-only view, not a complete cash-inclusive record.

PR #285 initially withheld Mahindra rather than accepting an unknown one-cell row. The actual source probe proved that row was an issuer-marker legend after Grand Total. PR #286 accepts only that exact footer after an explicitly verified 100% total; unknown text, malformed weights, duplicate issuers and conflicting table copies still fail closed. Current parser: **`mahindra-midcap-issuer-rows-v2`**.

The original audit, source hash, four excluded aggregates, source probes and regression history are preserved in [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md). This is a parser correction, not a trade or a publisher portfolio change.

## Safety boundaries

Mid Cap remains `stage=staged`. No Mid Cap portfolio/holding was promoted into live tables and no public Mid Cap page was enabled. These changes do not alter Small Cap UI or financial calculations; the full daily workflow continues its normal Small Cap/archive maintenance.

Sundaram's AUM date is discovery metadata only. Any portfolio file must independently prove its exact family and reporting date. A PDF is an explicit unsupported-parser case until verified, never HTML by assumption.

The source-contract probe is **manual-only**, with read-only repository permissions and no financial-data/publication writes. The owner's requested daily launch-readiness check is scheduled separately in ChatGPT: it reads current repository evidence and alerts only when launch conditions are newly satisfied. It cannot modify code, merge or publish.

## Next coherent task: make readiness freshness-safe

Before another coverage expansion or reporting-month rollover, harden `tracker/midcap_portfolio_readiness.py` and the launch-report inputs. This risk was identified during review and **is not fixed by PRs #285–#286**.

The current reconciler chooses complete/larger snapshots before comparing dates and counts any non-null `as_of` as current. It also drops source hashes and observation times from the combined view. The present accepted rows all report August 31, so this finding is not evidence that today's 15-family count is stale; the problem is that future retained/mixed-period inputs can produce a misleading readiness result.

Acceptance criteria for the next patch:

1. Re-evaluate reporting freshness against a deterministic current expected month-end. Reject future/malformed dates and stale retained artifacts from current coverage, preserving diagnostic reasons rather than erasing prior evidence.
2. Prove with a regression that a complete July 31 snapshot cannot defeat a partial August 31 snapshot when August is required. Cover month/year rollover and the repository's existing grace-period policy without changing that policy.
3. Validate input shape, family ownership, successful evidence status and positive named-position counts. Retain source hashes, source identity and observation times through reconciliation. A newly generated summary must not make old source observations new.
4. Ensure missing or failed upstream audit artifacts cannot silently make the launch gate green. Benchmark identity is not benchmark-series availability; the public dry run must use the correct series or explicitly show its absence, never a silent Small Cap comparator.
5. Preserve all existing launch thresholds and the disabled public switch. Run the full PR suite before merge, verify the exact production run and update this handoff.

After this reliability slice, resume exact first-party benchmark recovery and the remaining portfolio families. Revisit Kotak only through a verified fund-specific source; seek a current Sundaram disclosure rather than relaxing its date gate. Keep Bandhan, Bank of India and WhiteOak TER limitations explicit.

## Publication still requires a separate dry run

Before any deliberate launch: implement and validate category-aware exporter/static JSON/API/UI routing, actual holdings and metric evidence, source/freshness/partial labels, benchmark handling, and Small Cap non-regression. Staged audit counts are not a substitute for exportable financial records. The launch report itself never enables the category.

## Source-of-truth artifacts

- `docs/MIDCAP-PORTFOLIO-BATCH5.json`: detailed source results, parser version and errors.
- `docs/MIDCAP-PORTFOLIO-READINESS.json`: combined portfolio evidence and completeness counts.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and `docs/MIDCAP-TER-READINESS.json`.
- `docs/MIDCAP-LAUNCH-READINESS.json`: threshold evaluation, not a launch switch.
- `deployment/midcap-history-status.json`: staged NAV-history status.
- `deployment/update-status.json`: publication/build state, distinct from source coverage.
