# Mid Cap freshness-safe readiness implementation plan

> **For agentic workers:** use superpowers:executing-plans to implement this plan task by task. This plan is complete; resume from the current handoff, not from the original unchecked task list.

**Goal:** Prevent old, malformed or unverified retained audit evidence from making Mid Cap launch readiness green.
**Architecture:** Keep the existing month-end/grace policy. Reconcile validated source rows by reporting date before completeness, preserving provenance and diagnostic alternatives. Verify audit generation against an explicit current-run start at file boundaries; independently re-evaluate portfolio freshness at the launch boundary.
**Tech stack:** Existing Python/stdlib, unittest, GitHub Actions. No new dependencies.
**Spec:** The freshness-safe readiness acceptance criteria in docs/MIDCAP-HANDOFF.md at the PR #289 checkpoint; the current handoff records completion and the next source-coverage task.

## Global constraints
Preserve launch thresholds (100% AUM/NAV, >=90% TER/benchmark, >=80% current portfolio); keep public export disabled; no promotion of live Mid Cap financial records or changes to original evidence, source access or UI. Preserve PR #287's parser corrections. The full publishing workflow continues normal Small Cap/archive maintenance and is not a zero-database-write process.

## Review focus
Malformed/future timestamps; missing explicitly supplied batch files; failed collectors leaving same-day old files; month/year/leap-year rollover with the existing 10-day grace; truthful partial-source labels and retained provenance.

## Tasks
- [x] Reproduce older-complete precedence, stale-current counting and dropped provenance in three failing behavioral regressions against the existing module.
- [x] Implement validated, deterministic portfolio reconciliation and test malformed dates, ownership/status, counts, provenance, immutable inputs and rollover. Retain excluded evidence with reasons.
- [x] Add a shared audit-file reader, a current-run boundary in daily.yml, and explicit required upstream checks in both CLIs. Test missing/invalid/old files, zero-result successful reports, and future timestamps.
- [x] Make the launch evaluator independently recompute current portfolio counts and reject unverified/mismatched input health; preserve thresholds and the public-surface gate. Test falsely green summaries and clock rollover.
- [x] Run focused local tests, syntax checks and the full repository PR regression workflow before merge; review the patch; verify production artifacts/deployment; update the handoff.

## Execution ledger

Starting base: `69cde3417ae8c7144d8e43b36fdf488381f52162`. At the start, publisher run #646 was in progress; its generated reports and the newer handoff were preserved rather than overwritten.

Implementation: PR **#290**, head `0632014d2b8672f91057c5a54b0254f3bfd6dd24`, merged as `85642b293bd496e827eac3aa6ad50c5f59a13426`.

Pre-merge verification:
- 42 focused local tests passed in the earlier isolated scratch environment; this was not the full repository suite.
- [PR regression 36380319806](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319806): syntax checks and **631 tests passed**, 38 more than the previous 593-test checkpoint.
- [Research UI checks 36380319795](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319795): passed. The dedicated public-source preflight was skipped in this PR run; no rerun is claimed.
- The merged diff contains only the readiness modules/commands, related tests, this plan and a two-line audit-boundary workflow addition. No AMC collector or public UI code changed.

Production verification:
- [Run #647 / 36380625528](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380625528): **build and deploy completed successfully on 2026-09-28**. Regressions, site generation, generated-data/download validation and archive publication passed.
- Generated artifacts inspected at `9a370aa85e67936d016659b7d2c1ebd5fc62d372`.
- Portfolio evaluation: `2026-09-28T05:15:45.365686+00:00`; launch evaluation: `2026-09-28T05:15:45.442468+00:00`; expected portfolio date: `2026-08-31`.
- All **14 input-health checks passed**, `input_issues=[]`, `audit_input_integrity=true`. Portfolio reconciliation reports all supplied inputs verified.
- Current portfolios remain **16/34**, complete current portfolios **4/34**. The combined rows retain source/workbook hashes, member identity and source observation timestamps separately from summary evaluation timestamps.
- Launch remains blocked: AUM **34/34**, Direct TER **30/34**, reported benchmark identities **12/34**. NAV history remains **135/135** codes with zero history failures. `data_ready=false`, `launch_ready=false`, `public_export_enabled=false`.
- The new TER gap is **Samco Mid Cap Fund**, in addition to Bandhan, Bank of India and WhiteOak. Both dedicated first-party batches succeeded (7/7 and 3/3); Samco is not a target in those batches. The source-level cause is not yet proven. Do not repeat the older 31/34 TER total.
- Public production status remains **36 Small Cap families**, **143 plans**, AUM and fee coverage **36/36**, latest NAV **2026-09-25**. Direct public-site/browser access failed here; no visual/mobile pass is claimed.

Ruling: local GitHub DNS was unavailable during implementation, so the focused scratch suite was supplemented by full repository CI before merge. Do not relabel focused tests as full-suite verification.

Ruling: a newer closed-month snapshot during the existing grace window remains current; intramonth and future rows never count as monthly coverage. Valid stale rows remain visible but non-current.

Ruling: current-run file integrity and individual source coverage are separate. The 14 passing artifact checks do not erase Samco's TER gap or Kotak's portfolio gap. Address Samco in the next source-repair slice, preserving unavailable values and existing launch thresholds until fresh evidence is verified.

Ruling: the public category-aware dry run and actual benchmark-series handling remain separate launch work. This reliability patch neither completes nor bypasses them.

## Handoff

`docs/MIDCAP-HANDOFF.md` now records this completed checkpoint, the corrected current 30/34 TER count and the next priority: investigate/recover Samco TER evidence, then resume first-party benchmark-identity coverage and the remaining current portfolios. Use the latest machine-readable reports and exact production run on every continuation.
