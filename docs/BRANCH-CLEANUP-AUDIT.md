# Branch cleanup audit

Prepared: 2026-09-28  
Executed: 2026-09-28T20:16:46Z

The original branch classification is preserved below. The repository owner explicitly approved deletion of the **299 high-confidence merged-tip candidates only**. GitHub Actions run **36477739743** revalidated current branch tips and open PRs immediately before deletion, deleted all **299 / 299** exact matches, and reported **0 missing, 0 moved, 0 open-PR skips, and 0 failures**.

Independent post-cleanup verification found **0 approved-candidate survivors** and **60 total branches**. The review-required and newer branches were not deleted. Production run **#662 / 36477739739** completed successfully after the cleanup.

## Summary

| Classification | Count |
| --- | ---: |
| Total branches | 344 |
| Main | 1 |
| High-confidence merged-tip cleanup candidates | 299 |
| Open-PR branches | 0 |
| Merged previously, but tip moved afterward | 2 |
| Closed/unmerged PR branches | 8 |
| No PR evidence | 34 |

A branch is a high-confidence candidate only when its **current tip SHA exactly matches the head SHA of an already-merged PR** and it has no open PR. This avoids treating a branch with post-merge commits as disposable.

## Candidate counts by prefix

- `backend`: **135**
- `diag`: **46**
- `docs`: **42**
- `fix`: **36**
- `ui`: **14**
- `ops`: **8**
- `storage`: **7**
- `(root)`: **4**
- `feature`: **3**
- `cleanup`: **2**
- `audit`: **1**
- `work`: **1**

## Review-required branches

### Merged before, but current tip moved

| Branch | Current tip | Merged PR | Merged head |
| --- | --- | ---: | --- |
| `maintenance/storage-cleanup-20260925` | `d9246b03b7fb` | #108 | `dbc634f67b9e` |
| `ui/minimal-navigation-polish-2026-09-22` | `b01863636033` | #14 | `e9c3d5c01a8e` |

### Closed but unmerged PR branches

| Branch | PR | Title |
| --- | ---: | --- |
| `backend/bajaj-complete-portfolio` | #12 | Recover complete Bajaj Small Cap portfolios |
| `backend/groww-august-portfolio` | #84 | Refresh Groww portfolio from August monthly workbook |
| `backend/reclassify-risk-factor-docs` | #70 | Keep risk-factor PDFs out of factsheet coverage |
| `backend/union-bajaj-portfolio-20260925` | #105 | Document Union and Bajaj portfolio blockers |
| `diag/pgim-quant-communications-20260926-v2` | #207 | Inspect PGIM and Quant communication sources |
| `diag/sbi-sundaram-final-transport-20260926` | #213 | Trace final SBI and Sundaram communication transports |
| `docs/verified-midcap-freshness-647-20260928` | #292 | Record verified Mid Cap freshness safeguards and current launch blockers |
| `investigate/mirae-ter-20260925` | #104 | Recover Mirae Asset official TER and BER |

### No PR evidence

- `backend/bajaj-bandhan-communication-recovery-20260926` — `ca6f5232de1e`
- `backend/bandhan-portfolio-recovery-v129` — `84ab21e20c89`
- `backend/bandhan-portfolio-v129` — `170247168150`
- `backend/bandhan-production-v129` — `9f4f3ac8d1e2`
- `backend/edelweiss-portfolio-20260925` — `4a5b74c1135f`
- `backend/fix-groww-v33-release` — `f48fe5a0ab19`
- `backend/franklin-article-api-recovery-20260926` — `2f6e82164970`
- `backend/icici-complete-portfolio-v128` — `e18454590651`
- `backend/icici-monthly-portfolio-recovery-20260926` — `475816731301`
- `backend/icici-portfolio-transport-20260925` — `85dc28a6794b`
- `backend/invesco-monthly-holdings-v127` — `3011daad62f4`
- `backend/midcap-staged-nav-history-20260927` — `706b54508d53`
- `backend/portfolio-limitations-20260925-v2` — `4ffc9fec3e1f`
- `backend/probe-amfi-portfolio-feed` — `48a128c8a68a`
- `backend/sbi-sundaram-communication-final-20260926` — `935b6558f00d`
- `backend/sbi-sundaram-communication-recovery-20260926` — `c16b33a236ee`
- `backend/sbi-sundaram-communication-recovery-v2-20260926` — `0a5a5642e32b`
- `backend/sundaram-direct-outlook-recovery-20260926` — `a1fe2863d033`
- `backend/uti-portfolio-audit-v128` — `fb1638246b1d`
- `cleanup/retention-simulation-hooks-20260925` — `b23632bf07a0`
- `diag/midcap-benchmark-contracts-20260928` — `942228ae7300`
- `diag/midcap-benchmark-role-20260928` — `bfdcc63c1a46`
- `diag/midcap-two-sources-20260928` — `b782d3dfbe6f`
- `diag/pgim-quant-communications-20260926-v3` — `cb2652d1e335`
- `diag/sbi-sundaram-communications-v2-20260926` — `4c75bb92c868`
- `diag/wealth-uti-transport-20260926` — `93f9ef5b9375`
- `docs/axis-complete-portfolio-handoff-20260925` — `2b56cf3a741d`
- `docs/midcap-samco-ter-handoff-20260928` — `86183fbc395c`
- `fix/kotak-mirae-release-20260926` — `36a5be9b8842`
- `fix/samco-ter-investigation-20260928` — `09e2b6c3cf5d`
- `investigate/groww-ber-20260925` — `2a4f398fbd20`
- `investigate/uti-ber-20260925` — `c2a9510afb81`
- `ui-compact-top-navigation` — `5b72848f1619`
- `work/axis-portfolio-20260924` — `88df040a95e2`

## High-confidence merged-tip candidates

These were the approved deletion set. All **299** listed branches were deleted after exact-tip/open-PR revalidation on 2026-09-28. The rows remain below as execution evidence.

| Branch | PR | Merged at | Tip |
| --- | ---: | --- | --- |
| `audit/source-retention-20260925` | #109 | 2026-09-25T04:08:10Z | `631df53ef8e1` |
| `backend/abakkus-axis-communication-sources-20260926` | #183 | 2026-09-26T05:51:40Z | `4466e6132298` |
| `backend/absl-complete-portfolio` | #56 | 2026-09-23T14:28:12Z | `281ddd2e18af` |
| `backend/amc-communication-coverage-audit-20260926` | #178 | 2026-09-26T04:39:23Z | `053316444f74` |
| `backend/amfi-expense-coverage-v130` | #94 | 2026-09-24T21:36:41Z | `90754ea5f270` |
| `backend/axis-expense-recovery-20260925` | #119 | 2026-09-25T06:06:54Z | `e98255459e5c` |
| `backend/axis-full-portfolio-20260925` | #117 | 2026-09-25T05:16:01Z | `30342d550d56` |
| `backend/backfill-retained-portfolio-quantities` | #51 | 2026-09-23T04:34:45Z | `964249feb127` |
| `backend/bajaj-bandhan-communication-recovery-20260926-v2` | #187 | 2026-09-26T06:19:30Z | `20de3b4ef984` |
| `backend/bajaj-complete-portfolio-v2` | #13 | 2026-09-22T21:10:47Z | `63dce82fd3dd` |
| `backend/bandhan-public-disclosure-v129b` | #92 | 2026-09-24T18:35:18Z | `8185f7713344` |
| `backend/bandhan-wp-portfolio-attachments` | #74 | 2026-09-23T17:40:40Z | `513062e8d450` |
| `backend/benchmark-identity-tri-repair-20260925` | #125 | 2026-09-25T16:25:20Z | `a18b8ad14ca3` |
| `backend/boi-complete-portfolio` | #32 | 2026-09-22T23:54:54Z | `2e405e557fe5` |
| `backend/boi-layout-text-fallback` | #36 | 2026-09-23T00:45:43Z | `936d141e9fad` |
| `backend/boi-official-top-holdings` | #39 | 2026-09-23T02:06:36Z | `84e31cba70ab` |
| `backend/boi-pdf-reprocess` | #35 | 2026-09-23T00:03:15Z | `55a25ea89960` |
| `backend/boi-real-four-column-portfolio` | #71 | 2026-09-23T17:05:28Z | `5359a6cb9932` |
| `backend/bse-tri-source-audit-20260925` | #124 | 2026-09-25T16:12:36Z | `41ed1cbbfe7c` |
| `backend/classify-absl-idcw-nav-gap-20260925` | #144 | 2026-09-25T20:27:36Z | `91f499a4dd2c` |
| `backend/classify-official-nav-gaps-20260925` | #135 | 2026-09-25T18:50:49Z | `3003bc26adda` |
| `backend/communication-archive-limitations-20260926` | #221 | 2026-09-26T21:24:47Z | `3b64ed1c1b0b` |
| `backend/current-portfolio-share-deltas` | #50 | 2026-09-23T04:29:27Z | `3fd47b3c0127` |
| `backend/current-storage-health-20260927` | #241 | 2026-09-27T03:07:04Z | `db0b12bcef95` |
| `backend/edelweiss-current-factsheet-replay` | #55 | 2026-09-23T14:22:06Z | `14020f1e3a93` |
| `backend/edelweiss-franklin-communication-sources-20260926` | #189 | 2026-09-26T11:37:43Z | `069984f1b9ce` |
| `backend/edelweiss-pdf-franklin-api-recovery-20260926` | #197 | 2026-09-26T12:14:21Z | `9060239d6506` |
| `backend/edelweiss-top30-portfolio` | #44 | 2026-09-23T03:41:49Z | `2c37d3135bef` |
| `backend/evidence-aware-performance-benchmark-20260925` | #137 | 2026-09-25T19:12:12Z | `0e94546f9531` |
| `backend/fix-absl-parser-orphan-tail` | #58 | 2026-09-23T14:33:35Z | `8e80b756442b` |
| `backend/fix-absl-parser-splice` | #57 | 2026-09-23T14:30:56Z | `913944c283f5` |
| `backend/fix-amc-source-resolver-20260926` | #182 | 2026-09-26T05:04:53Z | `3b2d8db77e0f` |
| `backend/fix-amfi-probe-import` | #60 | 2026-09-23T14:48:07Z | `a963f1f5d2e7` |
| `backend/fix-bandhan-json-test` | #77 | 2026-09-23T17:45:28Z | `9aeaca6e0cbc` |
| `backend/fix-bandhan-wp-test` | #75 | 2026-09-23T17:42:36Z | `ee281d243029` |
| `backend/fix-boi-parser-syntax` | #33 | 2026-09-23T00:00:48Z | `d9881905bfc7` |
| `backend/fix-icici-reconciliation-fixture` | #68 | 2026-09-23T16:52:15Z | `e41c6fd04e3c` |
| `backend/fix-jm-top25-real-layout` | #64 | 2026-09-23T15:31:02Z | `a3cef2a9d445` |
| `backend/fix-jm-v30-fixture` | #65 | 2026-09-23T15:32:35Z | `991eefabee06` |
| `backend/fix-notice-filename-classification` | #45 | 2026-09-23T03:42:44Z | `a77b75e3dba6` |
| `backend/fix-parser-upgrade-gate` | #37 | 2026-09-23T00:48:04Z | `4ee0f5f832cf` |
| `backend/fix-parser-upgrade-test-import` | #38 | 2026-09-23T01:00:27Z | `d1c79baa6e5f` |
| `backend/fix-portfolio-document-classification` | #43 | 2026-09-23T03:36:19Z | `28fa415595ca` |
| `backend/fix-publication-amc-source-matching-20260926` | #179 | 2026-09-26T04:43:20Z | `e4ae17941376` |
| `backend/fix-quant-portfolio-filter` | #31 | 2026-09-22T23:42:48Z | `385d71970d84` |
| `backend/fix-quantity-schema-tests` | #53 | 2026-09-23T04:39:21Z | `1f3e9966b0fc` |
| `backend/fix-risk-factor-historical-cleanup` | #73 | 2026-09-23T17:11:31Z | `26c2ff2c2e3e` |
| `backend/fix-union-v45-rounding-test` | #81 | 2026-09-23T20:18:47Z | `c545fdac0696` |
| `backend/fix-v26-test-db-import` | #54 | 2026-09-23T04:41:24Z | `c86f5ffe8327` |
| `backend/fix-versioned-parser-tests` | #52 | 2026-09-23T04:36:40Z | `982c516c5e79` |
| `backend/franklin-api-communication-recovery-20260926` | #196 | 2026-09-26T12:11:41Z | `edf3a0095e10` |
| `backend/groww-august-portfolio-v2` | #85 | 2026-09-23T22:42:17Z | `cde840819ce4` |
| `backend/groww-hsbc-communication-recovery-20260926` | #199 | 2026-09-26T13:09:45Z | `f72c840fd23b` |
| `backend/groww-reconciled-portfolio` | #78 | 2026-09-23T17:53:07Z | `6c3305371542` |
| `backend/harden-boi-page-parser` | #40 | 2026-09-23T02:30:17Z | `ca3aad00d5fb` |
| `backend/hsbc-ter-v131` | #95 | 2026-09-24T22:01:05Z | `039ea1e4a0d7` |
| `backend/icici-blob-portfolio-recovery-20260926` | #174 | 2026-09-26T04:13:53Z | `d1253a8a89ab` |
| `backend/icici-complete-portfolio-final-20260926` | #176 | 2026-09-26T04:26:44Z | `29534f0b17c9` |
| `backend/icici-fresh-partial-portfolio` | #67 | 2026-09-23T15:46:23Z | `67a9b460c0f0` |
| `backend/icici-invesco-communication-recovery-20260926` | #200 | 2026-09-26T14:04:43Z | `d576857bf0c6` |
| `backend/icici-portfolio-recovery-fix-20260926` | #175 | 2026-09-26T04:18:38Z | `18117bb2e2fd` |
| `backend/icici-ter-v132` | #96 | 2026-09-24T23:05:06Z | `6f229c0c12f9` |
| `backend/inspect-boi-archived-layout` | #69 | 2026-09-23T16:54:38Z | `bc9d18a59718` |
| `backend/inspect-icici-archived-layout` | #66 | 2026-09-23T15:36:52Z | `a345724e3b1d` |
| `backend/inspect-jm-archived-layout` | #63 | 2026-09-23T15:24:34Z | `3b9a8f646592` |
| `backend/invesco-complete-portfolio-v127` | #90 | 2026-09-24T15:20:30Z | `ed45967e745e` |
| `backend/invesco-ter-v132` | #97 | 2026-09-24T23:31:18Z | `729a63debc9f` |
| `backend/iti-mahindra-communication-recovery-20260926` | #181 | 2026-09-26T05:02:00Z | `274adead5135` |
| `backend/jm-complete-portfolio-v128` | #91 | 2026-09-24T16:36:42Z | `246079107f6a` |
| `backend/jm-official-top-holdings` | #41 | 2026-09-23T02:31:51Z | `c60ccf69233e` |
| `backend/jm-ter-v133` | #98 | 2026-09-25T00:21:28Z | `2ce17729113c` |
| `backend/jm-top25-factsheet` | #62 | 2026-09-23T14:55:27Z | `2b1e058a6581` |
| `backend/kotak-mirae-communication-recovery-20260926` | #202 | 2026-09-26T14:17:49Z | `1ca2a04657bc` |
| `backend/lic-communication-url-canonicalization-20260926` | #226 | 2026-09-26T22:10:30Z | `4d4bc54d3f89` |
| `backend/lic-empty-asset-limitation-20260926` | #230 | 2026-09-26T22:42:54Z | `4bc4a55e3413` |
| `backend/lic-referer-fallback-20260926` | #228 | 2026-09-26T22:31:50Z | `e6adaf4c51d8` |
| `backend/mahindra-ter-v134` | #99 | 2026-09-25T01:11:58Z | `39176a520c5f` |
| `backend/midcap-benchmark-batch1-20260927` | #268 | 2026-09-28T00:15:44Z | `9e9283578493` |
| `backend/midcap-benchmark-batch2-20260927` | #269 | 2026-09-28T00:29:26Z | `e54615af1ec4` |
| `backend/midcap-history-staging-20260927` | #248 | 2026-09-27T11:31:27Z | `d45ce051afd8` |
| `backend/midcap-identity-audit-20260927` | #245 | 2026-09-27T04:13:53Z | `bd050cf51fae` |
| `backend/midcap-portfolio-batch1-20260927` | #270 | 2026-09-28T00:42:35Z | `4cd07f3c070e` |
| `backend/midcap-portfolio-batch2-20260927` | #272 | 2026-09-28T01:00:56Z | `4b59a09a3738` |
| `backend/midcap-portfolio-batch3-20260927` | #277 | 2026-09-28T01:48:44Z | `19d9b5d6a6fb` |
| `backend/midcap-portfolio-batch4-launch-gate-20260927` | #281 | 2026-09-28T02:53:10Z | `c7dc2fae057e` |
| `backend/midcap-portfolio-batch5-20260927` | #283 | 2026-09-28T03:40:55Z | `d9671d324f7e` |
| `backend/midcap-source-coverage-audit-20260927` | #250 | 2026-09-27T11:53:09Z | `ece55dcd0630` |
| `backend/midcap-staging-store-20260927` | #247 | 2026-09-27T04:22:21Z | `71661fa314e6` |
| `backend/midcap-ter-first-party-batch1-20260927` | #259 | 2026-09-27T17:42:42Z | `79fb2a3d03f0` |
| `backend/midcap-ter-first-party-batch2-20260927` | #264 | 2026-09-27T21:09:41Z | `bf1aad8a2947` |
| `backend/midcap-ter-gap-classification-20260927` | #257 | 2026-09-27T17:24:21Z | `89b39367d840` |
| `backend/midcap-ter-readiness-reconcile-20260927` | #260 | 2026-09-27T17:50:48Z | `f3504a437acc` |
| `backend/motilal-midcap-identity-20260927` | #246 | 2026-09-27T04:19:01Z | `957c57202cde` |
| `backend/multicategory-foundation-20260927` | #243 | 2026-09-27T03:55:58Z | `fd3ec6af942c` |
| `backend/performance-audit-benchmark-semantics-20260925` | #141 | 2026-09-25T19:56:47Z | `9a19cdbdda66` |
| `backend/performance-coverage-audit-20260925` | #122 | 2026-09-25T15:40:26Z | `9fe6e2b5c890` |
| `backend/persist-communication-repair-report-20260926` | #223 | 2026-09-26T21:34:30Z | `6c23002f79a6` |
| `backend/pgim-quant-communication-recovery-20260926` | #208 | 2026-09-26T15:55:04Z | `3862e1695800` |
| `backend/portfolio-gap-audit` | #17 | 2026-09-22T21:36:50Z | `3d6513bdca93` |
| `backend/portfolio-limitations-20260925` | #112 | 2026-09-25T04:34:33Z | `496b642f4630` |
| `backend/portfolio-recovery-queue-20260925` | #114 | 2026-09-25T04:45:14Z | `f4501dfcd8f0` |
| `backend/preflight-parser-syntax` | #34 | 2026-09-23T00:01:37Z | `027b510515c1` |
| `backend/probe-amfi-central-portfolio-current` | #59 | 2026-09-23T14:45:55Z | `8244fab05e3b` |
| `backend/publication-budget-reserve-20260927` | #239 | 2026-09-27T01:54:00Z | `b9ed51336db6` |
| `backend/quant-portfolio-discovery` | #29 | 2026-09-22T23:38:27Z | `48659c82fee4` |
| `backend/reclassify-risk-factor-docs-v2` | #72 | 2026-09-23T17:09:30Z | `80d2a682c909` |
| `backend/recover-missing-benchmarks` | #49 | 2026-09-23T04:15:52Z | `3088acff53d6` |
| `backend/recovery-source-change-watch-20260925` | #120 | 2026-09-25T06:23:43Z | `7a4ef1761fcf` |
| `backend/refresh-696-retention-simulation-20260926` | #159 | 2026-09-26T01:31:40Z | `a1b8cab9c6aa` |
| `backend/remove-amfi-portfolio-probe` | #61 | 2026-09-23T14:50:46Z | `28879a653bac` |
| `backend/remove-duplicate-upgrade-discovery` | #47 | 2026-09-23T03:50:11Z | `4718c8bb5227` |
| `backend/repair-unarchived-communications-20260926` | #222 | 2026-09-26T21:26:46Z | `c6caddfbf4bc` |
| `backend/retention-aware-storage-plumbing-20260925` | #146 | 2026-09-25T20:57:12Z | `bc33b60f98b7` |
| `backend/retention-repack-simulation-20260925` | #150 | 2026-09-25T21:52:47Z | `d466ec0bca35` |
| `backend/review-new-retention-hashes-20260926` | #157 | 2026-09-26T01:16:51Z | `4773e174834b` |
| `backend/samco-communication-classification-20260926` | #225 | 2026-09-26T22:09:37Z | `56328fae45cf` |
| `backend/sbi-sundaram-communication-recovery-final-v3-20260926` | #215 | 2026-09-26T20:23:00Z | `2cffdaafd88b` |
| `backend/stale-complete-refresh-v2` | #83 | 2026-09-23T22:09:13Z | `028efb130855` |
| `backend/sundaram-complete-portfolio-v126` | #89 | 2026-09-24T15:01:00Z | `c2ebd33f75bd` |
| `backend/sundaram-direct-outlook-recovery-v2-20260926` | #227 | 2026-09-26T22:30:38Z | `ebb8b8d5cc09` |
| `backend/target-parser-upgrades` | #46 | 2026-09-23T03:45:59Z | `df3f97d1b4a3` |
| `backend/tata-complete-portfolio-v124` | #87 | 2026-09-24T07:20:11Z | `3b4acae06ba4` |
| `backend/tata-portfolio-discovery` | #42 | 2026-09-23T03:14:48Z | `22a6d29bffdb` |
| `backend/tata-wealth-communications-20260926` | #216 | 2026-09-26T20:33:28Z | `6f6558ad3151` |
| `backend/transient-source-retry` | #30 | 2026-09-22T23:41:29Z | `dc5d7cf86728` |
| `backend/trustmf-communication-gap-audit-20260926` | #220 | 2026-09-26T21:11:54Z | `7233485402f0` |
| `backend/trustmf-complete-portfolio-v125` | #88 | 2026-09-24T14:31:31Z | `18e6aea4d17d` |
| `backend/union-communication-transport-limitation-20260926` | #236 | 2026-09-27T01:12:59Z | `41a3a627457f` |
| `backend/union-communications-20260926` | #218 | 2026-09-26T20:54:23Z | `98bc10a9075f` |
| `backend/union-direct-factsheet-fetch` | #48 | 2026-09-23T04:12:11Z | `9d95c6c98a35` |
| `backend/union-monthly-factsheet-retrieval-20260926` | #165 | 2026-09-26T02:20:57Z | `93c578c179a1` |
| `backend/union-omnibus-fallback-v45` | #80 | 2026-09-23T20:17:12Z | `1710099345f4` |
| `backend/uti-cms-communications-20260927` | #237 | 2026-09-27T01:08:26Z | `f2fc29139e64` |
| `backend/uti-communications-20260926` | #219 | 2026-09-26T21:10:40Z | `c77a9685a594` |
| `backend/uti-portfolio-audit-v130` | #93 | 2026-09-24T21:06:25Z | `6c89c13b579a` |
| `backend/wealth-current-insights-structured-payload-20260926` | #231 | 2026-09-26T22:46:12Z | `5678df90e573` |
| `cleanup/696-retention-simulation-workflow-20260926` | #160 | 2026-09-26T01:34:34Z | `1efb26e13c95` |
| `cleanup/retention-simulation-workflow-20260926` | #155 | 2026-09-26T00:46:47Z | `7f9ff9e38a5a` |
| `diag/absl-idcw-nav-gap-20260925` | #143 | 2026-09-25T20:23:01Z | `756c3d13f55c` |
| `diag/amc-historical-nav-sources-20260925` | #130 | 2026-09-25T17:32:02Z | `fa307dbdd472` |
| `diag/amfi-nav-gap-audit-20260925` | #129 | 2026-09-25T17:28:42Z | `4fc682b680c1` |
| `diag/amfi-portfolio-contract-20260926` | #166 | 2026-09-26T02:28:22Z | `5586269e1926` |
| `diag/bajaj-bandhan-communication-evidence-20260926` | #184 | 2026-09-26T06:04:07Z | `82338af49a6e` |
| `diag/bajaj-media-portfolio-catalog-20260926` | #171 | 2026-09-26T03:52:11Z | `727f6521a7d1` |
| `diag/bajaj-outlook-card-transport-20260926` | #186 | 2026-09-26T06:11:00Z | `105799a23b77` |
| `diag/bajaj-outlook-category-20260926` | #185 | 2026-09-26T06:07:42Z | `f648f5f58716` |
| `diag/dsp-nav-id157-20260925` | #134 | 2026-09-25T18:40:26Z | `25fb4ac9af2d` |
| `diag/edelweiss-api-request-contract-20260926` | #170 | 2026-09-26T03:48:23Z | `cc7cdb9a138b` |
| `diag/edelweiss-canonical-portfolio-20260926` | #167 | 2026-09-26T02:33:19Z | `bf2c1e96eefd` |
| `diag/edelweiss-franklin-communications-20260926` | #188 | 2026-09-26T11:30:49Z | `2077356ee92c` |
| `diag/edelweiss-statutory-api-20260926` | #168 | 2026-09-26T02:40:36Z | `d987ed79789f` |
| `diag/franklin-article-api-live-20260926` | #195 | 2026-09-26T12:01:30Z | `7d29c4edcd05` |
| `diag/franklin-article-api-signature-20260926` | #193 | 2026-09-26T11:46:32Z | `75a587a92cba` |
| `diag/franklin-article-endpoint-20260926` | #194 | 2026-09-26T11:59:38Z | `c20fbda7bedb` |
| `diag/franklin-frontend-basefix-20260926` | #192 | 2026-09-26T11:44:22Z | `154f2344ef39` |
| `diag/franklin-frontend-transport-20260926` | #191 | 2026-09-26T11:42:53Z | `f817421cf269` |
| `diag/franklin-official-communication-index-20260926` | #190 | 2026-09-26T11:40:33Z | `a91967a2d839` |
| `diag/groww-hsbc-communications-20260926` | #198 | 2026-09-26T12:59:41Z | `2b65f578640c` |
| `diag/icici-current-blob-portfolio-20260926` | #172 | 2026-09-26T03:54:24Z | `5c5742bde8d8` |
| `diag/icici-media-center-portfolio-20260926` | #164 | 2026-09-26T01:55:42Z | `443b3756601c` |
| `diag/icici-portfolio-contract-20260926` | #163 | 2026-09-26T01:51:44Z | `4dc60974632d` |
| `diag/icici-portfolio-zip-layout-20260926` | #173 | 2026-09-26T03:59:09Z | `8a6a06503647` |
| `diag/iti-mahindra-communication-evidence-20260926` | #180 | 2026-09-26T04:52:56Z | `b8b54a39937e` |
| `diag/kotak-mirae-communications-20260926` | #201 | 2026-09-26T14:11:21Z | `9c1822388c10` |
| `diag/midcap-portfolio-batch1-20260927` | #271 | 2026-09-28T00:53:02Z | `b439c0c0181e` |
| `diag/midcap-portfolio-batch3-contracts-20260927` | #274 | 2026-09-28T01:18:35Z | `8dab7e72e8f5` |
| `diag/midcap-ter-final3-targeted-20260927` | #266 | 2026-09-27T22:14:57Z | `ba8de3eaa097` |
| `diag/midcap-ter-final4-files-20260927` | #263 | 2026-09-27T20:57:48Z | `71605db4cd8a` |
| `diag/midcap-ter-final6-sources-20260927` | #262 | 2026-09-27T20:47:22Z | `1fb483d92bdd` |
| `diag/nav-api-contracts-20260925` | #131 | 2026-09-25T17:36:12Z | `c593d3eaa0cc` |
| `diag/nav-source-row-probe-20260925` | #132 | 2026-09-25T17:40:11Z | `5e0af649a015` |
| `diag/nav-source-row-probe-v2-20260925` | #133 | 2026-09-25T17:43:12Z | `a4c8a93f73d4` |
| `diag/pgim-quant-communications-20260926` | #206 | 2026-09-26T15:47:56Z | `118a5a29d25e` |
| `diag/sbi-sundaram-card-markup-20260926` | #210 | 2026-09-26T16:29:33Z | `723e3615b827` |
| `diag/sbi-sundaram-communications-20260926` | #209 | 2026-09-26T16:23:57Z | `b86916cc1ae1` |
| `diag/sbi-sundaram-link-targets-20260926` | #211 | 2026-09-26T16:48:58Z | `7225012e17f9` |
| `diag/sbi-sundaram-transport-20260926` | #212 | 2026-09-26T18:25:24Z | `aafc548e7ae7` |
| `diag/sundaram-knowledge-api-v2-20260926` | #214 | 2026-09-26T18:32:47Z | `3c36f099f7a0` |
| `diag/trust-uti-union-communications-20260926` | #217 | 2026-09-26T20:53:05Z | `00936c714e38` |
| `diag/union-apex-portfolio-20260926` | #162 | 2026-09-26T01:48:48Z | `47523c6e1f2b` |
| `diag/uti-cms-endpoint-20260926` | #233 | 2026-09-26T22:55:55Z | `d80e948fe8b2` |
| `diag/uti-cms-response-20260926` | #235 | 2026-09-26T23:39:03Z | `51ef624df4de` |
| `diag/uti-js-transport-20260926` | #232 | 2026-09-26T22:47:29Z | `edf5a7a6fc3b` |
| `diag/wealth-uti-transport-v2-20260926` | #229 | 2026-09-26T22:36:38Z | `3458c0e848a1` |
| `docs/696-retention-simulation-handoff-20260926` | #161 | 2026-09-26T01:37:17Z | `671515cd3def` |
| `docs/absl-idcw-gap-handoff-20260925` | #145 | 2026-09-25T20:31:35Z | `3b2b1eabe4a6` |
| `docs/axis-watch-handoff-20260925` | #121 | 2026-09-25T06:27:31Z | `012ad41dab53` |
| `docs/backend-handoff-2026-09-23` | #76 | 2026-09-23T17:47:46Z | `900d1a1c3fe8` |
| `docs/backend-handoff-2026-09-23-v45` | #82 | 2026-09-23T20:23:29Z | `5e0a7a45cdf7` |
| `docs/current-backend-handoff-20260927` | #238 | 2026-09-27T01:45:50Z | `14f6130f004f` |
| `docs/edelweiss-portfolio-audit-20260925` | #107 | 2026-09-25T03:24:36Z | `bb22bbbd16d6` |
| `docs/handoff-groww-run148` | #79 | 2026-09-23T17:57:44Z | `26cd35188832` |
| `docs/handoff-midcap-benchmark-portfolio-20260927` | #273 | 2026-09-28T01:10:55Z | `22169a9cef33` |
| `docs/handoff-midcap-history-20260927` | #249 | 2026-09-27T11:39:01Z | `823cab9a00bf` |
| `docs/handoff-midcap-launch-gate-20260927` | #282 | 2026-09-28T03:03:26Z | `8be4e0dcb11d` |
| `docs/handoff-midcap-portfolio-batch3-20260927` | #280 | 2026-09-28T02:39:58Z | `0ba56730da3c` |
| `docs/handoff-midcap-source-audit-20260927` | #252 | 2026-09-27T12:06:33Z | `07115d5a25bb` |
| `docs/handoff-midcap-ter-batch1-20260927` | #261 | 2026-09-27T17:58:49Z | `2a12a6684bd7` |
| `docs/handoff-midcap-ter-final3-20260927` | #267 | 2026-09-27T22:26:02Z | `99ee156be43d` |
| `docs/handoff-midcap-ter-gaps-20260927` | #258 | 2026-09-27T17:33:45Z | `956845ca9216` |
| `docs/handoff-midcap-ter-selector-20260927` | #256 | 2026-09-27T15:53:42Z | `4a2f7b6f67b4` |
| `docs/handoff-publication-reserve-20260927` | #240 | 2026-09-27T01:58:15Z | `f123c64c8089` |
| `docs/handoff-storage-health-20260927` | #242 | 2026-09-27T03:11:10Z | `9832e58b4cc8` |
| `docs/icici-portfolio-recheck-20260925` | #110 | 2026-09-25T04:23:13Z | `2776411596e7` |
| `docs/icici-recovery-handoff-20260926` | #177 | 2026-09-26T04:33:34Z | `40e7007dd548` |
| `docs/midcap-batch5-quality-handoff-20260927` | #288 | 2026-09-28T04:33:37Z | `b397b199da53` |
| `docs/midcap-benchmark-649-handoff-20260928` | #295 | 2026-09-28T13:34:55Z | `fa29e1cb74d8` |
| `docs/midcap-benchmark-650-handoff-20260928` | #297 | 2026-09-28T13:58:02Z | `83371e06f9e2` |
| `docs/midcap-evidence-handoff-20260928` | #289 | 2026-09-28T04:52:39Z | `bad66b1ed855` |
| `docs/midcap-freshness-handoff-20260928` | #291 | 2026-09-28T05:26:28Z | `995a7ac49e9d` |
| `docs/midcap-invesco-653-handoff-20260928` | #301 | 2026-09-28T15:19:29Z | `6803628dbdc2` |
| `docs/midcap-role-652-handoff-20260928` | #299 | 2026-09-28T14:39:39Z | `d3de21daae35` |
| `docs/nav-gap-audit-handoff-20260925` | #136 | 2026-09-25T18:54:53Z | `a667db64db29` |
| `docs/performance-audit-policy-handoff-20260925` | #142 | 2026-09-25T19:59:58Z | `65f71f535be1` |
| `docs/performance-benchmark-contract-handoff-20260925` | #138 | 2026-09-25T19:15:14Z | `e88f8edd7af8` |
| `docs/performance-coverage-handoff-20260925` | #123 | 2026-09-25T15:44:26Z | `3300c397c738` |
| `docs/portfolio-blockers-20260925-v2` | #106 | 2026-09-25T03:10:32Z | `29350333070c` |
| `docs/portfolio-limitations-handoff-20260925` | #113 | 2026-09-25T04:38:00Z | `25f75a76c635` |
| `docs/portfolio-recovery-queue-handoff-20260925` | #116 | 2026-09-25T04:51:49Z | `7abfc181c3f1` |
| `docs/post-audit-retention-review-handoff-20260926` | #158 | 2026-09-26T01:20:15Z | `ecf95b271956` |
| `docs/repository-audit-handoff-20260928` | #309 | 2026-09-28T17:44:42Z | `2eb5f4238650` |
| `docs/retention-plumbing-handoff-20260925` | #148 | 2026-09-25T21:02:37Z | `dd01eadd496d` |
| `docs/retention-simulation-handoff-20260926` | #156 | 2026-09-26T00:48:34Z | `da4f7601a94e` |
| `docs/split-storage-handoff-v2` | #26 | 2026-09-22T22:35:56Z | `9b176cabb538` |
| `docs/static-benchmark-ui-handoff-20260925` | #140 | 2026-09-25T19:39:17Z | `af8db0537b87` |
| `docs/tri-identity-handoff-20260925` | #128 | 2026-09-25T17:24:36Z | `e720ebeeb622` |
| `expand-amc-data-coverage` | #4 | 2026-09-09T19:58:03Z | `bf03db1045d0` |
| `expand-amc-disclosures` | #1 | 2026-09-07T21:08:11Z | `f4cc84550868` |
| `expand-sbi-mirae-motilal` | #2 | 2026-09-08T13:32:58Z | `550211e5a62f` |
| `feature/groww-ber-20260925` | #101 | 2026-09-25T02:27:57Z | `dd3e3dac940f` |
| `feature/mirae-ter-20260925` | #100 | 2026-09-25T02:07:01Z | `3e969ff087f5` |
| `feature/uti-ber-20260925` | #103 | 2026-09-25T02:47:36Z | `603cad05470c` |
| `fix-sbi-factsheet-association` | #3 | 2026-09-08T23:45:12Z | `9f4942e9b42d` |
| `fix/axis-preferred-complete-api-20260925` | #118 | 2026-09-25T05:21:49Z | `29e8ddae2753` |
| `fix/coverage-record-date-ranges-20260928` | #305 | 2026-09-28T16:45:20Z | `8948430c53cf` |
| `fix/current-eligible-retention-simulation-20260925` | #154 | 2026-09-26T00:43:10Z | `c4466a246ce7` |
| `fix/direct-fee-summary-20260925` | #102 | 2026-09-25T02:32:53Z | `ef50835064b8` |
| `fix/edelweiss-api-diagnostic-fallback-20260926` | #169 | 2026-09-26T03:44:17Z | `8255a7d9e0b5` |
| `fix/export-materialization-token-20260928` | #306 | 2026-09-28T17:06:03Z | `0815c8c293c4` |
| `fix/franklin-reviewed-tri-identity-20260925` | #127 | 2026-09-25T17:21:22Z | `d628a64da707` |
| `fix/franklin-tri-repair-gate-20260925` | #126 | 2026-09-25T16:29:33Z | `8fc8bab2845d` |
| `fix/icici-handoff-format-20260925` | #111 | 2026-09-25T04:25:03Z | `6c1fb158fb74` |
| `fix/kotak-current-link-identity-20260926` | #203 | 2026-09-26T14:19:34Z | `b4cc6def866e` |
| `fix/kotak-monthly-outlook-title-20260926` | #204 | 2026-09-26T14:21:20Z | `710a0cea9e12` |
| `fix/kotak-robots-link-only-20260926` | #205 | 2026-09-26T14:23:54Z | `f190e1def84a` |
| `fix/midcap-batch5-evidence-quality-20260927` | #285 | 2026-09-28T04:07:10Z | `ea3ee648c880` |
| `fix/midcap-benchmark-documents-20260928` | #296 | 2026-09-28T13:44:39Z | `6a06af3a2f13` |
| `fix/midcap-benchmark-invesco-20260928` | #300 | 2026-09-28T15:05:40Z | `22a4d46cd1d9` |
| `fix/midcap-benchmark-labels-20260928` | #294 | 2026-09-28T13:19:35Z | `a7ff8732ff60` |
| `fix/midcap-benchmark-role-20260928` | #298 | 2026-09-28T14:22:36Z | `725944fb5f34` |
| `fix/midcap-evidence-20260928` | #287 | 2026-09-28T04:38:55Z | `90adbef303ee` |
| `fix/midcap-jm-portfolio-date-20260927` | #284 | 2026-09-28T03:50:27Z | `f7e1d7e9e14d` |
| `fix/midcap-kotak-ter-identity-20260927` | #265 | 2026-09-27T21:20:15Z | `c15c31d41250` |
| `fix/midcap-mahindra-table-sections-20260927` | #286 | 2026-09-28T04:22:45Z | `64c812f4ef7e` |
| `fix/midcap-portfolio-contract-diagnostic-bootstrap-20260927` | #276 | 2026-09-28T01:37:09Z | `27ed670f9c9c` |
| `fix/midcap-readiness-freshness-20260928` | #290 | 2026-09-28T05:08:47Z | `0632014d2b86` |
| `fix/midcap-samco-ter-20260928` | #293 | 2026-09-28T05:56:59Z | `bd7a34f890a3` |
| `fix/midcap-ter-amc-contract-20260927` | #253 | 2026-09-27T15:17:10Z | `9dc5e6c9c1ed` |
| `fix/midcap-ter-category-selector-20260927` | #255 | 2026-09-27T15:44:15Z | `379632708279` |
| `fix/midcap-ter-date-parser-20260927` | #251 | 2026-09-27T11:59:46Z | `d9cffea04b5a` |
| `fix/midcap-ter-pagination-20260927` | #254 | 2026-09-27T15:28:44Z | `5133a711946f` |
| `fix/midcap-uti-portfolio-20260927` | #278 | 2026-09-28T02:17:52Z | `7e0966dbef32` |
| `fix/midcap-uti-portfolio-entry-scan-20260927` | #279 | 2026-09-28T02:28:11Z | `0f84edaf24d0` |
| `fix/package-manifest-20260928` | #304 | 2026-09-28T16:31:03Z | `fcfa23c8d634` |
| `fix/persist-midcap-portfolio-batch3-contracts-20260927` | #275 | 2026-09-28T01:27:28Z | `984758df6127` |
| `fix/recovery-queue-record-build-import-20260925` | #115 | 2026-09-25T04:48:16Z | `7499d02ecb2b` |
| `fix/retention-plumbing-regression-20260925` | #147 | 2026-09-25T20:58:53Z | `4bb221dc847c` |
| `fix/retention-simulation-active-checkpoint-20260925` | #151 | 2026-09-25T21:55:12Z | `afb2d22d4c79` |
| `fix/retention-simulation-manifest-lock-20260925` | #152 | 2026-09-25T22:01:41Z | `0cd39b8700b6` |
| `ops/least-privilege-publisher-20260928` | #303 | 2026-09-28T16:18:27Z | `dbaf3868951d` |
| `ops/midcap-universe-preview-20260927` | #244 | 2026-09-27T03:58:04Z | `eff0f3c979e9` |
| `ops/nonblocking-new-communication-recovery-20260926` | #224 | 2026-09-26T21:35:37Z | `a2249d128030` |
| `ops/pin-all-workflow-actions-20260928` | #308 | 2026-09-28T17:33:42Z | `42a73240c3ed` |
| `ops/remove-obsolete-communication-probe-20260926` | #234 | 2026-09-26T22:57:29Z | `80aa39a58c2b` |
| `ops/retire-completed-push-recovery-20260928` | #307 | 2026-09-28T17:22:38Z | `c824cab808c5` |
| `ops/run-retention-simulation-once-20260925` | #153 | 2026-09-25T22:03:39Z | `27aceb4562eb` |
| `ops/universal-pr-regression-20260928` | #302 | 2026-09-28T16:06:09Z | `ae6036b3867d` |
| `storage/activate-split-checkpoints-v2` | #23 | 2026-09-22T22:20:51Z | `8a2924550228` |
| `storage/delete-oldest-legacy-checkpoint` | #27 | 2026-09-22T22:50:58Z | `a907d3a61644` |
| `storage/narrow-parser-materialization-v2` | #25 | 2026-09-22T22:32:12Z | `e301c7152842` |
| `storage/remove-one-time-cleanup-step` | #28 | 2026-09-22T22:56:30Z | `44ed346d3ebf` |
| `storage/split-checkpoint-format-v2` | #22 | 2026-09-22T22:15:46Z | `c04b20c2cc82` |
| `storage/storage-breakdown-2026-09-22` | #21 | 2026-09-22T21:58:13Z | `5670137df255` |
| `storage/thin-restore-v2` | #24 | 2026-09-22T22:28:55Z | `0fdb64d182cf` |
| `ui/accessibility-polish-2026-09-22` | #9 | 2026-09-22T18:23:22Z | `4a4750cc5a57` |
| `ui/add-5y-cagr-2026-09-22` | #20 | 2026-09-22T21:47:41Z | `9d562eb3d769` |
| `ui/compact-mobile-fund-cards-2026-09-22` | #15 | 2026-09-22T21:23:19Z | `bd3d8a246b9f` |
| `ui/data-updates-refresh-2026-09-22` | #8 | 2026-09-22T18:13:48Z | `6f2bfa1ba8fe` |
| `ui/desktop-fund-table-2026-09-22` | #16 | 2026-09-22T21:26:40Z | `f2eafccf4c25` |
| `ui/fix-fund-table-header-2026-09-22` | #18 | 2026-09-22T21:39:57Z | `905bb8f4f964` |
| `ui/fund-detail-refresh-2026-09-22` | #6 | 2026-09-22T18:00:31Z | `4814fe27eac6` |
| `ui/fund-directory-refresh-2026-09-22` | #7 | 2026-09-22T18:05:32Z | `18aba14ceb37` |
| `ui/minimal-redesign-2026-09-22` | #10 | 2026-09-22T19:27:14Z | `fc74f2082332` |
| `ui/minimal-research-tabs-2026-09-22` | #11 | 2026-09-22T19:39:50Z | `49ea3e325a52` |
| `ui/navigation-refresh-2026-09-22` | #5 | 2026-09-22T17:29:30Z | `2274727854d9` |
| `ui/remove-public-refresh-button-2026-09-22` | #19 | 2026-09-22T21:44:29Z | `84168417347d` |
| `ui/research-desk-2026-09-25` | #149 | 2026-09-25T21:18:18Z | `060553a537ec` |
| `ui/static-benchmark-contract-20260925` | #139 | 2026-09-25T19:36:05Z | `d4fa81d90f7a` |
| `work/sbi-portfolio-20260924` | #86 | 2026-09-24T06:35:50Z | `df513d475fd3` |

Full machine-readable evidence is in `docs/BRANCH-CLEANUP-AUDIT.json`.
