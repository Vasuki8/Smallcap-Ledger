# Source-retention audit — proposal only

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
