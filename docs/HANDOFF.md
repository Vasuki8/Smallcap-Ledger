# Smallcap Ledger backend handoff

## Development checkpoint — 2026-10-02 (API restored; draft repair PR)

The freshly provisioned environment's `/etc/codex/network-policy.json` explicitly
allows `api.github.com`. The first and only access probe, a normal GET of the
repository API, returned **HTTP 200 at 2026-10-02T22:49:24Z**. No alternate route,
network/security setting, credential, or TLS policy was changed. The previous
API-blocked checkpoint below is historical and superseded by this section.

Remote main remains `fe21c5dc3cded97ec1fd0b6bb4a849a19d837ada`. The existing
repair was fast-forwarded intact to `068f181018cbaad7945e53db5b30614271d9d0fd`
(code repair `9e8ee21d3540b7069c8fae3f95f7fc2a61cf465e`), reviewed, and submitted
as draft [PR #350](https://github.com/Vasuki8/Smallcap-Ledger/pull/350). No duplicate
fix was implemented. The only executable diff pins the regression fixture clock;
production freshness calculations, snapshot acceptance, and Mid Cap gates remain
unchanged. Fresh local checks at that head: **844 tests passed in 13.459s**, locked
`uv sync --frozen`, Python compilation, and all five production JavaScript syntax
checks passed. `UV_CACHE_DIR=/workspace/.cache/uv` was needed because the default
home cache is read-only. The working tree was clean after testing.

PR creation started Repository regression run
[37074695018](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37074695018)
and Research UI checks run
[37074694999](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37074694999)
on `068f181…`. Both were in progress when this handoff update was prepared.
This documentation commit creates a newer PR head: final exact-head CI must be
read from the PR/API before integration; an earlier head's success is insufficient.

All nine pre-existing dependency PRs remain open and GitHub reports each mergeable.
PRs #317–319 still have failed recorded checks (`mergeable_state=unstable`):
#317 head `6a6726b6bd300e73cde41e6cc9f74da362244a90`, #318 head
`f07ff127d522bd3c60e164120eb6c3d96d6d3e7d`, #319 head
`d75ca9d5a5527cb93c3d4ef4f563b71765e1d90e`. PRs #320, #321, #322, #323,
#325, and #326 have successful recorded checks. These historical runs were not
rerun, and mergeability does not establish compatibility with current main.
[Issue #312](https://github.com/Vasuki8/Smallcap-Ledger/issues/312) is freshly
confirmed **open**; main is **unprotected**, and the ruleset list is empty.
No repository settings were changed.

The separate documentation-only diagnostic branch remains
`diag/icici-ter-evidence-20261002` at
`c8f05aefcd5e5620197b2dd6764e1f2fae3d7a4f`, based on the repair. It establishes
the ICICI Mid Cap TER header-validation failure boundary, not its upstream cause.
Exact failed-run workbook bytes are unavailable; no parser fix is justified.
Its prior HTTP 403 with `server: envoy` is ambiguous between environment/upstream,
not an established domain denial. No ICICI host was retried in this continuation.
The diagnostic records 49 focused tests passing; those are historical fixture
checks, not proof of compatibility with the unavailable workbook.

Next gate: inspect final-head PR #350 CI and request explicit merge authorization
before any integration or deployment. Then continue evidence acquisition for the
TER diagnostic under parent sequencing. No merge, deployment, source refresh,
launch-gate weakening, credential change, or spending change was performed.
No project AGENTS.md or `.agents/skills` exists; `/workspace/.agents` is empty.

## Historical development checkpoint — 2026-10-02 (GitHub API access blocked)

Remote Git refs were rechecked in this continuation: `main` is
`fe21c5dc3cded97ec1fd0b6bb4a849a19d837ada`; the existing repair branch
`fix/icici-regression-clock-20261002` was fetched at
`9e8ee21d3540b7069c8fae3f95f7fc2a61cf465e`. That repair was reviewed intact,
not recreated. It changes only the ICICI regression fixture's clock to
2026-09-24, leaving the real closed-month calculation and production freshness
checks unchanged. On the actual October clock the unchanged main test fails
because it requires September/August but supplies August/July snapshots.

Fresh local verification of the exact repair commit: **844 tests passed in
13.742s**, using `SMALLCAP_NO_SCHEDULER=1 .venv/bin/python -m unittest discover
-s tests -v`; Python compilation and all five JavaScript syntax checks from
`repository-regression.yml` also passed. The main version of the single test
was separately executed in memory and reproduced the expected assertion failure.
This is local evidence, not a CI result or production verification.

Git-fetched PR heads [#317](https://github.com/Vasuki8/Smallcap-Ledger/pull/317)
(`6a6726b6bd300e73cde41e6cc9f74da362244a90`),
[#318](https://github.com/Vasuki8/Smallcap-Ledger/pull/318)
(`f07ff127d522bd3c60e164120eb6c3d96d6d3e7d`) and
[#319](https://github.com/Vasuki8/Smallcap-Ledger/pull/319)
(`d75ca9d5a5527cb93c3d4ef4f563b71765e1d90e`) each pass local
`git merge-tree --write-tree` against that main commit. This establishes no
content conflict for these three refs; it does not establish open status, green
CI, or merge authorization. The earlier nine-open-PR claim and historical CI
failures could not be refreshed.

**Blocker:** `gh pr list` fails with `Post https://api.github.com/graphql:
Forbidden`; a normal HTTPS request also fails at the proxy CONNECT step with
HTTP 403. Git HTTPS works. No security setting, proxy route, credential, or TLS
policy was changed. No advertised pull-request head matched the repair commit,
but API confirmation of PR absence remains unavailable. No draft PR was created,
CI rerun requested, merge performed, or deployment triggered in this continuation.
The checkout has no project `.agents/skills` or `AGENTS.md`, and the mounted
`/workspace/.agents` is empty; repository handoffs were inspected instead.

Required user/environment action: **apply the already saved `api.github.com`
network allowlist change to this execution environment, then restart/resume the
task in that updated environment**. Once normal API access succeeds, re-list PRs
for the existing repair branch and create a draft only if absent; check its exact
head CI, refresh all open-PR conflicts/checks, and read
[issue #312](https://github.com/Vasuki8/Smallcap-Ledger/issues/312) and branch
protection again. Current issue/protection state is unverified, not reconfirmed
from the historical section below. Do not merge or change repository settings
without explicit authorization.

The latest committed launch report is newer than the production checkpoint below:
it was evaluated **2026-09-30T22:37:28.080093+00:00** at main `fe21c5d…`.
All **14/14** input hashes independently match. It reports AUM **34/34**, Direct
TER **29/34**, benchmark identity **28/34**, current portfolios **22/34**, and
complete current portfolios **6/34**; portfolio counts were independently
recounted, all accepted rows dated **2026-08-31**. Source-fetch health is true
in that report. These are dated committed observations, not new October source
fetches or independently verified live deployment results. Data/launch readiness
and public export remain false. See the updated Mid Cap handoff for next work.

Next milestone after API recovery: finish the repair PR/CI gate, then investigate
the fresh missing-data errors before changing parsers. No second implementation
stream was started while that first gate remains blocked; production rollout of
any recovery will require explicit merge authorization.


Updated: 2026-09-30, after the explicitly authorized merge of Helios Mid Cap portfolio recovery in PR #348 and independent production/live-data verification.

## Verified production checkpoint — 2026-09-30

The last successful production run is [#684 / 36671423719](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36671423719), on code `feefbb15025077b2e05e848edb9c9d31a6b53d9b` (PR #348). Its generated evidence commit is `087ba55634a9db3503117f22af61d4505b8f5799`. Build job `109747037093` and Pages deploy job `109755440959` both passed; deployment completed at **2026-09-30T05:36:47Z**. Cache-busted live status, fund-index and coverage reads matched the committed build clock **2026-09-30T05:35:53+00:00** and the following counts:

- Small Cap funds **36**, NAV series **143**, NAV observations **281,868**; latest included NAV **2026-09-29**.
- AUM and Direct fee presence **36/36**. Selected record-date ranges: AUM **2026-09-24 → 2026-09-28**, Direct fee **2026-04-30 → 2026-09-29**. Presence is not uniform freshness.
- The live NAV index has **142 series dated 2026-09-29** and **one dated 2020-04-24**; all 143 series remain in the Small Cap public scope. Its summed NAV observations match the status count.
- Retained portfolio snapshots **161**, documents **3,450**, original archive binaries **4,425**, archive bytes **3,578,406,511**. Database integrity, foreign keys, publication budget and retention safety all pass. No archive deletion occurred; split checkpoint `database-36671423719-1.zip` retains **124 reusable source packs**.

Recent repairs already merged: PR #342 fixed the fresh-source retention checkpoint boundary; #343 corrected the date-sensitive Tata portfolio regression; #344 runs the guarded daily refresh on push publications; #345 invalidates stale hosted-data caches; #346 and #347 recover ITI and Bank of India staged portfolio evidence. Their original source and publication evidence remains in GitHub history and generated reports. Do not repeat the September 25 NAV or PR #300 Mid Cap counts below as current.

[PR #348](https://github.com/Vasuki8/Smallcap-Ledger/pull/348) adds Helios Mid Cap monthly portfolio discovery in existing staged portfolio batch 2. Production freshly observed **74 positions, complete=true, 2026-08-31** at **2026-09-30T05:04:46+00:00**. All **844 repository tests** passed in production (`Ran 844 tests in 8.445s`, `OK`), followed by generated-site/download validation and publication. Independent code review and the earlier exact-source preflight also passed. See [MIDCAP-HANDOFF.md](MIDCAP-HANDOFF.md) for distinct production/preflight source hashes and CI evidence.

The user explicitly authorized the merge. PR #348 was squash-merged at **2026-09-30T05:00:28Z**, with expected head `d41c762541ce86c8bc88cd2a26b560825e40b4a2`. Its normal production run and independent live-data checks are complete. The release handoff changes only documentation and uses `[skip ci]` to avoid replaying collection for prose.

Fresh staged launch evidence reports AUM **34/34**, Direct TER **31/34**, benchmark identity **31/34**, current portfolio evidence **22/34** and **6 complete**. All **14 launch-input hashes** were independently checked; `audit_input_integrity=true`, `input_issues=[]`. Six more current portfolio families are needed for the 28-family policy gate. AMFI daily-AUM HTTP 502 still blocks source-fetch health; the category-aware public-surface gate also remains blocked. Mid Cap remains staged and non-public. Follow the updated Mid Cap handoff for the next source work.

Best-effort retained communication repair still leaves six unavailable originals: five LIC market-outlook URLs failed document validation and one Samco scheme-presentation URL is disallowed by the publisher's robots policy. A successful workflow does not erase those source limitations.

The September 28 repository audit below is preserved as historical evidence. Its branch-protection owner action remains documented; repository-administration settings were not rechecked in this source-recovery slice.

## 2026-09-28 repository audit closure and current gate

### Historical production checkpoint (#662)

Production **run #662 / 36477739739** completed successfully after the approved branch cleanup on commit `785918d57610daeb0f50522a9efcf06e651cbf3a`, followed by status commit `efe12ae9ad314a8d4e3a839b080786db3afb607f`.

Verification:
- **776 full repository tests passed** (`Ran 776 tests in 10.764s`, `OK`).
- static site generation and generated-data/download validation passed.
- split historical checkpoint publication passed: `database-36477739739-1.zip` with **113 reusable source packs**.
- collection/status evidence was committed successfully.
- Pages artifact upload and the dedicated `deploy` job both completed successfully.
- no financial calculation, source-acceptance, retention, launch-threshold or public-category policy was weakened by the operational work below.

Current production status built **2026-09-28T20:01:23Z**:
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

8. **Release-archive growth telemetry — PR #315 / `dc68dfcd5afc726f3a53114f6ba7387b793abc44`**
   - `deployment/storage-health.json` now records `tracker-history` release asset count and compressed bytes;
   - the internal review threshold is **750 assets** and is review-only: it never deletes, repacks or changes retention automatically;
   - production #661 reports **117 assets / 2,734,002,965 compressed bytes**, **633** assets remaining to the review threshold and `review_due=false`;
   - issue #314 was closed after production verification.

9. **Handoff compaction — PR #311 / `b87ce470a97fc13604c84ff6837bf2f341a50d92`**
   - active `docs/HANDOFF.md` was reduced from more than 3,600 lines to a concise current-state handoff;
   - the prior chronology was preserved, without deletion, in `docs/HANDOFF-ARCHIVE.md`.

10. **Dependency-update automation — PR #316 / `c3bc3cdf2c59d7dd4502a5ce16190893e2411d72`**
   - weekly Dependabot version-update PRs now cover both immutable GitHub Actions pins and `uv` dependencies;
   - checks run Monday at 05:00 Asia/Kolkata with at most five open version-update PRs per ecosystem;
   - no auto-merge is configured; normal pull-request regressions remain the acceptance gate.

11. **Approved historical branch cleanup — PR #327 / `785918d57610daeb0f50522a9efcf06e651cbf3a`**
   - the repository owner explicitly approved deletion of the **299** high-confidence merged-tip candidates from `docs/BRANCH-CLEANUP-AUDIT.json`;
   - cleanup run **36477739743** revalidated live branch tips and open PRs immediately before deletion;
   - **299/299** exact matches were deleted with **0 missing, 0 moved, 0 open-PR skips and 0 failures**;
   - independent post-cleanup verification found **0 approved-candidate survivors** and **60 total branches**;
   - the 2 moved branches, 8 closed/unmerged PR branches, 34 no-PR-evidence branches, newer maintenance branches and Dependabot branches were not deleted;
   - production #662 completed successfully after the cleanup.

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

### Remaining repository-maintenance gate

Only one repository-audit item remains open:

- **Issue #312 — Enable main branch protection ruleset.** This requires GitHub repository-administration access; the connected integration can verify but cannot apply the ruleset.

Issue #313 is complete: the owner-approved 299-branch high-confidence deletion set was executed and independently verified. Review-required branches remain untouched.

All other actionable findings from the repository-wide audit are now implemented and verified. Until #312 is completed, continue using pull requests voluntarily and do not push development commits directly to `main`.

For Mid Cap data work, continue to use `docs/MIDCAP-HANDOFF.md` and the generated readiness artifacts as the authority. Mid Cap remains staged/non-public until its explicit launch gates pass.

## Historical handoff archive

Older backend chronology has been moved, without deletion, to [HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md). Use that archive only when reconstructing prior source repairs, migrations, incidents, or production evidence. Do not let an older archived priority override the current-state section above.

For staged Mid Cap work, continue to use [MIDCAP-HANDOFF.md](MIDCAP-HANDOFF.md) and the generated readiness artifacts as the current authority.
