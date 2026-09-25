# Smallcap Ledger storage cleanup

## Validation status

Validated on a restored production copy in GitHub Actions run 36091497740. Production publication is pending.

- SQLite database: 100,773,888 to 73,322,496 bytes; saved 27,451,392 bytes.
- Compressed database checkpoint: 12,851,483 to 7,451,746 bytes.
- 273 regression tests passed, including 14 new migration tests.
- Every logical row in all 18 tables remained identical, verified by sorted-content SHA-256 fingerprints.
- Integrity, foreign-key checks, idempotence, checkpoint restore and generated-site/download checks passed.

## Scope

The four NAV/benchmark current and observation tables use composite primary-key WITHOUT ROWID storage. Current values, alternate observations/corrections, reporting and observation dates, metrics, holdings, source hashes, original binaries and all fund plans remain. New databases use the same compact layout. Unknown schemas and dependencies fail closed. The daily pipeline applies this before tests/export/publication and retains its prior checkpoint for rollback. First production migration evidence is recorded in deployment/storage-layout-v1.json.

## Unperformed archive retirement

The read-only audit identified unreferenced legacy release asset state-35791406887-1.zip, 1,087,514,828 bytes. It has NOT been deleted or replaced. The legacy-archive cleanup tool action was blocked; no space saving from it is claimed. Its exact database snapshot and every unique source must be preserved and verified before any retirement. No source-retention policy or fund-universe scope has changed.

See docs/STORAGE-AUDIT.json and docs/STORAGE-VALIDATION.json for the machine-readable evidence.
