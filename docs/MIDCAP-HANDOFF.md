# Mid Cap backend handoff

This is the focused continuation handoff. Use it together with the current generated reports, exact code commit and GitHub Actions results. Historical README entries are implementation history, not current source coverage. Never use an older successful audit, a summary timestamp, or a separate preflight to claim a newer production collector passed.

## Latest verified checkpoint

- Latest change: **PR #290**, merged as `85642b293bd496e827eac3aa6ad50c5f59a13426`. It preserves the preceding PR #287 source/parser corrections and updates only readiness aggregation, audit inputs, tests and the generation boundary.
- Pre-merge head: `0632014d2b8672f91057c5a54b0254f3bfd6dd24`. Both [Research UI checks / 36380319795](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319795) and [Mid Cap evidence regression / 36380319806](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319806) passed. The latter logged **631 tests / OK** in job 108794569077.
- Exact production: [run #647 / 36380625528](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380625528), **completed successfully on 2026-09-28 at 05:19:37 UTC**. The regression, generated-data validation, archive publication and status-recording steps passed; deploy job 108797719489 completed successfully at 05:19:36 UTC.
- Refreshed reports were inspected at commit `9a370aa85e67936d016659b7d2c1ebd5fc62d372`. Portfolio evaluation is **2026-09-28T05:15:45.365686+00:00**; launch evaluation is **05:15:45.442468 UTC**. The accepted portfolios report **2026-08-31**. Original source observation times and hashes are retained separately.
- All **14 required input artifacts** passed generation/integrity checks; the launch report has `input_issues=[]` and `audit_input_integrity=true`. This does not mean every underlying fund source has data: the latest TER audit has an additional Samco gap, described below.

Verification scope: deterministic bug reproductions, 42 focused local tests, uploaded-source hash checks, both full PR CI suites, and the exact production run and refreshed artifacts described above. The local scratch tree is not a complete repository checkout because container GitHub DNS was unavailable; the full repository test result comes from GitHub Actions. No browser-level visual/mobile pass is claimed.

## Completed reliability slice: freshness-safe readiness

PR #290 fixes the handoff's freshness-aggregation task without changing source parsers, launch thresholds or the public switch.

- Reporting date is compared **before** completeness or position count. A complete July 31 portfolio cannot displace a partial August 31 portfolio when August is required. Completeness and position count resolve same-date alternatives only.
- The current expected reporting month-end is calculated at an explicit, timezone-aware evaluation clock using the existing **10-day publication grace**. The grace policy is unchanged. A newer already-closed month can qualify during grace; an intramonth, future or unclosed-month observation cannot qualify as monthly portfolio evidence.
- Valid older rows stay visible with `current=false` and `freshness_status=stale`; they do not increase current or complete-current coverage. Invalid and alternate evidence is retained separately with diagnostic reasons rather than erased.
- Accepted rows must have exact staged family and AMC ownership, `status=recovered`, at least five named-position observations, a real boolean completeness flag, a HTTPS source, SHA-256 source identity and valid reporting/observation times. Source hashes, workbook hashes, source URLs, sheet/entry identities, original observation times and available positions survive reconciliation unchanged.
- A generated summary has its own `built_at`/`evaluated_at`; it does not replace source `observed_at`. Portfolio and launch reports now use **schema version 2**.
- Before the staged audits, the workflow exports one `MIDCAP_AUDIT_STARTED_AT` boundary. The file reader checks bytes/hash, shape and original generation time against that run, rejecting missing, malformed, failed, future or older retained reports. A same-day checked-in report still fails when it predates this run.
- The launch command checks **14 files**: five core reports and all nine producing TER/benchmark/portfolio batches. A newly generated combined summary cannot hide an old producing batch.
- A supplied-but-missing portfolio batch is an explicit input error, not silently skipped. Missing launch inputs produce a fresh blocked report with reasons instead of leaving an older green report in place. Existing collector/source gaps remain explicit; a successful workflow is not evidence that every fund source was recovered.
- The launch evaluator independently re-evaluates portfolio source rows at its own clock instead of trusting retained counts or `current` flags. `audit_input_integrity` must pass, in addition to the unchanged data and public-surface gates.

Acceptance evidence includes month/year rollover, leap years, same-date tie-breaking, invalid/future dates, malformed identity/status/counts, missing/nonfinite input files, failed/retained batches, provenance immutability and falsely green launch summaries. Thirty-eight net additional tests bring the full repository suite from 593 to 631.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 families | 34 / 34 |
| Direct TER | **30 / 34** | At least 31 / 34 |
| Reported benchmark identity | 12 / 34 | At least 31 / 34 |
| Current portfolio evidence | 16 / 34 | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Separate measure; partials remain partial |
| Audit input integrity | 14 / 14 verified; no input issues | All required inputs verified |

The four complete portfolios are **HDFC, Mirae Asset, Invesco India and Sundaram**. All 16 accepted current portfolio rows report August 31, 2026. This reliability slice does not claim new source recoveries.

**TER must now be reported as 30/34, not the older 31/34 checkpoint.** The latest run recovered 20 AMFI families plus all 10 first-party AMC families. Samco Mid Cap joins Bandhan, Bank of India and WhiteOak as a current unresolved TER gap. The latest AMFI gap audit records zero rows for Samco's exact AMC/category queries for July, August and September 2026, with no overall AMFI fetch error. That is this run's observation, not proof that Samco publishes no TER elsewhere or that its scheme identity changed. Preserve the older evidence as history; do not copy its count/value into the current successful-source tally.

Launch remains **data_ready=false**, **launch_ready=false**, **public_export_enabled=false**. The data thresholds need **one additional Direct TER family, 19 additional reported benchmark identities and 12 additional current portfolio-evidence families**, followed by the category-aware public-surface dry run. Input integrity and NAV/AUM checks pass; those do not override the remaining coverage blockers.

The public category remains disabled. These are product-quality thresholds, not regulatory rules. Reported benchmark identity is not benchmark-series availability, and staged readiness counts do not prove that all underlying data is already exportable to public fund pages.

## Preserved source corrections and limitations

PR #290 preserves PR #287's collector changes and the earlier #285-286 safeguards. The preceding verified checkpoint was production run #646 / 36378611855 (code `69cde3417ae8c7144d8e43b36fdf488381f52162`), which reported 16 current portfolio families and four complete current portfolios.

**Mahindra Manulife:** the original 63-position result included four sector headings as securities. The corrected view has 59 issuers. Its 16 sector subtotals and 97.71% equity total must reconcile independently; it remains equity-only partial, not a cash-inclusive complete portfolio. The verified post-total marker legend is accepted only after the total, while unknown footer text, invalid weights, duplicate issuers and conflicting responsive tables fail closed. Versions: `mahindra-midcap-issuer-rows-v2` and `sector-equity-reconciliation-v1`. Original source SHA-256: `53374413ff5f8e68e1a009cf3ce80517707d232348dd3d6c36a80bc8a58ab640`. Correction history remains in [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md); this was a parser correction, not a trade.

**Sundaram:** the discovery card's July 31 AUM date does not establish the portfolio date. The approved exact MC workbook independently reports August 31. Preserve fund-code/category checks and require the portfolio parser to prove its own date. The previously verified 79-position complete workbook is `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx`, SHA-256 `7cc4431867469382f3559c54bd12e0fbecb9586d6ddcd4bc02ba2bd7941894f0`. A stale/malformed workbook still fails even when AUM metadata looks current; PDF/HTML responses are explicit parser gaps.

**Kotak:** the preflight once recovered 68 equity positions, 23 sectors and a 96.48% equity total, but the preceding production response failed the exact scheme-heading gate. Treat that preflight only as diagnostic context. Count a production recovery only when the current generated report verifies the actual returned source; do not weaken ownership/date gates to make the count stable.

**TER:** Bandhan, Bank of India and WhiteOak remain explicitly disclosed first-party access/transport gaps. Samco is a newly observed AMFI zero-row case in run #647, not yet a proven permanent access blocker. Do not repeatedly probe unchanged blocked routes or substitute another scheme's TER merely to increase coverage.

## Operating the new input checks

Normal production supplies `MIDCAP_AUDIT_STARTED_AT` automatically before the staged collectors run. For an isolated local audit, establish a timezone-aware timestamp **before generating the input reports**, then pass `--audit-started-at` to the two readiness commands or export that environment variable. Omitting a boundary intentionally cannot establish launch readiness. Never choose an old boundary simply to make checked-in reports pass.

When adding portfolio batch 6 or another producing batch, update both the relevant CLI and `tracker/midcap_launch_readiness.py::UPSTREAM_FILES` in the same tested change. Required producing files are part of the integrity contract. Preserve the distinction between a failed artifact generation and a valid report documenting unavailable individual fund sources.

The current integrity record verifies artifact bytes/generation against this run. It is not a replacement for per-field reporting dates, authenticated scheme identity, publisher corrections or eventual public-export validation. Keep further benchmark/fee-specific validity work explicit rather than describing file-generation checks as a complete financial-data audit.

## Next coherent task

First **investigate the newly regressed Samco Mid Cap TER evidence**: compare this run with the last successful exact AMFI response and use a current exact first-party Samco TER disclosure if needed. Keep previous reporting dates and correction history; do not alter selectors or identity matching without returned-source proof. This is the new one-family fee-threshold blocker.

Then resume **exact first-party reported benchmark recovery**, the larger coverage deficit, while keeping the new source-row/input-integrity gates in place. Prioritize AMC factsheet/API evidence for the existing Franklin, UTI and JM product-page misses, and use verified ICICI/Axis/Mirae routes where exact scheme benchmark statements are available. Preserve publisher wording, reporting/effective dates and source identity; never infer TRI or default a Mid Cap fund to the Small Cap comparator.

Continue the remaining current portfolio families after each benchmark/source batch passes its own tests and production verification. Kotak needs a dependable fund-specific response; Sundaram's workbook-led date recovery must remain intact. Add/verify Taurus and WhiteOak source registration before claiming category-wide document coverage.

The next public release milestone remains a **separate category-aware exporter/static JSON/API/UI dry run**, only after data coverage and input integrity pass. Validate actual holdings/metric records, source and freshness labels, partial/unavailable states, correct benchmark series or explicit absence, routing and Small Cap non-regression before a deliberate launch. The launch report itself never enables Mid Cap.

## Safety and operations

Mid Cap remains `stage=staged` with `public_export_enabled=false`. This reliability change makes no live Mid Cap financial-data writes and changes no public UI or source access. The full daily publisher still performs normal Small Cap/archive maintenance; do not describe the whole workflow as making zero database writes.

The read-only Mid Cap PR regression workflow, full Research UI checks and manual source probes remain in place. No new dependency, spending, account, permission or external communication workflow was introduced.

The owner's daily launch-readiness check is already configured in ChatGPT; do not duplicate it. It cannot modify code, merge or publish. Its push/email notifications were disabled at the previous inspection, so do not promise delivery through those channels without a new check.

## Source-of-truth artifacts

- `docs/MIDCAP-PORTFOLIO-BATCH1.json` through `BATCH5.json`: detailed source evidence, exact reporting/observation dates, identities and errors.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and `.md`: schema-2 current/stale coverage, original provenance, input checks and excluded evidence.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and `docs/MIDCAP-TER-READINESS.json`, plus their producing batches.
- `docs/MIDCAP-LAUNCH-READINESS.json`: schema-2 threshold and input-integrity evaluation, not a launch switch.
- `deployment/midcap-history-status.json`: staged NAV-history status.
- `deployment/update-status.json`: publication/build state, distinct from source coverage.
- `docs/superpowers/plans/2026-09-28-midcap-freshness.md`: implementation and verification ledger.
