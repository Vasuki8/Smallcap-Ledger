# Mid Cap backend handoff

This is the focused continuation handoff for Mid Cap work. Historical README handoff entries remain an implementation history; use this file together with the latest generated readiness reports and GitHub Actions results for the current state. Never use an older successful audit to claim that a newer collector or publisher passed.

## Current code and verification

- PR #283 introduced portfolio batch 5 for Kotak, JM, Mahindra Manulife, Invesco and Sundaram.
- PR #284 fixed JM's exact monthly title-date parsing. Its production run `36375282524` completed successfully.
- Review of that run's retained batch-5 report found four Mahindra sector headings incorrectly counted as securities. The details, original audit commit and exact source hash are recorded in [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md).
- PR #285 corrects issuer/sector separation and Sundaram's plain date-field parsing. Merge commit: `240176139b40abce7cf7710f9ea7a09b17f91d9f`.
- All **564 tests passed before merge**, including **22 new parser/integration regressions**. PR verification: [run 36376275507](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36376275507).
- Production verification for PR #285 is [run #644 / 36376355823](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36376355823). At this document's preparation the refreshed staged audits had completed, but final publication verification was still pending. Replace this status with terminal results before merging this handoff.

## Scope and safety

The new Mahindra parser reads the exact published portfolio columns, excludes sector totals, retains explicitly reported issuer weights and fails closed on missing values, unknown row types, duplicate issuers or conflicting responsive copies. It records parser version `mahindra-midcap-issuer-rows-v1` and remains partial.

Sundaram's `AUMASONDATE` is parsed as a date field, but the downloaded portfolio must independently establish its own exact family and reporting date. A PDF is an explicit unsupported-parser case, not an HTML table and not verified portfolio coverage.

Mid Cap remains `stage=staged`, `public_export_enabled=false`. This change does not write Mid Cap portfolios or holdings into the live tables and does not alter Small Cap UI or calculations. The existing full daily publication workflow still performs its normal Small Cap/archive maintenance.

## Launch policy remains unchanged

For 34 staged families: AUM 34/34, Direct TER at least 31/34, exact reported benchmark identity at least 31/34 and current portfolio evidence at least 28/34. Complete current portfolios are a separate measure: a partial view must never be labelled complete.

The data thresholds alone do not authorize launch. A category-aware exporter/static JSON/API/UI dry run, verified source and date handling, and successful regression/publication checks remain mandatory before a deliberate public switch. The launch report cannot enable Mid Cap itself.

The owner's requested daily launch-readiness check is scheduled separately in ChatGPT. It is read-only, checks current repository evidence and alerts only when launch conditions are newly met; it has no authority to change code or publish.

## Next work

1. Close this run by reading the regenerated batch-5, portfolio-readiness and launch-readiness JSON files after terminal workflow success. Verify that Mahindra no longer contains sector headings and record the accepted count without treating the correction as a trade.
2. Harden readiness aggregation before the next reporting-month rollover. `tracker/midcap_portfolio_readiness.py` currently chooses complete/larger snapshots and counts any non-null `as_of`; it does not independently recheck the current expected month. Add deterministic tests preventing stale retained artifacts, future dates or malformed rows from increasing current coverage. Preserve source hashes and observation times in reconciled evidence. This risk is not fixed by PR #285.
3. Continue exact first-party portfolio and benchmark recovery. Resolve Kotak's actual returned page identity through a verified current factsheet/workbook route rather than weakening the family gate. For Sundaram, use the newly exposed source type/error to choose a dedicated parser instead of interpreting a current AUM date as portfolio proof.
4. Prioritize benchmark coverage alongside portfolio recovery; the prior launch report still had only 12/34 reported benchmark identities. Keep Bandhan, Bank of India and WhiteOak TER as explicit source limitations rather than substituting values.
5. Keep the next patch narrow, run the full PR regression workflow before merging, verify its exact production run and update this handoff afterwards.

## Source-of-truth artifacts

- `docs/MIDCAP-PORTFOLIO-BATCH5.json`: detailed batch-5 source results and errors.
- `docs/MIDCAP-PORTFOLIO-READINESS.json`: combined current/complete portfolio counts.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and `docs/MIDCAP-TER-READINESS.json`.
- `docs/MIDCAP-LAUNCH-READINESS.json`: threshold evaluation, not a launch switch.
- `deployment/midcap-history-status.json`: staged NAV history status.
- `deployment/update-status.json`: publication/build status, distinct from staged source coverage.
