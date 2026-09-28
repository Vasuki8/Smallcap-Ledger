# Mid Cap freshness-safe readiness implementation plan

> **For agentic workers:** use superpowers:executing-plans to implement this plan task by task.

**Goal:** Prevent old, malformed or unverified retained audit evidence from making Mid Cap launch readiness green.
**Architecture:** Keep the existing month-end/grace policy. Reconcile validated source rows by reporting date before completeness, preserving provenance and diagnostic alternatives. Verify audit generation against an explicit current-run start at file boundaries; independently re-evaluate portfolio freshness at the launch boundary.
**Tech stack:** Existing Python/stdlib, unittest, GitHub Actions. No new dependencies.
**Spec:** The pre-PR-290 docs/MIDCAP-HANDOFF.md, “Next coherent task: make readiness freshness-safe”.

## Global constraints
Preserve launch thresholds (100% AUM/NAV, >=90% TER/benchmark, >=80% current portfolio); keep public export disabled; no live financial records, original evidence, source access or UI changes. Preserve PR #287's newer parser corrections.

## Review focus
Malformed/future timestamps; missing explicitly supplied batch files; failed collectors leaving same-day old files; month/year/leap-year rollover with existing 10-day grace; truthful reporting of partial sources and retained provenance.

## Tasks
- [x] Reproduce older-complete precedence, stale-current counting and dropped provenance in three failing behavioral regressions against the existing module.
- [x] Implement validated, deterministic portfolio reconciliation and test malformed dates, ownership/status, counts, provenance, immutable inputs and rollover. Retain excluded evidence with reasons.
- [x] Add a shared audit-file reader, a current-run boundary in daily.yml, and explicit required upstream checks in both CLIs. Test missing/invalid/old files, zero-result successful reports, and future timestamps.
- [x] Make the launch evaluator independently recompute current portfolio counts and reject unverified/mismatched input health; preserve thresholds and public-surface gate. Test falsely green summaries and clock rollover.
- [x] Run focused local tests, syntax checks, review the patch, run the full repository regression workflow before merge, then verify production artifacts/deployment and update the handoff.

## Execution ledger
Base: `69cde3417ae8c7144d8e43b36fdf488381f52162`. At task start, publisher run #646 was in progress. Its generated reports and subsequent handoff changes were preserved rather than overwritten.

Ruling: the container could not resolve github.com, so local verification used connector-read source modules in an isolated scratch tree. The **42 focused local tests** are not the full repository suite. Syntax checks and uploaded file hashes also passed.

Ruling: a newer closed-month snapshot during the existing grace window remains current; no intramonth or future row counts as monthly coverage. Valid stale rows remain visible but are not current. Replaying August evidence at October 11 produces zero current coverage without changing the original observation timestamps.

Pre-merge verification: head `0632014d2b8672f91057c5a54b0254f3bfd6dd24`. [Research UI checks 36380319795](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319795) and [Mid Cap evidence regression 36380319806](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380319806) both passed. Job 108794569077 logged **631 full repository tests / OK**, 38 net tests beyond the previous 593-test checkpoint.

Merged: **PR #290**, `85642b293bd496e827eac3aa6ad50c5f59a13426`. [Production #647 / 36380625528](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36380625528) passed through Pages deployment on **2026-09-28 at 05:19:37 UTC**. Deploy job 108797719489 completed successfully at 05:19:36 UTC.

Refreshed reports were read at `9a370aa85e67936d016659b7d2c1ebd5fc62d372`: schema version 2, all 14 input artifacts verified, no input issues, 16 current portfolio families / 4 complete, 34 AUM, 30 TER, 12 reported benchmark identities. Launch remains false. The handoff records the newly observed Samco AMFI TER gap rather than carrying forward the older 31/34 fee count.

Verification boundary: full CI and actual production audit/publication results were checked. No browser-level visual/mobile test is claimed. This slice changes readiness integrity, not source parsers, public UI, source permissions or live Mid Cap financial records.
