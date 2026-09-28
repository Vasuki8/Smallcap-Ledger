# Smallcap Ledger backend handoff


Updated: 2026-09-28, after repository-wide operational hardening, portable-package repair, coverage-date clarification, and publisher cleanup.

## 2026-09-28 repository audit closure and current gate

### Latest verified production checkpoint

Production **run #660 / 36458995440** completed successfully on commit `181e5f038bfa61edf635f059cb672aeb2aceccd2`, followed by status commit `5ce202da5a1571251ed5a902e6c55bb2c33f5abf`.

Verification:
- **765 full repository tests passed** (`Ran 765 tests in 17.460s`, `OK`).
- static site generation and generated-data/download validation passed.
- split historical checkpoint publication passed: `database-36458995440-1.zip` with **113 reusable source packs**.
- collection/status evidence was committed successfully.
- Pages artifact upload and the dedicated `deploy` job both completed successfully.
- no financial calculation, source-acceptance, retention, launch-threshold or public-category policy was weakened by the operational work below.

Current production status built **2026-09-28T17:40:57Z**:
- funds: **36**
- NAV series: **143**
- NAV observations: **281,584**
- latest included NAV: **2026-09-25**
- AUM coverage: **36/36**
- dated Direct fee coverage: **36/36**
- benchmark observations: **5,330**
- retained portfolio snapshots: **134**
- retained documents: **2,156**
- retained archive binaries: **2,910 / 2,910**
- archive bytes: **2,498,478,753**
- database integrity remains protected by the normal regression/publication pipeline.

Presence and record-date freshness are now deliberately separate. Current selected record-date ranges are:
- AUM: **2026-09-24 → 2026-09-24**
- Direct fee: **2026-04-30 → 2026-09-25**
- reported benchmark identity: **2023-08-31 → 2026-09-25**

Do not interpret 36/36 presence coverage as 36/36 same-date freshness.

### Repository-audit fixes completed

1. **Universal pull-request regression gate — PR #302 / `5fdcb99d8f97fd43d0909a1e9c6a70925e897c7b`**
   - every PR now runs Python compile checks, production-JavaScript syntax checks and the full unittest suite;
   - the workflow is read-only and uses immutable setup-action pins.

2. **Publisher least privilege — PR #303 / `af72f05f0cfc5110555e359e13b61ea18c97e2e7`**
   - workflow default permission is read-only;
   - the build job has only `contents: write`;
   - `pages: write` and `id-token: write` exist only in the deploy job;
   - checkout credentials are not persisted;
   - `GH_TOKEN` is step-scoped rather than job-wide.

3. **Scoped-token incident and repair**
   - production **#657 / 36453320117** failed at `Generate GitHub Pages site` because lazy retained-source materialization calls `gh release download`, and the initial least-privilege pass had not granted that export step a token;
   - PR #306 / `19de3c89b9822397cbb460877d4ff61d83d8b11f` granted `GH_TOKEN` only to that specific export step;
   - production **#658 / 36455741314** then passed site materialization, archive publication, status recording, artifact upload and Pages deployment. Keep this step-scoped access; do not restore a job-wide token merely for convenience.

4. **Portable-package manifest integrity — `758502428d68a1712c869a4e25fb719cce21f551`**
   - the stale checked-in `PACKAGE-MANIFEST.json` was removed from package inputs;
   - portable packages now generate exactly one manifest entry;
   - integrity regressions protect against duplicate/stale package manifests.
   - production **#656 / 36451609846** succeeded.

5. **Coverage date-range visibility — `e38fa8e30ed630297876eb53167bdaabcc40dec5`**
   - coverage/status now exposes selected AUM, Direct-fee and benchmark-identity record-date ranges separately from collection/build clocks;
   - this closes the audit finding where 36/36 presence could be misread as uniformly fresh data.

6. **Retired completed push-only recovery hooks — PR #307 / `e0959888e293d460802fcae0376070bca331432d`**
   - ordinary pushes no longer rerun completed historical communication, portfolio, TER and diagnostic recovery hooks;
   - production logs had shown those upgrades as already applied, while remaining Union/UTI source gaps are documented non-actionable blockers;
   - `.github/workflows/daily.yml` dropped from **73 to 42 named steps**;
   - nightly `scripts/daily_update.py`, retained communication repair, retention preparation, database compaction, full regressions, export/validation, archive publication, status recording and Pages deployment remain active;
   - underlying recovery scripts remain in the repository for explicit/manual use.
   - production **#659 / 36457687329** succeeded on the streamlined path.

7. **Immutable Actions and checkout credential policy — PR #308 / `181e5f038bfa61edf635f059cb672aeb2aceccd2`**
   - every external GitHub Action in every workflow is pinned to a 40-character commit SHA;
   - every `actions/checkout` step sets `persist-credentials: false`;
   - repository-wide regressions now enforce both properties.
   - production **#660 / 36458995440** succeeded.

### Remaining P0 manual repository setting

**`main` is still unprotected.** GitHub currently reports `protected=false` and the repository ruleset list is empty. The connected GitHub integration can read this state but does not expose repository-administration writes, so this cannot be completed safely from the current connector.

Owner action still required in GitHub:
- create an active branch ruleset targeting the default branch;
- require pull requests before merge;
- require **Repository regression / regression** to pass;
- require branches to be up to date before merge;
- block force pushes;
- restrict branch deletion;
- do not require an approval count while this remains a single-developer repository unless the ownership/review model changes.

Until that ruleset is enabled, follow the PR workflow voluntarily and do not push development commits directly to `main`.

### Next repository-maintenance priority

The remaining audit work is lower priority than the P0 items above:
- branch backlog audit is complete in `docs/BRANCH-CLEANUP-AUDIT.json` / `.md`: **299** exact merged-tip cleanup candidates, **2** post-merge/moved branches, **8** closed/unmerged PR branches, **34** branches with no PR evidence, and **0** open-PR branches. **No deletion has been performed; branch deletion still requires explicit owner approval.**
- reduce handoff/documentation sprawl after preserving a concise current-state section;
- consider moving known maintenance/backlog items into GitHub Issues so they are not discoverable only through long handoff history.

For Mid Cap data work, continue to use `docs/MIDCAP-HANDOFF.md` and the generated readiness artifacts as the authority. Mid Cap remains staged/non-public until its explicit launch gates pass.

## Historical handoff archive

Older backend chronology has been moved, without deletion, to [HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md). Use that archive only when reconstructing prior source repairs, migrations, incidents, or production evidence. Do not let an older archived priority override the current-state section above.

For staged Mid Cap work, continue to use [MIDCAP-HANDOFF.md](MIDCAP-HANDOFF.md) and the generated readiness artifacts as the current authority.
