# Smallcap Ledger storage cleanup

## Completed and deployed

PR #108 was merged as `64e16f1ff426ed8d3ccd0a82af9c1d3a78db3f07`. Production workflow **36091631221 (#474)** succeeded, including compaction, regression tests, website/data validation, durable archive publication and GitHub Pages deployment. Independent read-only verification **36091796360** succeeded at **2026-09-25 03:47:48 UTC** (September 24 in America/Toronto).

The live website reports build **2026-09-25T03:46:14+00:00**, matching the committed deployment audit. Homepage, fund directory, a representative fund detail/NAV series (code 154215) and its CSV download were fetched successfully. Live coverage remains 36 funds / 143 NAV plans, 281,442 NAV points, AUM and fee coverage 36/36, and portfolio coverage 35/36 (28 complete, 7 partial).

## Measured savings

| Storage | Before | Published after | Reduction |
| --- | ---: | ---: | ---: |
| SQLite database | 100,773,888 bytes | 73,322,496 bytes | 27,451,392 bytes / 27.24% |
| Compressed database checkpoint | 12,851,483 bytes | 7,451,756 bytes | 5,399,727 bytes / 42.02% |

The production ZIP differs by 10 bytes from the validation-copy ZIP because the normal production initialization applies existing document-classification maintenance before compaction. Production preservation is verified against the actual production migration fingerprints, not an earlier staging copy.

These percentages apply to the database and its compressed checkpoint, **not the full source archive**. The live logical storage total is 2,235,842,164 bytes: 73,322,496 database bytes plus 2,162,519,668 bytes of original sources. Release rollback/legacy copies are separate from this logical total.

## What changed and what stayed

The four NAV/benchmark current and observation tables now use composite-primary-key `WITHOUT ROWID` storage instead of redundant rowid/composite-index storage. Free pages were reclaimed. The migration preserved every logical value, date, source, correction and row in **18 tables / 629,225 rows**, verified by sorted-content SHA-256 fingerprints immediately before and after the production migration. New databases use the compact layout.

All **2,519 original source files** and **95 source packs** remain. No fund plan, financial metric, holding, NAV/benchmark observation, original disclosure or source-retention policy was removed by this cleanup. The UI, fund scope and daily schedule are unchanged. Existing initialization/classification and portfolio-retention behavior was not expanded.

The daily pipeline runs `scripts/compact_database.py --apply --report deployment/storage-layout-v1.json` before tests/export/publication. Unknown schemas or dependencies fail closed, fingerprint mismatch rolls the transaction back, and the first migration evidence is retained rather than overwritten by nightly no-ops.

## Validation and recovery

**273 tests passed**, including 14 new migration tests covering rollback, idempotence, constraints, dependencies, correction history, post-migration updates and source preservation. Integrity checks, foreign-key checks, checkpoint restore and generated-site/download checks passed.

The published ZIP was independently downloaded, its size/SHA-256 checked, its database opened and checked for integrity/foreign-key violations, and every table fingerprint compared with the production migration report. The published database matched exactly.

Current checkpoint: `database-36091631221-1.zip`, SHA-256 `83b22717df940e94aa0423ca216dfa5e1849bfb5b94b8cd183a6c9c530e97d73`.

Retained rollback checkpoint: `database-36087719595-1.zip`, SHA-256 `05fba67c4818f3285b332696161dce2f1ad969f8ba5768106f5e66487c32736e`, with the shared source packs. The production publisher's normal current/previous recovery behavior remains active.

## Unperformed archive retirement

The audit identified unreferenced legacy release asset `state-35791406887-1.zip`, **1,087,514,828 bytes**. It has **not been deleted or replaced**. The legacy-archive cleanup tool action was blocked; no storage saving from it is claimed. Its continued existence and unchanged size were checked after deployment. Its exact database snapshot and every unique source must be preserved and verified before any retirement. Do not mark this item completed.

## Evidence and next handoff

- `docs/STORAGE-AUDIT.json`: initial read-only database/release audit.
- `docs/STORAGE-VALIDATION.json`: production-copy migration, restore and full regression validation.
- `deployment/storage-layout-v1.json`: actual production migration and all-table fingerprints.
- `deployment/storage-live-verification.json`: independently checked published archive, rollback checkpoint and live endpoints.

`docs/HANDOFF.md` points to this completion record and retains all previous backend context. Database compaction is complete; legacy archive retirement remains unresolved. Resume the previously documented portfolio source-recovery work, without treating partial source disclosures as complete portfolios.
