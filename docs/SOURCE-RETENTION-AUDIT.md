# Source-retention audit — proposal only

## Retention-aware infrastructure deployed — still zero deletion

The prerequisite retention-aware storage plumbing is now deployed, but **binary deletion is still disabled and not approved**.

Implementation PR **#146** merged as commit `c522c313fa03359590e2cdd8c9e9235773e19cde`. Production workflow **#505 / 36188792392** safely reached the migration and regression stages, but failed before publication because three legacy test paths used an ambiguous joined `ORDER BY hash` plus one invariant expected a more specific error message. No Pages deployment or new archive checkpoint was published from that failed attempt.

Follow-up PR **#147** merged as commit `742f84f4412e376ba5bb23d8ddb91c25905bb596`. Production workflow **#506 / 36188946719** then completed successfully at **2026-09-25T21:00:46Z** with **349 passing tests**, cumulative-history publication and GitHub Pages deployment.

The authoritative readiness evidence is committed at:

`deployment/retention-readiness.json`

Production readiness snapshot at **2026-09-25T20:59:23Z**:

- current archive hashes: **2,526**
- reviewed historical inventory hashes: **2,519**
- historical link-only candidates: **700**
- new hashes not yet reviewed by the historical audit: **7**
- binary state **retained: 2,526**
- binary state **metadata_only: 0**
- files actually deleted: **0**
- bytes actually deleted: **0**
- source-pack repack performed: **no**
- legacy/rollback assets retired: **no**
- protected archive metadata unchanged: **yes**
- every non-retention table fingerprint unchanged during classification: **yes**
- protected hashes covered by the active source-pack manifest: **yes**
- all 700 historical link-only candidates still covered by the active source-pack manifest: **yes**
- deletion enabled: **no**
- approved for binary deletion: **no**

Stored classifications after reconciliation with the current conservative dependency scan:

| Stored classification | Binary state | Files | Raw bytes |
| --- | --- | ---: | ---: |
| retain_evidence | retained | 984 | 1,292,126,190 |
| retain_latest_or_review | retained | 835 | 465,895,337 |
| link_only_candidate | retained | 700 | 404,498,141 |
| unclassified | retained | 7 | 1,920,223 |

None of the 700 historical candidates was weakened or deleted. The current dependency scan strengthened **0** historical link-only candidates in this run. The 7 newer hashes remain **unclassified + retained** rather than inheriting an old deletion decision.

### What is now retention-aware

The database now carries monotonic per-hash retention metadata with explicit `classification` and `binary_state`. Protected evidence cannot be downgraded. Only a reviewed `link_only_candidate` can ever become `metadata_only`.

Archive downloads, saved document-version links, AMC replay/reprocessing, selective source materialization, checkpoint verification, source-pack planning, Pages publication, and manual cumulative imports now understand binary-retention state. A metadata-only hash cannot appear as a saved downloadable copy or be silently materialized. If identical bytes are fetched again as current evidence, the hash is promoted back to **retain_latest_or_review + retained**.

Old checkpoints without the new table remain backward compatible and are treated as fully retained.

The active source-pack publisher deliberately refuses to publish when an active immutable pack contains a hash newly marked metadata-only. That forces any future reduction to use a separately reviewed **atomic replacement-pack migration** rather than silently orphaning provenance or leaving misleading pack contents.

### Important: this is infrastructure readiness, not deletion authorization

The original **700 candidate binaries / 404,498,141 raw bytes** remain physically retained in the current packs. The legacy cumulative ZIP, current rollback checkpoint and existing reusable source packs remain untouched.

A future reduction still requires a separate approved migration with exact candidate hashes, an isolated replacement-pack dry run, restore/replay/site validation against that proposed manifest, rollback preservation, and explicit approval before any production binary state or release asset is changed.


No archived file, source-pack asset, database row, production policy, schedule or website was changed.

| Classification | Files | Uncompressed bytes | Compressed payload bytes |
| --- | ---: | ---: | ---: |
| retain_evidence | 983 | 1,292,121,482 | 1036713814 |
| retain_latest_or_review | 836 | 465,900,045 | 325054381 |
| link_only_candidate | 700 | 404,498,141 | 34253903 |

Audit time: 2026-09-25T04:06:40+00:00. Checkpoint: `database-36091631221-1.zip`.

Potential link-only reduction: **404,498,141 raw bytes** (18.7049% of originals). **Actual deletion: 0 bytes.**

## Decision rules

Retain all sources tied by hash or exact source URL to financial records; successful historical extractions; dated/narrative AMC publications; literal code/handoff hash dependencies. Original PDFs, workbooks and other downloadable/unknown files remain retained or under review. Protect the latest saved version of every document, independently of later URL fetches, and every exact URL; also protect sources with documented transport boundaries or a latest recorded error.

Only superseded HTML/JavaScript responses with a strictly newer retained version for every associated URL and no identified evidence/replay dependency become link-only candidates. JSON/plain-text responses stay under review because request parameters and data semantics are not fully recorded. These are distinct response snapshots, not verified byte duplicates. Link-only means knowingly giving up old discovery-response bytes while retaining metadata and newer responses.

## Before any deletion

Obtain explicit approval of the exact candidate hashes. Add explicit binary-retention state without deleting provenance metadata. Make restore, verification, reprocessing, archive serving, publication selection and download labels retention-aware. Prevent re-archiving the same discardable responses. Build replacement packs and validate all retained members, sources and the complete website before switching an atomic manifest. Keep rollback packs until independently verified. This audit does not implement those steps.

## Important limits

- Metadata/dependency classification, not a semantic review of every original file.
- No live AMC link availability checks; retained fetch history is dated evidence only.
- Different hashes are different saved bytes, not proven duplicates. Candidate deletion loses those historical response snapshots.
- A URL or SHA-256 cannot reconstruct an overwritten or unavailable document.
- Original PDFs/workbooks and successful historical extractions are protected, including data beyond rolling parsed portfolio retention.
- Compressed payload totals exclude ZIP headers; actual release reduction requires approved repacking and rollback retirement.
- Existing restore, replay and website download code requires retained binaries. No deletion or policy change is enabled by this report.
- Legacy cumulative backup, current rollback checkpoint, repository bootstrap, and published Pages copies are separate and untouched.

## Largest candidate hosts

| Host | Candidate files | Candidate raw bytes |
| --- | ---: | ---: |
| samcomf.com | 71 | 219,887,652 |
| mutualfund.adityabirlacapital.com | 50 | 47,379,014 |
| tatamutualfund.com | 20 | 24,298,711 |
| assetmanagement.hsbc.co.in | 32 | 15,880,362 |
| dspim.com | 42 | 14,332,703 |
| mf.nipponindiaim.com | 43 | 12,102,253 |
| growwmf.in | 20 | 8,828,786 |
| barodabnpparibasmf.in | 70 | 7,876,457 |
| heliosmf.in | 26 | 7,464,567 |
| quantumamc.com | 37 | 7,204,292 |

Full inventory: `SOURCE-RETENTION-INVENTORY.csv` and `.json`. Every unique hash has a classification, source URLs, reasons, reporting/publication dates where known, and measured byte counts.

Validation: **299 passing tests**, final dependency-review run **36093073121**; compressed source packs measured and SHA-256 verified in **36092819677**. The production checkpoint and all source-pack release digests remain unchanged. All **629,225 database rows** and **2,519 originals** remain. No AMC links were live-probed. Latest saved document-download versions were independently protected.
