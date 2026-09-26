# Source-retention audit — proposal only

## Post-audit 271-hash review completed — all binaries still retained

The **271 hashes added after the original 2,519-hash review are now conservatively classified**. No source binary was deleted or marked metadata-only.

Implementation PR **#157** merged as commit `325ab240a9e7fe0629dcf65b970b1ba2273d2b3c`. Production workflow **#517 / run 36207892234** completed successfully at **2026-09-26T01:18:37Z** with **365 passing tests** and GitHub Pages deployment.

### Generated-artifact self-protection regression fixed

The previous readiness run had incorrectly promoted historical hashes because generated review files such as:

- `RETENTION-PROPOSED-MANIFEST.json`
- `RETENTION-MIGRATION-CANDIDATES.json`
- `RETENTION-REPLACEMENT-SIMULATION.md`

contain archive hashes by design. The conservative scanner treated those literal hashes as independent evidence dependencies.

Those generated retention-review artifacts are now excluded from literal-hash dependency scanning, just like the original `SOURCE-RETENTION-*` generated inventories.

The metadata preparation logic was also hardened:

- the original reviewed classification is the minimum historical floor;
- the corrected current dependency scan may strengthen that floor;
- an independently reviewed/refetched current state may remain stronger;
- a prior stronger state created only by the audit-import/current-scan automation can be corrected downward when the corrected scan no longer supports it;
- binary state remains unchanged.

This repairs the false self-protection without weakening genuine evidence or refetch promotions.

### Review result for the 271 post-audit hashes

Authoritative review artifacts:

- `docs/SOURCE-RETENTION-DELTA.json`
- `docs/SOURCE-RETENTION-DELTA.md`
- `docs/SOURCE-RETENTION-NEW-CANDIDATES.json`

Review time: **2026-09-26T01:17:22Z**.

| Classification | Files | Raw bytes |
| --- | ---: | ---: |
| retain_evidence | 67 | 147,277,130 |
| retain_latest_or_review | 199 | 89,172,029 |
| link_only_candidate | 5 | 3,851,376 |
| unclassified | 0 | 0 |

Every one of the 271 remains **binary-retained**.

The five new link-only candidates are a **separate candidate delta** and are explicitly **not merged into the existing approval-gated historical migration proposal**.

New candidate hosts/pages are:

- SAMCO Mutual Fund statutory-disclosure page;
- Baroda BNP Paribas September 2026 Small Cap e-factsheet page;
- Kotak Small Cap September 2026 factsheet HTML;
- Kotak Small Cap July 2026 factsheet HTML;
- Quantum Small Cap Fund page.

Each is classified as a superseded discovery response without an identified financial/replay dependency. Raw bytes across these five: **3,851,376**.

### Current full retention state

Production readiness at **2026-09-26T01:17:23Z** now reports **2,790 / 2,790 binaries retained**:

- `retain_evidence`: **1,051 files / 1,439,403,320 bytes**
- `retain_latest_or_review`: **1,038 files / 556,155,122 bytes**
- `link_only_candidate`: **701 files / 407,261,761 bytes**
- `unclassified`: **0**

Files actually deleted: **0**.  
Bytes actually deleted: **0**.  
Metadata-only binaries: **0**.  
Source-pack repack performed: **false**.  
Rollback/legacy assets retired: **false**.

All non-retention table fingerprints remained unchanged during classification, and active source packs still cover every retained hash.

### Historical simulation proposal is now stale

After removing generated-artifact self-protection, the corrected scan shows only **4** of the original 700 historical candidates are currently strengthened. Therefore:

- original historical reviewed candidates: **700**
- currently eligible historical candidates: **696**
- separate new post-audit candidates: **5**
- total currently classified link-only candidates: **701**

The previously simulated **695-hash** historical proposal is therefore no longer the current execution set. **Do not execute it.**

The five new candidates also must not be silently appended to that prior proposal; they remain a separate review delta.

### Next safe retention step

Before any owner approval can be acted on, rerun the isolated replacement-pack simulation against exactly the **696 currently eligible hashes from the original 700-hash historical review**, explicitly excluding the 5 new delta candidates.

That refresh remains simulation-only: no release upload/delete, no binary-state change, no active-manifest switch, no source-file deletion and no legacy-ZIP retirement.


## Isolated replacement-pack simulation completed — no production mutation

The storage-reduction proposal has now been simulated end-to-end against an exact active checkpoint. **No production binary state changed and no release asset was uploaded, deleted, retired or switched.**

The authoritative current simulation is committed in:

- `deployment/retention-pack-simulation.json`
- `docs/RETENTION-PROPOSED-MANIFEST.json`
- `docs/RETENTION-MIGRATION-CANDIDATES.json`
- `docs/RETENTION-REPLACEMENT-SIMULATION.md`

Final isolated workflow **run 36205872175** completed successfully at **2026-09-26T00:45:24Z**.

### Candidate-set change since the original audit

The historical audit reviewed **700** link-only candidates. By the active checkpoint created **2026-09-25T22:17:18Z**, newer collection evidence had strengthened **5** of those hashes to `retain_latest_or_review`.

The final simulated migration therefore contains **695 currently eligible candidates**, not 700.

- historical reviewed candidates: **700**
- currently eligible candidates: **695**
- reviewed hashes excluded because newer evidence strengthened them: **5**
- proposed metadata-only raw bytes: **403,318,035**
- reviewed compressed payload bytes for those 695 candidates: **34,139,810**

The five excluded hashes remain binary-retained and are listed with their current retention reasons in the committed candidate/report artifacts.

### Exact proposed pack result

The active checkpoint contains **2,790 archive hashes** and **101 active source packs**.

The final proposal would:

- keep **2,095** hashes binary-retained;
- mark **695** hashes metadata-only;
- affect **49** current source packs;
- replace **24** affected packs;
- fully retire **25** packs that contain only proposed metadata-only candidates;
- produce **76** steady-state source packs total.

Measured asset sizes:

- current source-pack assets: **1,540,491,329 bytes**
- proposed source-pack assets: **1,506,186,949 bytes**
- exact source-pack asset reduction: **34,304,380 bytes**
- current active database ZIP: **7,919,692 bytes**
- simulated database ZIP: **7,920,662 bytes**
- exact active-set reduction including the database ZIP change: **34,303,410 bytes**

The database ZIP grows by **970 bytes** because of the simulated retention-state metadata, so the active-set reduction is 970 bytes smaller than the source-pack reduction.

### Validation results

All simulation gates passed:

- non-retention database fingerprints unchanged;
- proposed manifest covers every retained hash exactly once;
- duplicate proposed manifest hashes: **0**;
- all **984** protected evidence hashes remain retained;
- metadata-only selective materialization is blocked;
- a retained replacement-pack member can be selectively materialized and hash-verified;
- AMC replay eligibility contains no metadata-only candidate and has **0 replay gaps**;
- metadata-only archive download endpoint returns the unavailable state;
- metadata-only saved document versions are hidden from saved-copy listings;
- full static-site generation and validation pass;
- metadata-only candidates published on the simulated site: **0**;
- current active manifest/database/source packs remain preserved as rollback.

The simulated static site was **344,503,712 bytes** and exposed **137** saved archive downloads, none from the proposed metadata-only set.

### Authorization boundary

Production mutations performed by the simulation:

- release uploads: **0**
- release deletions: **0**
- active-manifest switches: **0**
- production binary-state changes: **0**
- production source-file deletions: **0**
- legacy ZIP retirements: **0**

The exact migration proposal is ready for review, but **an actual binary-reduction migration remains approval-gated**.

The original 700-candidate simulation against the earlier 21:19 checkpoint remains historical evidence only. A later normal workflow correctly failed when it tried to reuse that stale 700-hash set after current evidence had strengthened one of those hashes. That failure led to the current-eligible intersection rule, and the final 695-hash run is the authoritative proposal.


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
