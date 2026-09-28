# Mid Cap freshness-safe readiness implementation plan

> **For agentic workers:** use superpowers:executing-plans to implement this plan task by task.

**Goal:** Prevent old, malformed or unverified retained audit evidence from making Mid Cap launch readiness green.
**Architecture:** Keep the existing month-end/grace policy. Reconcile validated source rows by reporting date before completeness, preserving provenance and diagnostic alternatives. Verify audit generation against an explicit current-run start at file boundaries; independently re-evaluate portfolio freshness at the launch boundary.
**Tech stack:** Existing Python/stdlib, unittest, GitHub Actions. No new dependencies.
**Spec:** docs/MIDCAP-HANDOFF.md, “Next coherent task: make readiness freshness-safe”.

## Global constraints
Preserve launch thresholds (100% AUM/NAV, >=90% TER/benchmark, >=80% current portfolio); keep public export disabled; no live financial records, original evidence, source access or UI changes. Preserve PR #287's newer parser corrections.

## Review focus
Malformed/future timestamps; missing explicitly supplied batch files; failed collectors leaving same-day old files; month/year/leap-year rollover with existing 10-day grace; truthful reporting of partial sources and retained provenance.

## Tasks
- [x] Reproduce older-complete precedence, stale-current counting and dropped provenance in three failing behavioral regressions against the existing module.
- [ ] Implement validated, deterministic portfolio reconciliation and test malformed dates, ownership/status, counts, provenance, immutable inputs and rollover. Retain excluded evidence with reasons.
- [ ] Add a shared audit-file reader, a current-run boundary in daily.yml, and explicit required upstream checks in both CLIs. Test missing/invalid/old files, zero-result successful reports, and future timestamps.
- [ ] Make the launch evaluator independently recompute current portfolio counts and reject unverified/mismatched input health; preserve thresholds and public-surface gate. Test falsely green summaries and clock rollover.
- [ ] Run focused local tests, syntax checks, review the patch, run the full repository regression workflow before merge, then verify production artifacts/deployment and update the handoff.

## Execution ledger
Base: 69cde3417ae8c7144d8e43b36fdf488381f52162. A newer publisher run #646 is in progress; do not overwrite its generated reports.
Ruling: container cannot resolve github.com, so local unit verification uses connector-read source modules in an isolated scratch tree. The complete repository suite must run in PR CI before merge; do not describe the scratch test set as the full suite.
Ruling: a newer closed-month snapshot during the existing grace window remains current; no intramonth or future row counts as monthly coverage. Valid stale rows remain visible, but are not current.
