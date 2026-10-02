# Mid Cap backend handoff

Read this alongside the latest generated artifacts and their exact production run. A green workflow, a fresh summary or an isolated source preflight does not establish coverage for every family. Mid Cap remains staged and non-public.

## Latest committed evidence reviewed — 2026-10-02

### Bounded ICICI TER investigation — source access blocked

Investigation branch `diag/icici-ter-evidence-20261002` starts at repair/handoff
commit `068f181018cbaad7945e53db5b30614271d9d0fd`, which includes the **unmerged**
test repair `9e8ee21d3540b7069c8fae3f95f7fc2a61cf465e`. This slice changes only
documentation. No parser fix is justified yet, and no production data changed.
Remote main and repair refs were checked immediately before branching and were
unchanged. The GitHub API denial was not retried.

Evidence establishes the failure boundary, not the upstream root cause:

- At evidence commit `087ba55634a9db3503117f22af61d4505b8f5799`, batch 1 built
  **2026-09-30T05:03:08+00:00** recovered ICICI Prudential Mid Cap Fund through
  `financial_disclosure_api`, with source record date **2026-09-28**, Regular TER
  **1.85** and Direct TER **1.11**. Workbook SHA-256:
  `84208bcc5a36576428ea6e049794843226fab2c17f4e31b4900893ead0d56bff`.
  The source was the official September workbook:
  `https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx`.
- At `fe21c5dc3cded97ec1fd0b6bb4a849a19d837ada`, batch 1 built
  **2026-09-30T22:32:44+00:00** reports `ICICI TER workbook columns changed`.
  The error is raised before exact-family selection: at least one A–L header
  differs from `_ICICI_HEADER` in the third decoded worksheet row. Neither
  `tracker/amc_expenses.py` nor `tracker/midcap_ter_first_party.py` changed between
  the successful and failing evidence commits. This rules out a change to those
  parsers between these checkpoints, but does not prove which source bytes or
  discovery route the failing run used.
- The failed result records no source URL, content hash, mismatched column,
  discovery channel or source reporting date. Those values remain **unknown**;
  the batch build time is not the source date. Current readiness correctly leaves
  ICICI Mid Cap TER values, date and source null. Historical 1.11/1.85 values must
  not be republished or retimestamped as current.
- Confirmed affected target: **ICICI Prudential Mid Cap Fund**, both plan values
  withheld. The Small Cap TER parser uses the same XML reader/header contract,
  so it is potentially affected by the same workbook change; this investigation
  does not establish a fresh Small Cap failure or effects on other AMC funds.
- `_icici_inline_strings` supports inline text and raw cell values but does not
  resolve shared-string indices. A shared-string encoding change, inserted rows,
  or changed header wording could each produce this error. None is proven without
  the actual failing workbook. Mid Cap tests currently mock decoded rows, while
  Small Cap tests construct inline-string XML; their success cannot demonstrate
  compatibility with the unavailable response.

No retained real ICICI workbook/database was found in this checkout or the local
workspace search. One normal request to the September workbook above returned
**HTTP 403**, `server: envoy`, `content-type: text/plain`, `content-length: 16`
(response Date **2026-10-02T22:38:17Z**). No workbook was downloaded; this is not
evidence that the AMC removed the workbook. Source access stopped at that denial;
no alternate host, proxy, security-setting change or TLS bypass was attempted.

Required evidence to continue: permit normal HTTPS access to
**`app.beta.icicipruamc.com`** for that workbook, or provide the original failed-run
workbook plus its source URL/hash. Reproducing the exact discovery path additionally
requires the normal **`apimf.icicipruamc.com`** categories/files endpoints (not
attempted in this bounded slice). Parent owns permission and sequencing decisions.
Once bytes are available, inspect raw OOXML cell types/header positions and exact
scheme/date rows, compare against the recorded successful hash, and reproduce the
failure before proposing a reusable reader correction. A newly fetched mutable
September URL need not contain the September 30 failed-run bytes.

Fresh focused checks on the unchanged application: **5 Mid Cap first-party TER
tests passed in 0.002s** and **44 AMC expense tests passed in 10.168s**. These
exercise existing fixtures, not the blocked source. The full 844-test repair
verification remains recorded in HANDOFF.md; it was not needlessly rerun for this
documentation-only investigation. No merge, deployment, network change or source
recovery is claimed.

### Dated readiness snapshot

At remote main `fe21c5dc3cded97ec1fd0b6bb4a849a19d837ada`, the launch report
evaluated **2026-09-30T22:37:28.080093+00:00** supersedes the earlier checkpoint's
coverage counts below: AUM **34/34**, Direct TER **29/34**, benchmark identity
**28/34**, current portfolio evidence **22/34**, and complete portfolios **6/34**.
All 14 input hashes match; the 22 current/six complete portfolio counts were
independently recounted, with accepted reporting dates **2026-08-31**. Remaining
numerical deficits are **two TER, three benchmark identities and six portfolios**.
Source-fetch health is true in this committed report. No October source fetch or
new live-production verification is implied. Mid Cap is still non-public and
`data_ready=false`, `launch_ready=false`, `public_export_enabled=false`.

The next bounded missing-data investigation should reproduce **ICICI's TER
workbook column mismatch** from first-party batch 1, inspect the exact returned
workbook headers, scheme/plan identity and source date, then add a fixture-backed
parser correction only if supported by that evidence. Its benchmark PDF also
timed out with HTTP 504; that transport result is separate and does not prove a
parser defect. The Wealth Company TER timed out; ABSL's benchmark failed the
one-Fund-Snapshot-table contract. Do not repeat the older claim that the TER and
benchmark gates currently pass. Keep all remaining families and nulls visible.

For the continuing portfolio roadmap, Kotak still fails identity in both batches
1 and 5. Reproduce the actual production response before changing accepted
headings or counting its earlier isolated preflight. The twelve-family portfolio
list below remains applicable. None of these source investigations requires
merging the test-only ICICI repair to inspect evidence, but the requested first
GitHub-repair milestone is currently blocked by API network access (see
[HANDOFF.md](HANDOFF.md)); no concurrent parser implementation was started.
Any future production integration requires explicit merge authorization, and
the public-surface gate remains separate.

## Verified production checkpoint — 2026-09-30

Production [#684 / 36671423719](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36671423719) completed successfully on code `feefbb15025077b2e05e848edb9c9d31a6b53d9b` (PR #348), with generated evidence commit `087ba55634a9db3503117f22af61d4505b8f5799`. Build job `109747037093` and deploy job `109755440959` passed. The latest launch report was evaluated **2026-09-30T05:06:24.056660+00:00**, separately from the **05:35:53** public status build and **05:36:47Z** terminal deployment time. Cache-busted live status, fund-index and coverage reads matched the exact public build and NAV **2026-09-29**. Small Cap retains **36 families, 143 series and 281,868 NAV observations**; the live index reports 142 latest dates on September 29 and one on April 24, 2020. Its category identities and summed observations were independently checked.

| Measure | Current production evidence | Required policy |
| --- | ---: | ---: |
| Staged scheme/NAV history | 135/135 codes, 353,423 observations through 2026-09-29 | All staged codes |
| AUM | 34/34 | 34/34 |
| Direct TER | 31/34 | At least 31/34 |
| Reported benchmark identity | 31/34 | At least 31/34 |
| Current portfolio evidence | 22/34 | At least 28/34 |
| Complete current portfolios | 6/34 | Separate measure |

`data_ready=false`, `launch_ready=false`, `public_export_enabled=false`. `audit_input_integrity=true`; `input_issues=[]`. All **14 input-file hashes** were independently recomputed against this checkpoint, and current/complete portfolio counts were recalculated from the accepted rows. Current portfolio evidence reports **2026-08-31**. The six complete accepted portfolios are HDFC (81 positions), Helios (74), Mirae Asset (68), Invesco (43), Motilal Oswal (32) and Sundaram (79). Current presence remains distinct from a fresh successful fetch of every source: the source-coverage report records an **AMFI daily-AUM HTTP 502**, and source-fetch health remains false. Do not count retained AUM as a successful AMFI request in that run.

The benchmark gate is numerically satisfied; the earlier Invesco/ICICI/Franklin/UTI/JM recovery tasks below have progressed and must not be repeated from the old priority list. Remaining benchmark gaps are Trust, Union and WhiteOak. Portfolio evidence still needs six more families to reach the policy minimum; the category-aware exporter/API/static-data/UI dry run remains separate and blocked. Names do not establish available benchmark TRI history.

## Deployed Helios recovery — PR #348

[PR #348](https://github.com/Vasuki8/Smallcap-Ledger/pull/348) adds **Helios Mid Cap Fund** to the existing portfolio batch 2. It adds no audit artifact, database schema, dependency, launch threshold or public-category switch.

Production batch 2 freshly observed **74 positions, complete=true, unknown_rows=[]**, sheet **HMCF**, reporting date **2026-08-31**, at **2026-09-30T05:04:46+00:00**. The workbook SHA-256 is `375e9f39754882d43677cfd45f95a57572a89b8eb4de04895cf88780a432f181`; production discovery-page SHA-256 is `3680c51e4fd443e74a4897885060557f78eac5c0ac11ad880dcf7a9edc793003`. The workbook matches the earlier preflight; the actual discovery-page bytes differ. The fresh combined report accepts Helios as current and complete. Production passed **844 tests in 8.445s**, generated-site validation, archive publication and Pages deployment. No new visual/mobile browser pass is claimed for this backend-only change.

Discovery uses `https://www.heliosmf.in/portfolio-disclosure`: exactly one Monthly Portfolio section, exactly one Helios Mid Cap Fund scheme section, the expected month label, a unique approved HTTPS workbook link and its complete explicit reporting date. Large & Mid Cap and half-yearly disclosures cannot supply the evidence. Duplicate identical links are one source; distinct current links fail closed. Credential markers (including empty userinfo), unapproved hosts/ports and malformed/stale source paths are rejected.

The workbook is parsed in memory with the existing exact-family/date structured parser. That parser's issuer, unknown-row, duplicate and net-asset reconciliation semantics remain unchanged; unrecognized numeric rows keep a snapshot partial. Both discovery and workbook bytes retain actual SHA-256 hashes, media types and source locator. The collector uses `archive=False`, and the standalone source preflight forbids database connections.

Application head: **`df3c945c73d0ad60359d07bea967064f52b29ae2`**. Exact-head [push verification 36670447719](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670447719), job `109744099747`, passed **844 full repository tests** (`Ran 844 tests in 13.977s`, `OK`), compilation and the exact Helios preflight. [Repository regression 36670454506](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670454506), [Mid Cap PR regression 36670454540](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670454540) and [Research UI checks 36670455402](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670455402) all passed. PR runs do not perform the live preflight.

The source preflight observed **2026-09-30T04:48:07+00:00**, sheet **HMCF**, reporting date **2026-08-31**, **74 positions**, `complete=true`, `unknown_rows=[]`.

- Workbook: `https://www.heliosmf.in/wp-content/uploads/2026/09/helios-mid-cap-fund-monthly-portfolio-as-on-31st-august-2026.xlsx`.
- Workbook SHA-256: `375e9f39754882d43677cfd45f95a57572a89b8eb4de04895cf88780a432f181`.
- Exact-head discovery SHA-256: `62f5670ec554218be41805d59ee0557ed2010ba3f121d9fcfb9c1849f2e51114`.
- Locator: `Monthly Portfolio / Helios Mid Cap Fund / August 2026`; parser version `helios-midcap-monthly-workbook-v1`.

Ten new tests exercise real in-memory XLSX parsing and discovery boundaries. Their first run failed for the absent reader and missing batch integration; they then passed. Independent read-only code review found no blocking issues. Its empty-userinfo suggestion was reproduced with failing tests, corrected and verified. The local full suite passes **844 tests** after that correction. An initial sandboxed full-suite attempt hung in an existing in-process API test; the unchanged test and full suite passed outside the sandbox. No application change was made for that execution-environment issue.

The shared `providers.fetch` API follows public redirects without returning the final URL; redirect-host pinning remains an existing transport-wide limitation, separately deferred. This bounded repair validates selected source URLs and actual returned hashes under the existing client contract.

The user explicitly authorized the merge. PR #348 was squash-merged at **2026-09-30T05:00:28Z**, with expected head `d41c762541ce86c8bc88cd2a26b560825e40b4a2`, into code commit `feefbb15025077b2e05e848edb9c9d31a6b53d9b`. Final-head Repository regression [36670974257](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670974257), Mid Cap PR evidence [36670974174](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670974174), Research UI [36670974188](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670974188) and exact-source push verification [36670971628](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36670971628) all passed before merge. Production and independent live-data verification are complete. The pre-release checkpoint (#683) reported 21/34 current and five complete portfolios; use the fresh 22/34 and six complete above.

## Next action

Continue exact first-party portfolio recovery from the current twelve unavailable families: Edelweiss, Franklin, HSBC, Kotak, LIC, Nippon India, Quant, Trust, Taurus, The Wealth Company, Union and WhiteOak. Six additional current families are needed for the policy minimum. Helios is verified in production; do not reimplement its reader or reuse an old count.

Kotak passed a fresh read-only check earlier in this session (**68 equity positions, partial, 2026-08-31**), but both production batch 1 and batch 5 again recorded identity failures in #684. Keep the discrepancy explicit; reproduce the production response before changing identity validation or counting recovery. ABSL remains recovered in the current run (78 positions, partial), so the historical 503 below is not the current task. Source-fetch health still needs a successful new AMFI observation, not retimestamped last-good evidence. Only after data/input-integrity gates pass should the separate category-aware public-surface dry run proceed; the launch report never enables Mid Cap itself.

## Historical checkpoint through PR #300

The following chronology is preserved for parser contracts and historical source evidence. Its counts, production run, source outcomes and next-task notes are superseded by the current sections above.

### Historical verified checkpoint (#653)

- **Code: PR #300**, Invesco India Mid Cap Fund primary-benchmark recovery from a dated AMC factsheet. Squash merge: `f8ab83dd20970efa93d38c983cbb79c0fa694946`. This adds one source to existing benchmark batch 2; the PR #298 ABSL/SBI role correction and all earlier freshness safeguards are preserved.
- **Final tested head:** `22a4d46cd1d9272f7dedd344dcc248da74d256f6`. [Branch verification 36440199684](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36440199684), **attempt 2**, job `108989263321`, passed syntax checks, **749 full repository tests** (`Ran 749 tests in 72.806s`, `OK`) and **5/5 actual read-only benchmark-source preflights, `errors=[]`**. Attempt 1's ABSL HTTP 503 and the normal same-head recovery are retained below.
- [PR regression 36440559060](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36440559060) and [Research UI checks 36440559248](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36440559248) both passed before merge. PR-triggered runs skip source preflights; the exact-head push run above is the source-preflight evidence. Samco and batch-5 preflights were not rerun on this benchmark branch.
- **Production:** [run #653 / 36440964786](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36440964786), **build and deploy completed successfully on 2026-09-28**. Build job `108991006729` passed staged audits, repository regressions, generated-site validation, cumulative archive publication and status recording. Deploy job `108994540481` completed at **15:14:14 UTC**. The normal full daily collector was skipped on this push, as designed. The individual ABSL portfolio source failed as recorded below; successful publication does not erase that gap.
- **Evidence commit:** `64480cfccfb932af750fffc6c399980745fcc1ee`, one generated-report commit after the code merge, with no additional application-code changes. Benchmark batch 2 built at `2026-09-28T15:08:58+00:00`; portfolio readiness at `2026-09-28T15:10:19.801844+00:00`; launch readiness at `2026-09-28T15:10:19.880936+00:00`. Required portfolio reporting month-end: **2026-08-31**.
- **Input integrity:** **14/14 checks passed; `input_issues=[]` and `audit_input_integrity=true`**. Source observation, document period, report generation, status build and terminal deployment are distinct clocks.
- **Small Cap coverage:** `COVERAGE-AS-OF.md` built at `2026-09-28T15:13:02+00:00` reports **36 funds, 143 NAV series, AUM and Direct fee coverage 36/36**, latest included NAV **2026-09-25**. The public Small Cap category remains intact; no new visual/mobile browser pass is claimed.

Verification scope: local parser red-to-green checks, remote failing-then-passing batch integration, full repository CI, actual source preflight, exact-diff self-review and the production evidence above. No independent human/subagent review is claimed. No public UI, dependencies, launch thresholds, source permissions or Mid Cap publication switch changed.

### Historical staged readiness (#653)

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 | 34 / 34 |
| Direct TER | 31 / 34 | At least 31 / 34 |
| Reported benchmark identity | **17 / 34** | At least 31 / 34 |
| Current portfolio evidence | **15 / 34** | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Separate measure; never relabel partials |

Benchmark batch 2 recovered **9/10** targets; JM's existing exact-page identity failure remains explicit. The new Invesco result is present in production: **BSE 150 Midcap TRI**, PDF page **11**, document period **2026-08**, observed at **2026-09-28T15:08:58.983559+00:00**, source SHA-256 `85b405dab788875aff4b31748bd1efab4424c73c9339cef207415595804d4a5a`. This matches the preflight PDF hash, but the production observation is distinct. Combined reported benchmark coverage increased from **16 to 17/34**.

**Do not repeat the previous 16/34 portfolio count as current.** In run #653 the unchanged ABSL portfolio-discovery page `https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio` returned **HTTP 503 Service Unavailable**. Portfolio batch 4 recovered PGIM and Mirae (2/3); ABSL is unavailable in the current combined report. Its earlier 78-position August observation is historical evidence, not a successful fetch in this run. This is separate from the earlier preflight 503 on ABSL's benchmark page, which recovered on retry. No common internal cause, permanent outage, portfolio change or parser defect is established.

All **15** accepted current portfolio rows report **2026-08-31**. The four complete portfolios remain **HDFC (81 positions), Mirae Asset (68), Invesco India (43) and Sundaram (79)**. Invesco's portfolio workbook was freshly observed at **2026-09-28T15:10:15+00:00**; it was not copied or retimestamped from a prior run. Kotak remains unavailable.

The latest report is **`data_ready=false`, `launch_ready=false`, `public_export_enabled=false`**. Remaining numerical deficits: **14 more reported benchmark identities and 13 more current portfolio-evidence families**, then the separate category-aware public-surface dry run. Thresholds are tracker product-quality policy, not regulatory rules. Benchmark names do not establish available index series, effective dates or complete/exportable financial records.

## Completed: Invesco first-party primary benchmark

PR #300 adds one benchmark identity source to **existing batch 2**, without adding an upstream artifact or changing the **14-file launch-input integrity contract**. The previous product-page HTML did not expose a usable primary value; the new reader instead uses the dated official AMC factsheet.

Source verified for this slice: `https://www.invescomutualfund.com/docs/default-source/factsheet/invesco-mf-factsheet-august-2026.pdf`.

The PDF cover explicitly reports **August 2026**. On the unique **Invesco India Mid Cap Fund** scheme-detail page, both the **Scheme Benchmark / AMFI Tier I** panel and the **Key Facts / Benchmark Index** field report **BSE 150 Midcap TRI**. The reader requires these two complete values to agree. The observed PDF page is **11** (one-based); the parser locates the exact heading/descriptor rather than hardcoding a page number. Table-of-contents references, another scheme, duplicate detail pages and performance tables cannot supply this identity.

The monthly URL is resolved at collection time using the existing official AMC factsheet pattern, not frozen at module import. Only the latest closed month's explicitly dated document qualifies for this new reader. A missing or stale document stays a gap; there is no fallback that relabels the last-good PDF as current. On a month rollover, a new month's document may not yet be available. This conservative source-specific contract does not change the separate portfolio grace policy or launch thresholds.

The reader validates exact family/URL and staged AMC ownership, PDF media/magic/size, bounded page count, explicit cover period, exact scheme heading/descriptor and reviewed section boundaries. It rejects missing or historical/additional-only roles, unknown or conflicting primary values, compound values and extra suffixes rather than extracting an expected-name substring. TRI/PRI is retained only when stated.

Retained fields include publisher wording, source URL, SHA-256, content type, observation timestamp, document period, page, structural locator and the two-role excerpt. Parser version: `invesco-midcap-benchmark-factsheet-v1`. Keep `source_document_period=2026-08` separate from `source_data_as_of=null` and `benchmark_effective_as_of=null`. `benchmark_series_verified=false` remains explicit. This task does not import the BSE index series or any portfolio, fee or performance values.

The PDF also contains additional performance comparators. They are **outside this reader's collection scope**. Its empty `additional_benchmarks` list must not be interpreted as proof that the publisher has no additional comparator. No comparator is promoted to the primary role.

### Verification and source limitations

The 22 parser tests were written before implementation and failed for the missing source module, then passed, including real synthetic PDF extraction. Four new integration tests failed against the unwired original batch in run **36439963869**, then passed after the focused wiring. Full repository coverage increased from **723 to 749 tests**. The local focused checkout is not the full repository and no dependency facades were uploaded.

The exact final-head branch run **36440199684**, attempt 1, passed all 749 tests and the new Invesco preflight, but the unchanged ABSL source returned **HTTP 503**. A normal same-head retry (attempt 2, job **108989263321**) passed syntax, all **749 tests** and **5/5 actual benchmark-source preflights with `errors=[]`**. No ABSL parser or transport workaround was added. Keep both attempts in the execution history; the successful retry does not erase the original source failure.

The successful Invesco preflight observed **2026-09-28T15:03:34.830651+00:00**, page 11, document period 2026-08, source SHA-256 `85b405dab788875aff4b31748bd1efab4424c73c9339cef207415595804d4a5a`. Source preflights forbid `db.connect` and use `archive=False`; they are not production coverage. Use the latest generated batch for the production observation.

**ICICI Prudential remains unresolved.** The tested route `https://digitalfactsheet.icicipruamc.com/fact/icici-prudential-midcap-fund.php` failed TLS certificate verification in the GitHub runner. TLS validation was not disabled. This establishes a limitation of that tested route, not that every ICICI source is unavailable or that the AMC stopped publishing. Do not count an ICICI benchmark from this investigation.

Read-only diagnostics **36438400728**, **36438603687** and **36438967299** remain on `diag/midcap-two-sources-20260928`. The last confirmed the actual official August PDF and its exact text contract. Their diagnostic workflow was **not merged** into the application branch. No recurring production diagnostic was added.

## Prior work that must not be reimplemented

**ABSL/SBI, PRs #296 and #298:** the original expected-name regex could accept additional/historical labels, ignore conflicting primary disclosures and truncate compound values. PR #298 replaced this with complete primary-role validation and added 30 tests; it did not establish that the previously observed names were wrong. ABSL requires the exact scheme heading and actual Fund Snapshot table, checking every complete primary `Benchmark:` cell. SBI requires an exact full KIM heading and one Tier-I role inside the first-page Benchmark Riskometer block, ending at the reviewed investor footnote. Preserve duplicate/conflict/whole-value guards and PDF line boundaries.

ABSL's observed document banner is **July 2026**, retained as `source_document_period=2026-07`, not September because it was fetched in September. Its publisher wording is **Nifty Midcap 150 TRI**; reference hash `c21d367231006606430cdb2bb34970a44fca211115b31a93b5d39a15c8b67c14`. SBI's KIM is dated **2025-10-31**, retained separately as `source_document_as_of`; publisher wording **Nifty Midcap 150 Index TRI**, PDF page 1, reference hash `1340f3e97b4c90c9efd0a0623468c81011d4c2532a7ecb223335b1e6b5db66e6`. Both retain `explicit-benchmark-documents-v2`, unknown benchmark effective dates and `benchmark_series_verified=false`. These old document dates are not proof of the newest available AMC disclosure. Use current artifacts for source outcomes/hashes.

**Axis/Mirae, PR #294:** exact non-navigation scheme headings and reviewed primary roles. Axis requires its primary banner and percentage/rupee performance columns to agree; **BSE Midcap 150 TRI** is distinct from its additional **Nifty 50 TRI** comparator. Mirae requires the exact `benchmark index` fund-fact card and preserves **NIFTY Midcap 150 (TRI)**. Performance/AUM/NAV dates are not benchmark effective dates. Original proof is deep-copied into the combined report. These readers and legacy reconciliation precedence are unchanged; do not generalize their validation to every older benchmark reader.

**Samco TER, PR #293:** the exact AMC-scoped fallback repaired category-17 omission and AMFI's plural category wording. Dynamically resolve the AMC, preserve complete bounded pagination, exact name/NSDL `SAMC/O/E/MIF/25/10/0013`, category/type, current-month non-future dates and both plans' published TER/component reconciliation. BER is not substituted for TER. Historical September 25 observations are not constants to paste into future results. Bandhan, Bank of India and WhiteOak remain the previously documented TER limitations unless a later artifact proves recovery.

**Freshness, PR #290:** select portfolio reporting month before completeness. A newer valid partial displaces an older complete snapshot. Preserve the 10-day grace rule, exact family/AMC, valid named-position counts, boolean completeness, source hashes and reporting/observation clocks. Keep stale/alternate/excluded evidence explicit. Establish `MIDCAP_AUDIT_STARTED_AT` before staged audits and verify five core inputs plus nine producing batches; a new summary cannot conceal old, malformed or failed input. Independently recalculate portfolio counts at launch evaluation. Missing inputs must produce a fresh blocked report. A future new upstream batch needs matching CLI/`UPSTREAM_FILES` changes and stale/missing-input tests; PR #300 adds no batch.

**Portfolio corrections, PRs #285–#287:** Mahindra's original 63-position extraction included sector headings; the corrected source has 59 issuers with 16 sector subtotals reconciling to 97.71% equity. Preserve `factsheet_equity_only`, `complete=false`, issuer/footer/duplicate guards and [MIDCAP-EVIDENCE-CORRECTIONS.md](MIDCAP-EVIDENCE-CORRECTIONS.md). Sundaram's discovery-card AUM date does not date its workbook: verify exact scheme/code MC and workbook reporting date independently. Do not borrow NAV/AUM dates to label a portfolio current.

**Invesco/Kotak portfolios:** #649's Invesco 502 was followed by normal recovery in #650 and #652, with 43 positions in the exact August workbook. Use the latest batch outcome; a past successful fetch is not a fresh observation, and one upstream failure is not evidence of a permanent outage or parser defect. Kotak's earlier isolated 68-issuer preflight is not production coverage when the exact scheme gate fails. Never copy it into a report or weaken identity rules merely to increase coverage. PR #300 changes no portfolio reader.

The preceding full checkpoint and detailed correction history are preserved in [the pre-#300 handoff](https://github.com/Vasuki8/Smallcap-Ledger/blob/d6ba0ae3367c2deae95923727c010607492fd0b9/docs/MIDCAP-HANDOFF.md) and its linked runs/plans. New numerical coverage claims require the exact fresh evidence checkpoint above.

### Historical next-task notes (superseded)

First recheck the **ABSL portfolio-discovery HTTP 503** against its normal official route. Restore a current count only after a successful new observation and production reconciliation. Require a repeatable transport/source contract before changing code; do not retimestamp the old workbook, weaken validation or add another permanent diagnostic on every production push.

Continue exact first-party benchmark recovery from the latest `remaining_families` list. **Invesco is implemented; do not repeat the failed product-page approach.** Start with a valid official **ICICI Prudential** factsheet/KIM/scheme-document route that explicitly proves the exact staged scheme and primary index without bypassing TLS. Then address **Franklin, UTI and JM** using publisher-proven scheme identities/aliases and designated primary roles, not broad name proximity or the category's usual benchmark.

Preserve full publisher values, primary/additional roles, TRI/PRI wording, source URLs/hashes, evidence location, observation times, document periods and unknown effective dates. Existing ABSL/SBI and Axis/Mirae repairs are complete. Verifying a name is not verifying an importable benchmark time series.

Continue current portfolio recovery toward the 28-family gate using actual unavailable-family/error lists. Require repeatable first-party evidence before changing a transport contract. Preserve freshness-safe current-run validation, partial labels and original observations. Verify Taurus/WhiteOak registration before claiming category-wide AMC document coverage; keep access-blocked routes explicit.

Only after the data and input-integrity gates pass should the separate category-aware **exporter/static JSON/API/UI dry run** proceed. Verify actual exportable metrics/holdings, the correct index series or explicit absence, dates/source/partial/unavailable labels, routing and Small Cap non-regression. Never silently substitute the Small Cap comparator. The launch report itself never enables Mid Cap.

## Operations and source-of-truth artifacts

Mid Cap stays `stage=staged`, `public_export_enabled=false`. Source audits do not promote staged financial data to live tables. The overall publisher still performs its normal Small Cap/archive maintenance; do not describe the entire workflow as making zero database writes. No source-access bypass, spending, subscription change, archive deletion or automatic promotion is authorized by this task.

The existing daily ChatGPT launch-readiness check is unchanged; do not create a duplicate. It cannot change code, merge or publish. Push/email settings were previously recorded disabled and were not rechecked here. The documentation-only handoff commit/merge uses `[skip ci]` to avoid replaying the collector for prose; application-code CI and production verification ran normally and the schedule/workflow remain enabled.

- `docs/MIDCAP-LAUNCH-READINESS.json`: actual/required counts, per-input health, remaining gates and evaluation date; not a launch switch.
- `docs/MIDCAP-BENCHMARK-BATCH2.json` and `docs/MIDCAP-BENCHMARK-READINESS.json`: new Invesco and existing source proof, document periods/page/roles, observation times and errors. Batch 1 contains unchanged legacy evidence.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and portfolio batches 1–5: current/stale/unavailable rows, completeness, source proof and alternate/excluded evidence.
- `docs/MIDCAP-TER-READINESS.json`, both TER batches and `docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json`: AUM/TER evidence and explicit gaps.
- `deployment/midcap-history-status.json`: staged NAV history; `deployment/update-status.json`: separate build/publication status.
