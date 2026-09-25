# Smallcap Ledger backend handoff

## Source-retention audit — NO deletion authorized (2026-09-25 UTC)

The owner approved classification and savings analysis BEFORE deleting anything. Completed report: `docs/SOURCE-RETENTION-AUDIT.md`; per-hash CSV/JSON inventories and summary are adjacent. Final review run **36093073121** passed **299 tests**. Source-pack measurement run **36092819677** checked all **95** packs against release digests. The exact production checkpoint is unchanged, with **629,225 rows** and **2,519 originals**.

Final link-only candidates: **700 files / 404,498,141 raw bytes / 34,253,903 compressed payload bytes** (ZIP headers excluded). These are superseded discovery responses, not proven duplicates or guaranteed recoverable historical files. Current saved document versions, financial evidence, historical extractions, original reports, unknown requests and fragile transport sources remain protected or under review. **Deleted files/bytes: 0.**

No production workflow, source-retention policy, database schema, collector, UI or schedule was changed. Approval of this audit is NOT approval to delete the candidates or retire the old legacy ZIP. Before any approved migration, make restore, replay, archive serving and publication/download code retention-aware, preserve provenance, validate replacement packs and retain rollback until independently verified.

## Database cleanup (2026-09-25 UTC)

**Read `docs/STORAGE-CLEANUP.md` for the current merge, production verification and cleanup status.** This is the storage batch's completion/handoff record; the validation evidence is in `docs/STORAGE-VALIDATION.json`.

The owner requested unnecessary/redundant database storage cleanup. The four NAV/benchmark tables were migrated to composite-primary-key `WITHOUT ROWID` storage on a production copy. All 273 tests, all-table content equality, integrity/foreign-key checks, idempotence, checkpoint restore and generated-site validation passed. Measured database size: **100,773,888 to 73,322,496 bytes**; checkpoint ZIP **12,851,483 to 7,451,746 bytes**. No logical record or original source was removed.

The legacy cumulative ZIP `state-35791406887-1.zip` (**1,087,514,828 bytes**) remains untouched: its retirement action was blocked, so do not claim this storage was reclaimed. Source-retention policy and fund scope are unchanged. After storage publication is verified, resume the previously documented portfolio source-recovery task below.


Updated: 2026-09-25, after Axis full recovery and material source-change watch deployment.







## Latest completed batch: Axis full recovery + blocker source-change watch

**Axis Small Cap Fund is no longer a portfolio or fee-coverage gap, and the remaining blocked portfolio queue now watches for material first-party evidence changes without retrying sources automatically.**

### Axis complete monthly portfolio

Commit `c3713ea704e346b427b232c7d5f6b20dda1555c4` recovered Axis's exact first-party monthly Small Cap workbook through the public statutory CMS flow. Validation run **36097681418** passed all **315 tests** plus production-state/site assertions.

Current retained complete Axis snapshot:
- reporting date: **2026-08-31**
- positions: **134**
- complete: **true**
- source: `https://www.axismf.com/1/5/464/560/3622/4549/Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_4a112f9ef0.xlsx`

The parser strictly reconciles the constituent table and 100% grand total; no holding was inferred from the older factsheet aggregate. The later intramonth fund-page Top-10 snapshot remains retained history but is not preferred over the complete regulatory month-end. Commit `02ee47f1ebb802b165e7732363d0a8e89add3444` fixed fund/API selection accordingly; validation run **36098102438** passed **315 tests** and verified the static Axis export contains all 134 holdings.

### Axis explicit BER and Total TER

Commit `067748b42f3faa7f0dd6ae049cf822aa0ea3fe92` recovered Axis's public generated Total Expense Ratio workbook through the same first-party CMS transport. Validation run **36101232004** passed **323 tests**, production-checkpoint recovery, 36/36 BER+TER assertions and static-site validation.

Current Axis fee evidence as of **2026-09-24**:
- Regular BER **1.34%**
- Regular Total TER **1.68%**
- Direct BER **0.52%**
- Direct Total TER **0.71%**
- source: `https://www.axismf.com/1/5/2125/Total_Expense_Ratio_2026-09-25_06_04_34.xlsx`

The collector separately retains BER, brokerage, transaction cost, statutory levies and Total TER and cross-checks the browser API against the workbook. Axis's older unqualified fund-page expense ratio remains labelled separately; it was not retroactively promoted.

Production workflow **36101432739** completed successfully after the Axis fee recovery. Current coverage is now:
- funds **36**
- AUM **36/36**
- dated Direct fee **36/36**
- reported TER **36/36**
- BER **36/36**
- benchmark identity **36/36**
- portfolios **35/36**
- complete portfolios **29**
- current portfolios **34**
- current + complete portfolios **29**
- partial portfolios **6**
- latest NAV **2026-09-24**

### Material source-change watch for blocked portfolio recovery

After Axis left the recovery queue, the generated queue had **7** remaining items and **0 actionable-now** targets. The remaining cases are verified source/transport or disclosure-precision boundaries, so repeated blind probing would add noise.

PR **#120** merged as commit `2f08bd61c25666e97ddbb14ba6054a3da3bf11ca`. It extends `tracker/portfolio_recovery_queue.py` with a read-only material-change watch for the four `retry_after_source_change` cases.

A blocked fund is promoted to `review_source_change` only when newly retained first-party evidence materially changes, such as:
- a previously blocked exact recovery URL being fetched successfully after the reviewed blocker baseline;
- an exact recovery source-page check moving out of a blocked status;
- Union's watched host transport recovering;
- a new first-party document classified as a portfolio appearing after blocker review.

Routine timestamp refreshes and repeated identical failures do **not** reopen work. The watch itself performs no fetch, retry or portfolio mutation.

Validation run **36102524816** passed all **327 tests** and the restored production checkpoint. It confirmed:
- TER **36/36**
- BER **36/36**
- complete portfolios **29**
- recovery queue items **7**
- actionable now **0**
- material source changes detected **0**

Production workflow **#481**, run **36102660112**, completed successfully through all source upgrades, **327-test** regression gate, site generation/validation, split history publication, queue/status recording, Pages artifact upload and Pages deployment at **2026-09-25T06:25:31Z**.

Final Pages artifact **10850105587** is **230,748,340 bytes** with digest `sha256:1f9acd42747a0a814033925a971cb65c3cdf1ce45233e50ff371d8f4fe62a986`.

Status commit `6def40910f96157dc96ab35b04ad6c0b38451db4` records:
- plans **143**
- NAV observations **281,442**
- benchmark observations **5,329**
- retained portfolio snapshots **124**
- document versions **1,784**
- database bytes **73,347,072**
- latest NAV **2026-09-24**

Current material-change watch state generated at **2026-09-25T06:24:56Z**:
- Union: unchanged host transport blocker;
- Bajaj Finserv: unchanged exact Downloads 403 blocker;
- Edelweiss: no post-review evidence that the statutory portfolio route recovered;
- ICICI Prudential: no post-review evidence that the monthly ZIP/archive transport recovered.

The queue therefore has no justified portfolio source-recovery target right now. Bandhan, Sundaram and UTI remain disclosure-precision cases and must not be completed by estimating censored weights.

No paid service, external communication, UI change, source deletion or retention-policy change was introduced. The **700 link-only source-retention candidates remain untouched**, and the legacy cumulative ZIP has not been retired.

### Next backend task

**Do not probe any portfolio blocker while `source_changes_detected == 0`.** On future runs, inspect `docs/PORTFOLIO-RECOVERY-QUEUE.json` first; if a blocker is promoted to `review_source_change`, review that retained first-party evidence before any live retry.

While the portfolio queue is closed, move the next backend batch to **historical performance / benchmark coverage auditing**. Build a read-only per-plan audit that identifies:
- first and latest NAV date and observation count;
- eligibility for 1Y / 3Y / 5Y displayed returns;
- first/latest overlapping date with the relevant benchmark series;
- missing or unusually large NAV gaps that can affect chart/comparison periods;
- benchmark-series gaps versus merely reported benchmark identity;
- funds where the website can display benchmark identity but lacks enough overlapping TRI observations for the selected performance period.

Do not invent historical returns, forward-fill benchmark values, add paid data, or change the UI in that audit. Use retained NAV/benchmark evidence only, publish the audit in machine-readable and operator-readable form, and use it to choose the next historical-data repair batch.

## Latest completed batch: read-only portfolio recovery queue

**The backend now publishes a deterministic recovery queue for every partial or missing portfolio, ranked by source actionability rather than retained position count. The queue is read-only: generating it performs no source fetch, retry or portfolio mutation.**

PR **#114** merged as commit `24e8a28a22395e31804223d602467d8f47e316a0`. Isolated validation run **36095583451** passed compileall and all **309 tests**, restored the production checkpoint, verified all eight incomplete/missing funds had retained timestamped fetch/source-page evidence, and confirmed the action split and ranking.

The first production attempt, workflow **#476** / run **36095715032**, passed the 309-test gate, site generation/validation and cumulative archive publication, but correctly stopped before deployment when `scripts/record_build.py` could not import the repo-root `tracker` package from script execution context. No bad Pages deployment occurred.

PR **#115** merged the import-path fix as commit `5efcbeb03ac4bb1ed01baea6c3fc00a2f6b43a25`. Focused validation run **36095854354** again passed all **309 tests** and verified the recorder's script-context import. Production workflow **#477**, run **36095921572**, then completed successfully through tests, generated-site validation, cumulative-history publication, recovery-queue recording, GitHub Pages artifact upload and Pages deployment at **2026-09-25T04:50:20Z**.

Final Pages artifact **10847801270** is **230,742,223 bytes** with digest `sha256:7ea3c5d35db32fed41898b41c2bc965bcd285b684b71b41e4b4fa0030c86a482`. Status commit `5bce311a61e5681a6d9c2b695640e76ff67990af` records the deployed collection/coverage state and generated queue.

### Queue contract and published evidence

New module `tracker/portfolio_recovery_queue.py` combines the existing machine-readable portfolio limitation with retained fetch/source-page/document evidence. It assigns an actionability score and action class; **retained position count is never a ranking input**. A changed unclassified partial is intentionally ranked highest for review.

The normal status recorder now publishes:
- `docs/PORTFOLIO-RECOVERY-QUEUE.json` — structured operator data;
- `docs/PORTFOLIO-RECOVERY-QUEUE.md` — human-readable queue.

Production queue generated at **2026-09-25T04:49:12Z** contains **8** incomplete/missing funds:
- **1 actionable now** — search for a fuller first-party disclosure;
- **4 retry only after source/transport change**;
- **3 cannot improve without a more precise AMC disclosure**;
- **1 stale partial** — Bajaj Finserv;
- **1 missing portfolio** — Union.

Current order:

| Rank | Fund | State | Action | Limitation |
| ---: | --- | --- | --- | --- |
| 1 | Axis Small Cap Fund | current partial | `search_fuller_first_party_disclosure` | `undisclosed_constituents` |
| 2 | Union Small Cap Fund | missing | `retry_after_source_change` | `upstream_source_unavailable` |
| 3 | Bajaj Finserv Small Cap Fund | stale partial | `retry_after_source_change` | `named_subset_only` |
| 4 | Edelweiss Small Cap Fund | current partial | `retry_after_source_change` | `named_subset_only` |
| 5 | ICICI Prudential Small Cap Fund | current partial | `retry_after_source_change` | `undisclosed_constituents` |
| 6 | Bandhan Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |
| 7 | Sundaram Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |
| 8 | UTI Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |

Each queue row includes the exact retained source URL, portfolio reporting date, limitation payload, optional recovery/watch URL, latest exact fetch evidence, latest relevant source-page check, latest matching document evidence, latest evidence timestamp and a concise retry condition.

The queue deliberately prevents repeated blind probes:
- **Union**: retry only after its official portfolio transport becomes reachable or an exact attachment appears.
- **Bajaj**: remains visibly stale, but retry only when the Downloads transport works from production or a current exact attachment appears.
- **Edelweiss**: retry only after its statutory portfolio route/static transport changes or an exact attachment appears.
- **ICICI Prudential**: retry only after its monthly ZIP stops redirecting to the unresolved archive host or another working first-party route appears.
- **Bandhan, Sundaram and UTI**: do not estimate censored/non-numeric weights; wait for more precise AMC disclosure.

No paid service, external communication, UI change, source deletion or portfolio mutation was introduced. The source-retention audit remains read-only: the **700 link-only candidates and legacy cumulative ZIP remain untouched**.

### Next backend task

The queue selects **Axis Small Cap Fund** as the sole actionable-now portfolio recovery target.

Start from retained evidence before any new broad probing. The latest retained snapshot is a **10-position current partial dated 2026-09-16** from:

`https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct`

The queue's latest retained source evidence is **2026-09-24T22:12:17Z**. Earlier Axis audit already proved that the official August full factsheet is reachable but not constituent-complete: it publishes **Equity 92.37%**, named holdings down to 0.50%, the explicit aggregate **Other Domestic Equity (Less than 0.50% of the corpus) 15.20%**, and **Debt, Cash & other current assets 7.63%**.

**Next batch:** search Axis's own statutory/monthly portfolio disclosure surfaces for an exact workbook, ZIP, API payload or other first-party constituent-level source that identifies the holdings hidden by that aggregate. Reuse retained source/fetch evidence first, then perform only a bounded live discovery if needed. Do not split the 15.20% aggregate, infer unnamed constituents, weaken source validation, or mark the factsheet snapshot complete.

Axis is also the only fund without explicitly labelled TER/BER. Keep its current unqualified expense-ratio observation distinct during this portfolio investigation; do not promote it to TER or BER without a separately explicit first-party label.

## Latest completed batch: machine-readable portfolio limitation reasons

**Partial and missing portfolio limitations are now first-class backend data without changing any holdings, weights, dates or completeness flags.**

PR **#112** merged as commit `b3ff3e370e5b6fc478fa4fbedd303949b20c8359`. Isolated validation run **36094891651** passed compileall, all **304 tests**, restored the real production database and verified the exact current limitation classifications while preserving production portfolio counts.

Production workflow **#474**, run **36095002670**, then passed the same **304-test** regression gate, generated-site validation, cumulative-history publication, collection-status recording and GitHub Pages deployment. The build and deploy jobs both completed successfully.

### Backend contract

New module `tracker/portfolio_limitations.py` provides stable evidence classifications for retained partial snapshots and missing portfolios. The classifier is deliberately source-anchored: if a future source changes, an old limitation is **not** silently inherited; it falls back to `partial_reason_unclassified` until reviewed.

The API now exposes `portfolio_limitation` at fund level and `limitation` on portfolio snapshots, including prior snapshots returned by `/api/portfolios/{snapshot_id}`. `COVERAGE-AS-OF.json` exposes the same structured limitation both at fund level and inside the retained portfolio object, plus aggregate `portfolio_limitation_reasons` counts.

Current production limitation codes generated at **2026-09-25T04:35:03Z**:

| Code | Funds | Current examples |
| --- | ---: | --- |
| `undisclosed_constituents` | **2** | Axis, ICICI Prudential |
| `named_subset_only` | **2** | Bajaj Finserv, Edelweiss |
| `non_numeric_source_weight` | **3** | Bandhan, Sundaram, UTI |
| `upstream_source_unavailable` | **1** | Union |

The evidence payload also carries `kind`, `basis`, `source_marker`, `detail` and `scope`. Examples include:
- Axis: AMC aggregate **Other Domestic Equity (Less than 0.50% of the corpus)**;
- ICICI Prudential: **Equity less than 1% of corpus**;
- Edelweiss: **Top 10 Holdings / Top 10 stocks: 23.00%**;
- Bandhan: **Less Than 0.01% of NAV** marker;
- Sundaram: exact **less than 0.01%** workbook footnote;
- UTI: censored `*` weight plus short-term deposits without an exact NAV percentage;
- Union: first-party portfolio transport unavailable from the production collection network.

A changed/unrecognized partial source receives `partial_reason_unclassified` rather than a guessed old reason. Complete snapshots receive no limitation.

### Production invariants after this batch

Production coverage remains unchanged:
- funds **36**
- AUM **36/36**
- dated Direct fee **36/36**
- reported TER **35/36**
- BER **35/36**
- benchmark identity **36/36**
- portfolios **35/36**
- complete portfolios **28**
- current portfolios **34**
- current+complete **28**
- partial portfolios **7**
- latest NAV **2026-09-24**

The production status written at **2026-09-25T04:35:23Z** records **143 plans**, **281,442 NAV observations**, **123 retained portfolio snapshots**, **1,782 document versions**, **73,322,496 database bytes**, and no change to the source-retention policy. The release saved checkpoint `database-36095002670-1.zip` with the existing **95 reusable source packs**.

No censored source marker was converted into a numeric estimate. No portfolio was reclassified complete. No source file was deleted. The source-retention audit remains read-only; the **700 link-only candidates remain untouched** and the legacy cumulative ZIP has not been retired.

### Next backend task

**Build a read-only portfolio recovery queue from the new limitation codes and retained source evidence.** The goal is to stop repeatedly probing already-proven blockers while still surfacing genuinely actionable work.

The queue should:
- rank incomplete/missing portfolios by actionability rather than position count alone;
- distinguish **retry only after source/transport change** from **search for a fuller first-party disclosure** and **cannot improve without more precise AMC disclosure**;
- include the exact source URL, reporting date, limitation code, last relevant source-page check/fetch evidence and a concise retry condition;
- keep stale-but-partial Bajaj visible separately from current partials;
- avoid any new paid service, external communication, source deletion or UI work;
- remain read-only and must not automatically retry or mutate portfolio data.

Use this queue to choose the next source-recovery batch. Do not re-probe Union, ICICI, Edelweiss or Bajaj merely because they rank as incomplete unless the queue shows new first-party transport/source evidence.


## Latest completed batch: ICICI Prudential portfolio transport re-check

**ICICI Prudential Small Cap Fund remains a current partial portfolio because its exact first-party monthly portfolio ZIP transport is still broken upstream. No holdings were fabricated or promoted.**

Diagnostic run **36093923776** re-tested the exact August and July 2026 portfolio URLs from the same GitHub Actions network used by production.

Exact first-party entry URLs:

- August: `https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`
- July: `https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/July/Monthly-Portfolio-Disclosure-July-2026.zip`

Both still return **HTTP 307** to the exact first-party archive host:

`https://archive.icicipruamc.com/...`

The archive hostname is still unusable:

- the GitHub runner resolver returns **`gaierror(-5, 'No address associated with hostname')`**;
- Google DNS-over-HTTPS returns **no A Answer**;
- Google DNS-over-HTTPS returns **no CNAME Answer**;
- the authoritative response contains only the `icicipruamc.com` SOA;
- direct August and July archive requests both fail before HTTP because the hostname does not resolve.

This exactly reproduces the earlier blocker documented in runs **36024378270** and **36024773905**. The AMC's public metadata and redirect path remain internally consistent; the failure is the unresolved archive host, not a parser bug or missing filename.

Do **not** work around this by pinning an old IP, disabling TLS verification, using third-party cached ZIPs as financial evidence, or converting the factsheet's separately disclosed **"Equity less than 1% of corpus"** aggregate into invented constituents.

The tracker therefore retains **ICICI Prudential Small Cap Fund · 83 named positions · 2026-08-31 · partial · current**, sourced from the official complete factsheet. Production coverage remains unchanged:

- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

The remaining portfolio backlog is now mostly verified source/precision boundaries rather than missing parser work. **Make partial-portfolio limitation reasons first-class machine-readable backend data.**

The current API and `COVERAGE-AS-OF.json` expose `complete: false`, but do not explain why a retained portfolio is partial. Add a conservative structured limitation field for the latest retained portfolio without changing holdings or inventing weights. It should distinguish at minimum:

- **source aggregate / undisclosed constituents** — ICICI Prudential, Axis;
- **source publishes only top/named holdings** — Edelweiss, Bajaj where applicable;
- **censored/non-numeric source weight** — Bandhan, Sundaram, UTI;
- **upstream transport/source unavailable** — use for missing-portfolio cases such as Union, not as a substitute for a retained partial snapshot.

Prefer storing/deriving the limitation from exact parser/source evidence rather than a free-form UI label. Expose it through the fund/portfolio API and coverage JSON, add regression tests, and keep existing completeness semantics unchanged. Censored source markers such as `<0.01%`, dollar-sign footnotes, or `*` must never become estimated numeric weights.

The source-retention audit remains **read-only**: no deletion of the 700 link-only candidates or retirement of the legacy cumulative ZIP is authorized by this batch.

No production data, parser rules, UI, paid service, permissions, schedule cadence, source-retention policy or archive files changed in the ICICI transport re-check. The temporary diagnostic workflow was removed before this handoff update.

## Latest completed batch: Edelweiss portfolio source audit

**Edelweiss Small Cap Fund remains a verified current partial portfolio. No holding or weight was fabricated or promoted in this batch.**

The exact production September factsheet was recovered from the tracker's cumulative archive rather than re-downloaded from the AMC because current GitHub Actions requests to Edelweiss's factsheet/statutory routes return **HTTP 403 Forbidden**. Retained evidence:

- source: `https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf`
- SHA-256: `ecda95db8183525b4b429c835d10d883b4db0757dabff2b562002d5a16cec366`
- bytes: **16,733,406**
- portfolio reporting date: **2026-08-31**

The exact Small Cap page publishes only **Top 10 Holdings**, not a complete constituent table. The retained rows are City Union Bank 3.17%, Karur Vysya Bank 2.64%, Multi Commodity Exchange of India 2.64%, PNB Housing Finance 2.34%, Avalon Technologies 2.27%, Gabriel India 2.18%, KEI Industries 2.06%, Ajanta Pharma 1.94%, Fortis Healthcare 1.92% and Radico Khaitan 1.84%. They reconcile to the factsheet's explicit **Top 10 stocks: 23.00%** total.

The same page contains an **Additional Information pertaining to Portfolio of the scheme** section. PDF annotation inspection in successful diagnostic run **36089827060** proved that all five portfolio-related "Click Here" links resolve to the exact first-party route:

`https://www.edelweissmf.com/statutory/portfolio-of-schemes`

The tracker history contains prior successful fetches of that exact page. The newest retained HTML is:

- fetched: **2026-09-24T04:43:04Z**
- SHA-256: `c2978d8fc61804b4afad5e3c65d98131ed2d6f74c31c45980212518deea5ab6a`
- bytes: **795,717**

Runs **36089882783**, **36089930620** and **36090041993** inspected the retained page and database history. The archived page is an Angular application shell; it contains no exact monthly workbook attachment, no child portfolio document already retained by the tracker, and no directly usable Small Cap holding payload. Its client bundle is referenced as `main.0411e4933dfdb2cb.js`, but the current production runner receives **HTTP 403** when requesting that bundle as well. Current direct requests to the statutory page and September PDF likewise return 403.

This establishes a transport/discovery boundary rather than a parser-completeness bug. The existing conservative Top-30 parser is not applicable to the current September factsheet because that PDF genuinely publishes a Top-10 table. Do not expand the 10 named holdings by inference, reuse an older month's Top-30 list as current, guess workbook filenames, or mark the snapshot complete.

Published coverage therefore remains unchanged:
- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

Do **not** repeat Edelweiss source probing unless its first-party statutory route or static bundle becomes reachable again, or an exact monthly attachment URL becomes available.

**ICICI Prudential Small Cap Fund is the next preferred portfolio source-recovery target for a bounded transport re-check.** Earlier work already identified exact first-party August/July monthly portfolio ZIP metadata, but the files redirected to `archive.icicipruamc.com`, whose authoritative public DNS did not resolve at the time. First verify whether that exact official transport has materially changed. If the host still has no usable public transport, record the unchanged blocker and do not guess alternate filenames or use third-party copies.

Bandhan, Sundaram and UTI remain disclosure-precision blockers because their source files contain censored or non-numeric tiny positions; Axis remains an aggregate-disclosure blocker; Union and Bajaj remain the transport/source-discovery blockers documented in the previous batch. Axis also remains the only fund without explicitly labelled TER and BER.

No UI, paid-service, permission, archive-retention policy, schedule cadence or production data changed in this audit. Temporary diagnostic workflows were removed before merge.

## Latest completed batch: Union + Bajaj portfolio source re-audit

**No portfolio values were invented or promoted in this batch. The two highest-priority portfolio gaps were re-checked from the same GitHub Actions network used by production, and both remain transport/source-discovery blockers.**

Diagnostic run **36088945502** retried Union's exact official portfolio routes from a GitHub-hosted runner:
- `https://www.unionmf.com/about-us/downloads`
- `https://www.unionmf.com/about-us/downloads/monthly-portfolio`

Both still fail before page/script discovery with **`URLError: [Errno 111] Connection refused`**. This reproduces the prior production-network boundary. A separate public web crawl can currently read Union's Downloads page and confirms that Union advertises Monthly Portfolios there, but that does not provide the production updater with a fetchable first-party attachment. No guessed filename, alternate IP, TLS bypass, third-party copy or inferred holding was used. **Union Small Cap Fund therefore remains the sole fund with no retained portfolio.**

The handoff-directed fallback, **Bajaj Finserv Small Cap Fund**, was then re-checked. Bajaj's official public Downloads page at `https://www.bajajamc.com/downloads` visibly contains a dedicated **Monthly Portfolio** section with year/month selectors, and Bajaj scheme documents state that portfolio disclosure is provided as a downloadable spreadsheet. However, combined diagnostic run **36089063486** received **HTTP 403 Forbidden** when the GitHub runner requested that Downloads page, before its client-side scripts/API could be traced. A bounded public-source search found the existing lagged Small Cap factsheet but did not expose a concrete current August 2026 monthly Small Cap spreadsheet URL. The tracker therefore retains Bajaj's existing **13-position partial dated 2026-07-31**; it was not relabelled as August merely because the factsheet filename says August 2026.

Current published coverage remains unchanged from production #473:
- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

Do **not** repeat Union or Bajaj source probing unless their first-party transport materially changes or an exact current attachment URL becomes available. **Edelweiss Small Cap Fund is the next preferred portfolio-recovery target** because it is a current partial and is more likely to yield incremental source recovery than the already-proven Axis, Sundaram, UTI, Union and Bajaj boundaries. Re-read the prior Edelweiss v89-v103 source tracing before any new attempt; promote only exact first-party named holdings and preserve partial status if the source itself is incomplete.

Axis remains the only fund without explicitly labelled TER and BER. Its current official Direct `expense_ratio` must remain unqualified unless a first-party source explicitly labels TER or BER.

No UI, paid-service, permissions, archive-retention policy, schedule cadence or production data was changed in this audit. Temporary diagnostic workflows were removed before merge.

## Latest completed batch: UTI Small Cap explicit BER recovery

**UTI Small Cap Fund now has explicitly labelled Direct and Regular BER from UTI Mutual Fund's own public YTD TER workbook. The tracker did not use or bypass UTI's authenticated scheduler API.**

PR #103 merged as commit `2e02b0e1fa11df72c4ced20675d8e47b385e4383`. Isolated validation run **36087658254** passed compileall, all **259 tests**, and a live first-party UTI CMS metadata → YTD TER workbook → strict Small Cap parser check. Production workflow **#473**, run **36087719595**, then passed the one-time UTI recovery, the same **259-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T02:49:01Z**.

### UTI source discovery and exact observations

UTI's current production web application publishes the public CMS metadata endpoint:

`https://www.utimf.com/api/page/get-ytd-ter-disc-page-data`

At recovery time that endpoint exposed the current-financial-year file:

- CMS title: **Daily TER YTD 01042026-12072026**
- source workbook: `https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/daily_ter_ytd_01042026_12072026_imp.xlsx?VersionId=IkGh3zzgPAsjAuVAMH.mIny_xn3zhpxb`
- workbook SHA-256: `f1ec288c456330387706a4ad32e59f381c320e200eb145c0d9978212179f9094`
- CMS YTD end date: **2026-07-12**

UTI's production JavaScript also exposes a scheduler route named `getTerData` under `https://prod-api-investor.utimf.com/api/v1/scheduler/getTerData`. Direct unauthenticated requests returned **401 Unauthorized**. The tracker does **not** attempt to obtain or bypass credentials for that route; the public CMS workbook is the auditable source used here.

The workbook's **YTD TER** sheet has these exact published columns:

`PORTFOLIO, NSDL_CODE, PORTFOLIO_NAME, TRANS_DATE, BER_REG, BRK_REG, TRAN_REG, STAT_REG, TOTALTER_REG, WTD_TER_REG, BER_DIR, BRK_DIR, TRAN_DIR, STAT_DIR, TOTALTER_DIR, WTD_TER_DIR`

The parser requires exact UTI Small Cap identity:

- portfolio code: **751**
- NSDL scheme code: **UTIM/O/E/SCF/20/03/0094**
- scheme name: **UTI Small Cap Fund**

Newest exact row in the public YTD file: **2026-07-12**

| Plan | BER | Brokerage | Transaction cost | Statutory levies | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.59%** | 0.00% | 0.00% | 0.20% | **1.79%** |
| Direct | **0.56%** | 0.00% | 0.00% | 0.10% | **0.66%** |

The workbook also publishes WTD TER columns. Those are validated as part of the source schema but are not promoted into the daily Total TER metric. The tracker stores only the explicitly published BER, brokerage, transaction cost, statutory levies and Total TER fields.

The parser rejects changed headers, wrong portfolio/NSDL/scheme identity, future rows, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that fail reconciliation within rounding tolerance. The CMS selector requires the title dates and workbook filename dates to agree, requires the current financial year to start on 1 April, rejects future end dates and accepts only UTI's registered public CloudFront path.

`scripts/refresh_uti_expenses.py` performs the idempotent push recovery and records `source_upgrade_uti-ber-v1` only after a current-financial-year Regular/Direct BER+TER pair exists on one exact date from one UTI YTD workbook with one non-empty source hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #473 logged:

`UTI Small Cap Fund: official BER/TER as of 2026-07-12 (Direct 0.56%/0.66% BER/TER; YTD file through 2026-07-12)`

with the exact source and hash above.

### Date precedence and retained UTI TER

The new YTD workbook establishes BER, but it is **not** UTI's newest retained Total TER observation. The tracker already has UTI's official Fund Watch observation:

- Direct Total TER: **0.86%**
- reporting date: **2026-07-31**
- source: `https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-08/uti_fund_watch_active_august_2026_rv2.pdf?VersionId=B2XKeBTyWsZMGfHUqI3nbdnzhATN16Ax`

Because reporting date remains the primary ordering rule, the website continues to show **Direct TER 0.86% as of 2026-07-31** while separately exposing **Direct BER 0.56% as of 2026-07-12**. No value was derived or forward-filled.

Status commit `7eae627ec707c681b43f71902ac034eeeec2e561` records the published state. Final Pages artifact **10844880313** is **230,729,840 bytes**, digest `sha256:78b2a09036b06ae4273478e89a03b66a9c6595f4b3b2348229bf0a8cb95223fe`.

### Expense and portfolio coverage after UTI

Coverage generated at **2026-09-25T02:48:03Z** is:

- reported TER: **35 / 36**
- base expense ratio / BER: **35 / 36** (up from 34 / 36)
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

UTI's current AUM is **₹5,404.066 crore as of 2026-09-23** via AMFI. Its August portfolio remains current but partial at **108 retained positions as of 2026-08-31**.

**Axis Small Cap Fund is now the only fund without both explicitly labelled TER and BER.** Its official fund page still publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that value classified as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party disclosure.

### Next backend task

The expense-source pass is now complete for every fund except the deliberate Axis classification boundary. **Return to portfolio recovery, with Union Small Cap Fund as the next preferred target because it is the sole fund with no retained portfolio at all.**

Before retrying Union, re-read the prior Union source/transport investigations in this handoff and current source-page evidence. Union has previously been an official-host transport blocker. Retry only if its current first-party disclosure route, robots policy, attachment path or transport has materially changed; do not guess filenames, weaken host checks or invent holdings simply to close the gap. If Union remains unchanged/unreachable after a bounded evidence-based check, move to **Bajaj Finserv Small Cap Fund**, which remains the only stale collected portfolio.

Other current portfolio boundaries remain:
- **Bajaj Finserv Small Cap Fund**: stale collected portfolio.
- **Axis, Edelweiss, ICICI Prudential, Sundaram and UTI**: current partials with existing source/access/data-precision constraints.
- **Sundaram**: one holding is disclosed only as less than 0.01%; do not fabricate an exact weight.
- **UTI**: current source abbreviates/censors small positions; do not infer exact weights.
- completed structured recoveries such as SBI, Tata, TRUSTMF, Invesco and JM should not be rerun without new source evidence.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this UTI batch.

## Latest completed batch: Groww Small Cap current BER recovery

**Groww Small Cap Fund now has current, explicitly labelled Direct and Regular BER from Groww Mutual Fund's own signed BER notice. Future/conditional revised BER values were deliberately not promoted.**

PR #101 merged as commit `aa0e04e33154f2d1628d0f22d07090b60298fe04`. Isolated validation run **36086300920** passed compileall, all **254 tests**, and a live first-party expense-page → BER notice → strict Smallcap row parse. Production workflow **#471**, run **36086366140**, passed the one-time Groww recovery, the same **254-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. Production #471 completed successfully at **2026-09-25T02:29:25Z**.

A small correctness follow-up was then completed in PR #102, merged as commit `3b045693161208b31628d27b677d88bc8616efb4`. Family-level fee-like coverage summaries now prefer **Direct** when Regular and Direct observations share the same reporting date, while reporting date remains the primary ordering rule. Isolated validation run **36086652916** passed **255 tests**. Production workflow **#472**, run **36086706291**, passed the full **255-test** regression gate, site/download validation, cumulative-history publication and Pages deployment, completing successfully at **2026-09-25T02:34:31Z**.

### Groww source discovery and exact observations

Current first-party expense-ratio page:

`https://www.growwmf.in/downloads/expense-ratio`

The current 2026–27 page publishes signed BER notices on Groww's registered asset host. The newest notice containing **Groww Smallcap Fund** at recovery time is:

`https://assets-netstorage.growwmf.in/compliance_docs/Downloads/Expense%20Ratio/Notice%20-%20Change%20in%20TER/2026%20-%202027/26.%20Notice%20-%20Change%20in%20BER.pdf`

Exact PDF SHA-256:

`ab1e3bbff3e527d8d43124578738d36929088b3c5758e433ef760b38a4efffa1`

Notice identity: **26/2026–2027**. It was signed **2026-09-24** and explicitly labels the current values as **Current BER**, with footnote **As on September 23, 2026**.

| Plan | Current BER as of 2026-09-23 | Revised BER shown in notice | Effective date |
| --- | ---: | ---: | --- |
| Direct | **0.42%** | 0.49% | 2026-09-30 |
| Regular | **1.94%** | 1.94% (No change) | 2026-09-30 |

The revised BER column is **not** stored as a current exact observation. The notice says the revised BER may be lower depending on the applicable AUM slab/regulatory requirements on the effective date, and its effective date was still in the future when collected. The tracker therefore retains only the exact **Current BER** observations dated 2026-09-23.

The preceding Notice 24 independently exposed **Direct Current BER 0.45% as of 2026-08-31** with Regular shown as **NA** and a conditional revised Direct BER of 0.51% effective 2026-09-05. The collector treats NA as missing and never infers a Regular value.

The parser/discovery path requires:
- current-financial-year **Notice - Change in BER.pdf** identity;
- exact registered Groww asset host and expense-ratio path;
- exact BER notice heading and Current BER/Revised BER table headings;
- exact scheme text **Groww Smallcap Fund**;
- valid as-of, signed and effective dates with non-future observation/publication dates;
- numeric Current BER within the accepted range;
- one exact Smallcap row in the notice.

`scripts/refresh_groww_expenses.py` performs the idempotent push recovery and records `source_upgrade_groww-ber-v1` only after recent Regular/Direct BER observations exist on one date from one exact Groww notice with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #471 logged:

`Groww Small Cap Fund: official Current BER as of 2026-09-23 (Direct 0.42%, Regular 1.94%); notice 2026-09-24, revised BER effective 2026-09-30 not promoted`

with the exact source and hash above.

### Coverage-summary correction

Before PR #102, the generic `base_expense_ratio` field in `COVERAGE-AS-OF.json` could surface Groww's Regular 1.94% row because Regular and Direct were tied on the same reporting date. The database observations were both correct; only the family-level representative row was nondeterministic.

`tracker/coverage.py` now orders fee-like summary metrics by:
1. newest reporting date;
2. Direct before Regular when the reporting date is equal;
3. observation timestamp after the date/plan tie.

A regression test also confirms that a genuinely newer Regular observation still outranks an older Direct one. Final published Groww BER is therefore **Direct 0.42% as of 2026-09-23**, while the Regular 1.94% observation remains retained in history.

Final Pages artifact from production #472 is **10844591043**, **230,727,776 bytes**, digest `sha256:3786e28ed05b5b41b8dd987ba4ee41ca2660f81ec6a5b9c681dcc2197133a6dc`. Final status commit `e0f880294a8245188198fd247b10f5b3cc3dec70` records the corrected published state.

### Expense and portfolio coverage after Groww

Coverage generated at **2026-09-25T02:33:30Z** is:

- reported TER: **35 / 36**
- base expense ratio / BER: **34 / 36** (up from 33 / 36)
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

Groww now has **Direct BER 0.42% as of 2026-09-23** and **Regular BER 1.94% as of 2026-09-23**. Its retained explicitly reported Direct Total TER remains **1.12% as of 2026-04-30** from the official April factsheet; the BER notice does not publish a current Total TER, so no TER was derived from BER. Current AUM remains **₹948.2145 crore as of 2026-09-23** via AMFI, and the August portfolio remains complete at **62 positions as of 2026-08-31**.

The sole fund without explicitly reported Total TER remains **Axis Small Cap Fund**. The remaining BER gaps are now only **Axis Small Cap Fund** and **UTI Small Cap Fund**. **Union Small Cap Fund** remains the sole zero-portfolio fund, and **Bajaj Finserv Small Cap Fund** remains the only stale collected portfolio.

### Next backend task

**UTI Small Cap Fund is the next preferred expense-source target.** The tracker currently retains Direct Total TER **0.86% as of 2026-07-31** from UTI's official Fund Watch but still has no explicitly labelled BER. Trace UTI's current first-party statutory TER/expense disclosure route for a dated, explicitly labelled BER. Prefer current structured disclosure/API/workbook evidence when available; preserve exact source URL/document identity/date/hash and do not derive BER from Total TER or components.

**Axis remains a deliberate classification boundary:** its official fund page currently publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that observation as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party source.

Portfolio recovery remains secondary to the current expense-coverage pass: **Union Small Cap Fund** is the only fund with no retained portfolio; Bajaj Finserv remains stale; existing partial-source precision rules must not be weakened merely to close coverage.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Groww batch.

## Latest completed batch: Mirae Asset Small Cap explicit Total TER/BER recovery

**Mirae Asset Small Cap Fund now has current, explicitly labelled BER and Total TER from Mirae Asset Mutual Fund's own daily statutory-disclosure workbook.**

PR #100 merged as commit `9f8431ac94f6e5ecbad323f55632e2bb45e905cf`. Isolated validation run **36084851382** passed compileall, all **249 tests**, and a live first-party statutory service → current TER workbook → strict Small Cap parser check. Production workflow **#470**, run **36084922795**, then passed the one-time Mirae recovery, the same **249-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T02:08:49Z**.

### Mirae source discovery and exact observations

Current first-party statutory TER page:

`https://www.miraeassetmf.co.in/downloads/statutory-disclosure/total-expense-ratio`

Mirae's production browser loads the disclosure list from the public same-origin service:

`https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData`

using the exact module name **TotalExpenseRatio** plus bounded from/to dates and pagination. No investor login, account credential, token or private secret is used.

For **2026-09-23**, the service returned the exact record:

- title: **Total Expense Ratio -23 Sep 2026**
- workbook: `https://www.miraeassetmf.co.in/DailyUploads/TotalExpenseRatio/IN_MF_EXPENSE_RATIO_SEBI_V3_23092026.xls`
- publish date: **2026-09-23**
- workbook SHA-256: `ad2faa3e9140f121268b2385d2b81d7b5e3d2b0af5b2c87b6c3e13bba9541722`

The legacy XLS has one **Report** sheet and explicit columns for BER, brokerage, transaction cost, statutory levies including GST and **Total TER** for both Regular and Direct plans. The parser requires exact scheme name **Mirae Asset Small Cap Fund**, exact NSDL code **MIRA/O/E/SCF/24/10/0075**, exact two-row header identity and the newest unique non-future row.

Newest exact row: **2026-09-23**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.57%** | 0.07% | 0.01% | 0.47% | **2.12%** |
| Direct | **0.32%** | 0.07% | 0.01% | 0.24% | **0.64%** |

The tracker stores the workbook's explicit **Total TER** fields. It does **not** derive Total TER from BER or components. Component arithmetic is only a rejection check. Metadata title date, workbook filename date and published date must all agree. The parser also rejects changed workbook layout, wrong scheme/NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that fail reconciliation within rounding tolerance.

`scripts/refresh_mirae_expenses.py` performs the idempotent push recovery and records `source_upgrade_mirae-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Mirae daily TER workbook with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #470 logged:

`Mirae Asset Small Cap Fund: official BER/TER as of 2026-09-23 (Direct 0.32%/0.64% BER/TER)`

with the exact source and workbook hash above. Status commit `eadc871b7d90f9f2b5584fd174b471c580835769` records the published coverage state.

### Expense and portfolio coverage after Mirae

Coverage generated at **2026-09-25T02:07:40Z** is:

- reported TER: **35 / 36** (up from 34 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

Mirae's published Direct fee is now **TER 0.64% with BER 0.32%, both as of 2026-09-23**, replacing the older **0.34% BER as of 2026-07-31** fallback. Its current AUM is **₹5,965.3286 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **86 positions as of 2026-08-31**.

The sole fund without explicitly reported Total TER is now **Axis Small Cap Fund**. The remaining BER gaps are **Axis, Groww and UTI**. The sole zero-portfolio fund is **Union Small Cap Fund**; **Bajaj Finserv Small Cap Fund** remains the only stale collected portfolio.

### Next backend task

**Groww Small Cap Fund is the next preferred expense-source target.** The tracker has a dated Direct TER **1.12% as of 2026-04-30** from Groww Mutual Fund's official factsheet but still has no explicit BER. Trace Groww's current first-party statutory TER/expense disclosure route for a current explicitly labelled BER and, if available, a fresher Total TER. Preserve exact source identity/date/hash and do not derive BER or TER from components.

After Groww, investigate **UTI Small Cap Fund** for an explicitly labelled BER. **Axis remains a deliberate classification boundary:** its official fund page currently publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that observation as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party source.

Portfolio recovery remains secondary to the current expense-coverage pass: **Union Small Cap Fund** is still the only fund with no retained portfolio; Bajaj Finserv remains stale; existing partial-source precision rules must not be weakened merely to close coverage.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Mirae expense-recovery batch.

## Latest completed batch: Mahindra Manulife Small Cap current TER/BER recovery

**Mahindra Manulife Small Cap Fund now has current, explicitly labelled BER and Total TER from Mahindra Manulife Mutual Fund's own mandatory-disclosure workbook.**

PR #99 merged as commit `29b755558280871e7237a01a25d6968628b7f897`. Isolated validation run **36080863767** passed compileall, all **245 tests**, and a live downloads-metadata → current TER workbook → strict Small Cap parser check. Production workflow **#469**, run **36080964116**, then passed the one-time Mahindra recovery, the same **245-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T01:13:37Z**.

### Mahindra source discovery and exact observations

Mahindra's current public Downloads page is:

`https://www.mahindramanulife.com/downloads`

Its production browser loads the public downloads tree from:

`https://investorapi.mahindramanulife.com/api/v1/web/preLogin/downloads`

The response is wrapped using AES-CBC constants published in Mahindra's production browser bundle. The tracker mirrors only that public browser transport; **no investor login, account credential, token or private secret is used**. The decoded AMC metadata is walked through the exact category path:

`MANDATORY DISCLOSURES > Total Expense Ratio of Mutual Fund Schemes > Total Expense Ratio`

The tracker then selects the exact current-financial-year workbook from AMC metadata rather than guessing or hardcoding a rotating filename. For 2026–27 the production source is:

`https://www.mahindramanulife.com/uploads/download/6d61db84-f11d-4987-b7a6-929a71d43967.xlsx`

Mahindra also publishes a **FROM APRIL 01 2026** last-six-months entry; at validation time it resolved to the same **234,648-byte** workbook with the same SHA-256, so the annual **TOTAL EXPENSE RATIO - 2026-27** metadata entry is retained as the canonical source.

Exact workbook SHA-256:

`2945005fb6e4cef4922fad976ee57a0dc53b602f1f97ced855eaa29f4b0b00d3`

The parser requires exact NSDL scheme code **MAHM/O/E/SCF/22/07/0020**, exact scheme name **Mahindra Manulife Small Cap Fund**, the exact two-row Regular/Direct TER header, and the newest unique non-future row.

Newest exact row: **2026-09-24**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.59%** | 0.12% | 0.01% | 0.48% | **2.20%** |
| Direct | **0.47%** | 0.12% | 0.01% | 0.32% | **0.92%** |

The tracker stores the workbook's explicit **Total TER** fields. It does **not** calculate Total TER from BER or components. Component arithmetic is only a rejection check. The parser rejects changed sheet/header layout, wrong scheme/NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER and component totals that fail reconciliation within rounding tolerance.

`scripts/refresh_mahindra_expenses.py` performed the idempotent push recovery and records `source_upgrade_mahindra-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Mahindra workbook with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #469 logged:

`Mahindra Manulife Small Cap Fund: official BER/TER as of 2026-09-24 (Direct 0.47%/0.92% BER/TER)`

with the exact source and workbook hash above.

Status commit `8bd8bc0ad5d397a50e9302b8570aa4154695613c` records the published state. Pages artifact **10841938013** is **230,727,478 bytes** with digest `sha256:21f68bebf1b08555d08681a4265aa5d4b95145b778ae48b570bc58ff16e54a3a`.

### Expense coverage after Mahindra

Coverage generated at **2026-09-25T01:12:32Z** is:

- reported TER: **34 / 36** (up from 33 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

Mahindra's published Direct fee is now **TER 0.92% with BER 0.47%, both as of 2026-09-24**, replacing the older August BER-only fallback. Its current AUM is **₹5,528.25 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **82 positions as of 2026-08-31**.

The two remaining funds without reported TER are **Axis Small Cap Fund** and **Mirae Asset Small Cap Fund**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**Mirae Asset Small Cap Fund is the next preferred TER target.** The tracker currently retains Direct BER **0.34% as of 2026-07-31** from the official August factsheet and a complete August portfolio from:

`https://www.miraeassetmf.co.in/docs/default-source/portfolios/mascf_aug2026.xlsx`

Trace Mirae Asset's current first-party statutory/expense disclosure route for an explicitly labelled Total TER and exact reporting date. Prefer a current AMC disclosure table/workbook/API over the older factsheet BER observation. Store Total TER only if Mirae publishes it directly; do not derive it from BER, GST, brokerage or transaction-cost components. Preserve exact source identity/date/hash.

**Axis remains special:** its current official fund page publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**, while explicit TER and BER are still absent. Keep that value as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Mahindra expense-recovery batch.

## Latest completed batch: JM Small Cap current TER/BER recovery

**JM Small Cap Fund now has current, explicitly labelled BER and Total TER from JM Financial Mutual Fund's own Scheme Expense Ratio API.**

PR #98 merged as commit `65983a16fe8c34f0502e6cd2a3a1523158771727`. Isolated validation run **36077070883** passed compileall, all **239 tests**, and a live first-party JM TER API check. Production workflow **#468**, run **36077163847**, then passed the one-time JM recovery, the same **239-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T00:23:21Z**.

### JM source and exact observations

Current first-party Scheme Expense Ratio page:

`https://www.jmfinancialmf.com/Scheme-Expense-Ratio`

JM's live browser posts public JSON requests to the same first-party API host already used by the tracker for JM monthly portfolio discovery. The current TER table uses:

`https://jmmfapi.jmfinancialmf.com/api/GetTerPageLatest`

with the browser's unfiltered latest-table request:

`{"IICategory":0,"IVFundCode":""}`

The API wraps its response payload using the AES-CBC key/IV published in JM's production browser bundle. The tracker reuses the already-validated read-only JM browser transport; **no investor login, account credential, token or private secret is used**. For TER evidence, the tracker archives the decoded first-party financial JSON that the browser renders rather than treating the encrypted transport envelope as the source artifact.

The collector accepts only the exact identity:

- scheme name: **JM Small Cap Fund**
- scheme code: **SC**
- NSDL scheme code: **JMFI/O/E/SCF/23/11/0016**

Newest exact row: **2026-09-24**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.94%** | 0.09% | 0.01% | 0.50% | **2.54%** |
| Direct | **0.59%** | 0.09% | 0.01% | 0.28% | **0.97%** |

The tracker stores JM's explicit **Total TER** fields. It does **not** calculate Total TER from BER or components. Component arithmetic is only a rejection check. The parser rejects a changed response shape, wrong scheme/code/NSDL identity, future dates, duplicate latest rows, missing or out-of-range values, Total TER below BER, and component totals that do not reconcile within rounding tolerance.

Decoded production evidence SHA-256:

`3b4e875ae00865fb9e36ecf7feb1d0e6f194198a8d9e7b7bf59b8692bfeb7dbd`

`scripts/refresh_jm_expenses.py` performed the idempotent push recovery and records `source_upgrade_jm-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from the exact JM TER endpoint with one non-empty source hash. Normal nightly collection remains active through `amc_expenses.update`; a source failure preserves prior observations.

Production #468 logged:

`Jm Small Cap Fund: official BER/TER as of 2026-09-24 (Direct 0.59%/0.97% BER/TER)`

with source `https://jmmfapi.jmfinancialmf.com/api/GetTerPageLatest` and the exact decoded-evidence hash above.

Status commit `5378c91c43cf152943024dd5a7a9bcb9387501c3` records the published state. Pages artifact **10840805225** is **230,728,268 bytes** with digest `sha256:e9c7ee8d331b2d36408ff7a2f9fd075e4e39da9689fb0bf1e9d71ef37ab9694f`.

### Expense coverage after JM

Coverage generated at **2026-09-25T00:22:01Z** is:

- reported TER: **33 / 36** (up from 32 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

JM's published Direct fee is now **TER 0.97% with BER 0.59%, both as of 2026-09-24**, replacing the older August BER-only fallback. Its current AUM is **₹955.1431 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **85 positions as of 2026-08-31**.

The three remaining funds without reported TER are **Axis, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**Mahindra Manulife Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.47% as of 2026-08-31** from the official August digital factsheet:

`https://www.mahindramanulife.com/digital-factsheet/august-2026/Equity-funds/Small-Cap-Fund.html`

Trace Mahindra Manulife's current first-party statutory/expense disclosure route for an explicitly labelled Total TER and exact reporting date. Store Total TER only if the AMC publishes it directly; do not derive it from BER, GST, brokerage or transaction-cost components. Preserve exact source URL/document/API identity and source hash.

After Mahindra Manulife, continue **Mirae Asset Small Cap Fund**. **Axis** remains special: its current official fund page publishes an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**, while BER is still absent. Keep that value as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this JM expense-recovery batch.

## Latest completed batch: Invesco India Small Cap current TER/BER recovery

**Invesco India Small Cap Fund now has current, explicitly labelled BER and Total TER from Invesco Mutual Fund's own statutory-disclosure API.**

PR #97 merged as commit `6c3fd457f2f15623d8d5066fad0398f950a22c38`. Isolated validation run **36073035236** passed compileall, all **235 tests**, and a live read of the exact current Invesco TER endpoint. Production workflow **#467**, run **36073145561**, then passed the one-time Invesco recovery, the same **235-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The run completed successfully at **2026-09-24T23:32:42Z**.

### Invesco source and exact observations

Current first-party TER page:
`https://www.invescomutualfund.com/statutory-disclosures/ter-mutual-fund-since-2026/ter`

The production browser component uses the public plan list at:
`https://www.invescomutualfund.com/api/Common/GetAllPlans`

and loads TER rows from:
`https://www.invescomutualfund.com/api/TotalExpenseRatioOfMutualFundSchemePolicy/GetTERExpenseData?title=<scheme>&fincialYear=<start-year>&month=<month-number>`

The collector requires the exact scheme name **Invesco India Small Cap Fund** and exact NSDL scheme code **INVM/O/E/SCF/18/07/0030**. It checks the current month first and the immediately preceding month as a bounded fallback, including the April/March financial-year boundary.

Production source for the latest retained observation:
`https://www.invescomutualfund.com/api/TotalExpenseRatioOfMutualFundSchemePolicy/GetTERExpenseData?title=Invesco+India+Small+Cap+Fund&fincialYear=2026&month=9`

The source response retained in production has SHA-256:
`4f2681e5a50ed4b7609537a226d56cab713dbcfc9763012179b70d4493bb0de7`

Newest exact row: **2026-09-23**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.44%** | 0.05% | 0.00% | 0.34% | **1.83%** |
| Direct | **0.41%** | 0.05% | 0.00% | 0.17% | **0.63%** |

The tracker stores the API's explicit **Total TER** value. It does **not** calculate TER from BER or components. Component reconciliation is only a rejection check. The parser rejects a changed response shape, wrong scheme or NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that do not reconcile within rounding tolerance.

`scripts/refresh_invesco_expenses.py` performs the idempotent push recovery and records `source_upgrade_invesco-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Invesco TER API source with one non-empty source hash. Normal nightly collection remains active in `amc_expenses.update`.

Production #467 logged:
`Invesco India Small Cap Fund: official BER/TER as of 2026-09-23 (Direct 0.41%/0.63% BER/TER)`

Status commit `e559c7b4c8bd27fdd74b1cb708fea502bca6b77e` records the published coverage state. Pages artifact **10838957887** is **230,728,637 bytes** with digest `sha256:2afd9b34e0e4a53f1ad2f60d645205644b2d58136ce3b78ab480b72680de3176`.

### ICICI Prudential state catch-up

The prior handoff still named ICICI Prudential as the next target, but that recovery completed before the Invesco batch began. PR #96 merged as commit `46eb738ee80f98c6d15517a48e7a618de70a21bc`; production workflow **#466**, run **36070920935**, completed successfully at **2026-09-24T23:06:35Z** and passed **230 tests**.

ICICI's production source is the exact TER workbook discovered through its first-party Financials & Disclosures API:
`https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx`

Retained workbook SHA-256:
`d40c69429f907bd1f967a908884ab3feb330ecb7395d402f7a50c64976cd5488`

Latest ICICI Prudential Small Cap observation is **2026-09-23**: Regular **BER 1.50% / Total TER 2.10%** and Direct **BER 0.70% / Total TER 1.18%**. The retained workbook is **238,073 bytes**. The collector discovers the workbook from ICICI's exact current TER category/subcategory metadata, parses the source OOXML rows conservatively, and stores only explicit published BER/Total TER values. Production #466 Pages artifact **10838356588** is **230,726,093 bytes** with digest `sha256:039a593f3bb605eeccfb53eabe0adbb41347cf0ef5045a678b2125aeb663008b`.

### Expense coverage after ICICI + Invesco

Coverage generated at **2026-09-24T23:31:41Z** is:

- reported TER: **32 / 36** (up from 30 / 36 at the last handoff)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

Invesco's published Direct fee is now **TER 0.63% as of 2026-09-23**, replacing the older BER fallback. Its current AUM observation is **₹16,523.94 crore as of 2026-09-23** from AMFI.

The four remaining funds without reported TER are **Axis, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**JM Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.59% as of 2026-08-31** from JM Financial Mutual Fund's official September 2026 factsheet, and the project already has a validated read-only JM public-API transport for monthly portfolio disclosures. Trace JM's first-party expense/TER disclosure route for an explicitly labelled Total TER and exact reporting date. Reuse public browser/API mechanics only when the AMC itself exposes them; do not derive Total TER from BER, GST, brokerage or transaction-cost components.

After JM, continue with **Mahindra Manulife** and **Mirae Asset**. **Axis** remains special: its current fund page exposes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in the ICICI/Invesco expense-recovery batches.

## Latest completed batch: HSBC Small Cap detailed TER/BER recovery
**HSBC Small Cap Fund now has current, explicitly labelled AMC-published BER and Total TER from the detailed TER workbook linked by HSBC's own factsheet.**

PR #95 merged as commit `1077f6887d07b1e81de1dbf9ab1c03e88dd66096`. Isolated validation run **36064819731** passed compileall, all **224 tests**, and a live end-to-end AMC-link -> CAMS browser transport -> decoded workbook -> strict HSBC row parse. Production workflow **#465**, run **36064999961**, then passed the one-time HSBC recovery, the same **224-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-24T22:16:34Z**.

### Source chain and retained evidence

HSBC's exact retained August factsheet is:

`https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf`

Its HSBC Small Cap page publishes **Base Expense Ratio (BER)** only — Regular **1.42%**, Direct **0.56%**, as of **2026-08-31** — and explicitly directs readers to the detailed TER workbook:

`https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx`

That public CAMS route is an Angular download application rather than raw XLSX bytes. Its browser performs a public `GET_UPD_MB_RESULT` request to `https://digital.camsonline.com/api/v1/camsonline` and receives the workbook as base64 inside its encrypted transport envelope. `tracker/amc_expenses.py` mirrors only that public browser transport using constants embedded in the public application bundle; **no investor login, account credential, token, or private secret is used**. The decoded XLSX itself is archived and hashed as source evidence; the transient encrypted API response is not treated as the financial source.

Exact decoded workbook evidence:

- source link: `https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx`
- bytes: **5,493,673**
- SHA-256: `2fab33e3ece2a39e8dd73832672059a41bb02d605f53471717504665f5b5866c`
- required sheet: **TER**
- exact scheme code: **HEMIDF**
- exact NSDL scheme code: **LTMF/O/E/SCF/14/02/0023**
- exact scheme name: **HSBC Small Cap Fund**

The newest non-future HSBC Small Cap row in the verified workbook is **2026-09-23**:

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.42%** | 0.03% | 0.00% | 0.33% | **1.78%** |
| Direct | **0.56%** | 0.03% | 0.00% | 0.18% | **0.77%** |

The tracker stores the workbook's explicit **Total TER** field; it does **not** calculate TER from the components. Component reconciliation is only a rejection check. The parser also rejects a changed TER-sheet title/header, wrong scheme/NSDL identity, duplicate latest rows, future dates, invalid ranges, Total TER below BER, and component totals that fail the published Total TER within rounding tolerance.

`scripts/refresh_hsbc_expenses.py` performed the idempotent push recovery and records `source_upgrade_hsbc-detailed-ter-v1` only after recent Regular/Direct BER+TER observations exist with the exact CAMS source and one non-empty workbook hash. Normal nightly collection remains active through `amc_expenses.update`; a source failure preserves prior observations.

Production #465 logged:
`HSBC Small Cap Fund: official detailed BER/TER as of 2026-09-23 (Direct 0.56%/0.77% BER/TER)`
and retained hash `2fab33e3ece2a39e8dd73832672059a41bb02d605f53471717504665f5b5866c`.

Status commit `5b0beffa3cf85bd55c21014d75dab0c0fc6fb001` records the published state. Pages artifact **10836118342** is **230,723,187 bytes** with digest `sha256:3cf0cc15bab4c9240d3dfe3bb1bd6e26f1c0b836e998b54dc38d2c371c8e0251`.

### Coverage after this batch

Coverage generated at **2026-09-24T22:15:26Z** is:

- reported TER: **30 / 36** (up from 29 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**

HSBC's published Direct fee is now **TER 0.77% as of 2026-09-23** rather than the older BER fallback. Its current AUM observation is **₹19,210.586 crore as of 2026-09-23** from AMFI, while the complete August portfolio remains **115 positions as of 2026-08-31**.

The six remaining funds without reported TER are **Axis, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps are **Axis, Groww and UTI**.

### Next backend task

**ICICI Prudential Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.70% as of 2026-08-31** from the official ICICI Prudential complete factsheet:
`https://www.icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf`.

Trace the current ICICI Prudential first-party expense/TER disclosure path for an explicitly labelled Total TER. The earlier ICICI *portfolio ZIP* archive-DNS blocker is a separate issue and does not establish a TER blocker; do not conflate those source paths. Store Total TER only if published directly by ICICI Prudential/its explicitly delegated public disclosure route. Do not derive TER from BER, GST or other expense components.

After ICICI Prudential, continue Invesco India, JM, Mahindra Manulife and Mirae Asset. Axis remains special because its current fund page exposes only an unqualified **Expense Ratio** observation; preserve that as `expense_ratio` until an explicitly labelled TER/BER source is found.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this HSBC batch.

## Latest completed batch: Canara Robeco current TER/BER recovery

**Canara Robeco Small Cap Fund now has current, explicitly labelled AMC-published TER and BER.**

PR #94 merged as commit `886de8b4eeaaf223d41dc3eb2609a5c6f6a0427b`. Production workflow **#463**, run **36062579037**, passed cumulative-history restore, the one-time Canara recovery, all **219 tests**, site generation/validation, cumulative-history publication, status recording and GitHub Pages deployment. The run completed successfully at **2026-09-24T21:38:17Z**.

Canara's current Expense Ratio app is client-rendered. Its production browser bundle calls the first-party read-only endpoint:

`https://www.canararobeco.com/wp-json/ter/v1/records?from_date=<YYYY-MM-DD>&to_date=<YYYY-MM-DD>`

The public JSON identifies the scheme by exact name **Canara Robeco Small Cap Fund** and scheme code **SC**, and publishes separate rows for `Regular Plan` and `Direct Plan`. The tracker now requires exactly one row for each plan on the newest complete non-future date. It stores only the AMC-published `base_ter` as **base expense ratio / BER** and `total_ter` as **TER**. It does **not** recompute TER from brokerage, transaction-cost or statutory-levy components.

Production source:
`https://www.canararobeco.com/wp-json/ter/v1/records?from_date=2026-09-18&to_date=2026-09-24`

Published observations retained for **2026-09-24**:

| Plan | BER | Total TER |
| --- | ---: | ---: |
| Regular | **1.46%** | **1.84%** |
| Direct | **0.46%** | **0.68%** |

The collector rejects wrong scheme names/codes, incomplete plan pairs, duplicate plan rows, future dates, missing/non-numeric values, out-of-range values, and a Total TER below BER. Failure retains the previous observations. `tracker/amc_expenses.py` runs inside the normal nightly metrics job, while `scripts/refresh_canara_expenses.py` performed a one-time push backfill and records `source_upgrade_canara-expense-v1` only after all four recent metrics are present from the exact API.

Isolated validation run **36062414901** passed compileall, all **219 tests**, and a live API check that returned the same 2026-09-24 Regular/Direct values above. Production #463 independently passed the same **219-test** regression gate. Status commit `05f2bd2f9fbe1740275ed3a551ac9bc0830caa48` records the published state.

Pages artifact **10835206674** is **231,215,086 bytes** with digest `sha256:593cbe84c1914ef4f5128821b6919aae00cb69128b3f27836fa1340d1e303ded`.

### Expense coverage after this batch

Coverage generated at **2026-09-24T21:37:12Z** is:

- reported TER: **29 / 36** (up from 28 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**

The seven remaining funds without a reported TER are **Axis, HSBC, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps are **Axis, Groww and UTI**.

The source audit before implementation is important: diagnostic run **36061083795** showed that AMFI's current September Small Cap TER query returns **572 daily records** covering the 28 tracker families that already matched, while the eight then-missing TER families were absent rather than merely misspelled. Diagnostic run **36061192992** traced AMFI's live TER page bundle and confirmed the browser uses the same `populate-te-rdata-revised` endpoint/filter structure. Do not add fuzzy aliases merely to force absent AMFI rows to match. Canara was recovered from its own exact first-party disclosure API instead.

### Next backend task

**HSBC Small Cap Fund is the next preferred TER target.** The retained official August source already provides Direct BER **0.56% as of 2026-08-31** from `https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf`, but no TER is currently stored. Inspect the same/current HSBC first-party factsheet or TER disclosure path for an explicitly labelled total TER for Regular and/or Direct plan. Store it only if the AMC publishes the value directly; do not derive Total TER from BER or expense components.

After HSBC, continue through ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset using exact AMC/AMFI disclosures. Axis remains special: its live fund page currently exposes only an unqualified **Expense Ratio** observation, so keep that metric distinct unless an explicit TER/BER source is found.

No UI, permission, paid-service, archive-retention or schedule-cadence change was made in this batch.

## Latest completed batch: Bandhan production recovery plus UTI/Axis/Union source audit

Bandhan's recovery is now production-verified. PR #92 merged as commit `a8c630c5ff36c9cd7d790035f3cedd62845523d8`. Production workflow **#462**, run **36042284692**, passed the release gate and GitHub Pages deployment; Pages artifact **10826922439** is **231,213,983 bytes** with digest `sha256:b44b4a3f985820b8e3643d905d60c1a0563a268fd8a7839e138576b175faa138`. Status commit `540070cfedc193e1f4d0ce925eb47cb37e84d114` records the post-deployment collection state.

Bandhan's public first-party finance disclosure path now resolves the exact Small Cap monthly workbooks through the exact scheme disclosure page and its own post ID. The tracker accepts only the Bandhan Google Cloud Storage bucket returned by that API. Retained official sources are:

- August: `https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx` — SHA-256 `f793184232eb89f776bfab87cc6729dd203af3fce6d054ca23332d6667828975`
- July: `https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/08/797467c3-bandhan-small-cap-fund_74dec064-fd93-4fe8-950a-e55f077e1a6d_31-july-2026.xlsx` — SHA-256 `4e5980ac2cbbe4231b73dabce6765003bc8766e68981fe82b213c50f5ec590b0`

August retains **260 numeric positions**, July **263**, and both reconcile to **100.00% known numeric weight**. They intentionally remain **partial** because Bandhan publishes several tiny equities with the literal marker `$ = Less Than 0.01% of NAV`; those censored positions are not assigned fabricated numeric weights. August workbook AUM is **₹34,176.024349 crore** and July is **₹31,103.029413 crore**. The isolated validation run **36041997427** passed **214 tests** and verified exact URL/host identity, the censored-weight rule, explicit TREPS/cash leaves, idempotency and both month-end workbooks.

### UTI completeness audit — verified disclosure-precision blocker

Diagnostic run **36056204470** inspected the exact already-retained August UTI ZIP:
`https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip?VersionId=HDm7fGngbSbB9olwo6wnStXgJC1XWJ16`.

The relevant first-party workbook is `Sebi Exposure as on 31 Aug 2026_final.xlsx`. The UTI Small Cap block confirms why the current snapshot must remain partial:

- the tracker retains **108** equity rows with exact numeric weights;
- `MTAR TECHNOLOGIES LTD` (ISIN `INE864I01014`, quantity **1**, market value **₹0.07 lakh**) has the literal NAV-weight marker **`*`**, not a number;
- the workbook publishes a **SHORT TERM DEPOSITS** amount of **₹127 lakh** without an exact `% TO NAV` value;
- Net Current Assets is separately published at **3.96%**;
- total UTI Small Cap market value is **₹544,764.68 lakh**.

Do not calculate the censored MTAR weight or a deposit weight from market value/AUM. Under the standing evidence rules, UTI remains **108 positions · 2026-08-31 · partial**.

### Axis completeness audit — current official factsheet still aggregates undisclosed holdings

The current Axis August e-factsheet route was recovered and verified in diagnostic runs **36058054003**, **36058173359**, **36058283743**, **36058525795** and **36058742161**.

Exact first-party sources:

- e-factsheet: `https://www.axismf.com/efactsheet/Aug-2026/Innerpage/SMALL-CAP.html`
- full official PDF: `https://www.axismf.com/efactsheet/Aug-2026/Innerpage/Axis%20Fund%20Factsheet%20August%202026%20Final.pdf`

The full PDF is reachable from GitHub Actions, **8,488,816 bytes**, **171 pages**, unencrypted. Its printed page 16 is the exact Axis Small Cap page, anchored by the mandate, **29 November 2013** allotment date, **Nifty Smallcap 250 TRI**, and **₹31,448.32 crore as of 2026-08-31**.

The portfolio table itself is not a complete constituent disclosure. It publishes **Equity 92.37%**, named holdings down to 0.50%, then the explicit aggregate **Other Domestic Equity (Less than 0.50% of the corpus) 15.20%**, followed by **Debt, Cash & other current assets 7.63%** and **Grand Total 100.00%**. Therefore this source cannot establish the unnamed constituents inside the 15.20% aggregate or split the debt/cash aggregate. Do not mark it complete or turn either aggregate into invented securities. Axis's newer **10-position partial dated 2026-09-16** remains the latest retained snapshot.

This supersedes the older statement that Axis's full factsheet route was inaccessible: the current August full PDF is reachable, but its disclosure format itself prevents a complete named portfolio.

### Union source audit — runner transport still blocked

Union's public Downloads page states that monthly portfolio statements are hosted under its Factsheets & Portfolios section, but the GitHub production network still cannot fetch the application. Diagnostic run **36058957582** requested the exact official page `https://www.unionmf.com/about-us/downloads` and received **`URLError: [Errno 111] Connection refused`** before any client-side API/script discovery could run.

A bounded public-source search found indexed Union factsheets and older disclosure material but no concrete current August Small Cap monthly portfolio attachment that can replace the blocked live transport. No guessed URL, third-party copy, stale IP, TLS bypass or inferred holding was used. Union therefore remains the **only 0-position fund** and a transport/source-discovery blocker.

### Production coverage and next backend target

Post-Bandhan production coverage at **2026-09-24T18:36:27Z** is **36 funds; 35 with a portfolio; 28 complete; 34 current; 28 current+complete; 7 partial**. AUM, a dated Direct fee figure and benchmark identity remain **36/36**. The only zero-portfolio fund is **Union Small Cap Fund**. Current partials are Axis, Bandhan, Edelweiss, ICICI Prudential, Sundaram and UTI; Bajaj Finserv is the only stale partial.

The portfolio backlog is now dominated by verified upstream disclosure/transport limitations rather than untried parser relaxations. Do not re-audit UTI or Axis unless their AMC disclosure format changes, and do not retry Union until a working first-party transport or exact attachment appears.

**Next preferred backend task:** return to expense-metric precision/coverage. Current coverage has reported TER for **28/36** funds and base expense ratio for **33/36**. Missing reported TER: Axis, Canara Robeco, HSBC, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset. Missing base expense ratio: Axis, Groww and UTI. Start with official AMFI revised-TER data and exact AMC disclosures; preserve TER and BER as distinct metrics and never relabel an unqualified expense ratio as TER.

No production parser/data mutation was made by the UTI/Axis/Union audit. Temporary diagnostic workflows are removed before merge.

## Latest completed task: JM complete current + prior monthly portfolio recovery

Merged PR #91 as commit `c9f813dcdbe895ef28d051fda1a879ed3b5ddd7e`. Production workflow **#461**, run **36028576004**, passed cumulative-history restore, parser v128 recovery, all **206 tests**, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T16:37:11Z**, status was recorded at **2026-09-24T16:37:33Z**, and the workflow completed successfully at **2026-09-24T16:38:18Z**.

JM Financial's live Downloads SPA exposes the public first-party API `https://jmmfapi.jmfinancialmf.com/api/`. The browser uses **Portfolio Disclosure** category ID 2 and **Monthly Portfolio of Schemes** subcategory ID 4. Its API responses are AES-CBC encoded with key/IV constants embedded in JM's production browser bundle; these are public application constants, not account credentials. The tracker mirrors the browser-side decode using the system OpenSSL already available on the GitHub runner, with no new Python dependency.

Discovery now reads the public category/listing endpoints, accepts only the exact **JM Small Cap Fund** title, registered JM publication host and XLS/XLSX file type, and selects only the newest two closed calendar month-ends. API listing responses are transient and are **not archived**; only the actual official workbooks and their hashes are retained.

Official source evidence retained in production:

| Reporting date | Positions | Complete | Weight | Quantities | Workbook AUM | SHA-256 |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| 2026-08-31 | 85 | Yes | 100.00% | 83 | ₹929.496506 Cr | `a1060a5d303c8d94e96428afb67aff66e0d00291e184edbbd9341d76149ece24` |
| 2026-07-31 | 83 | Yes | 100.00% | 81 | ₹868.317695 Cr | `17e9e333b30ebbe2b435d574ad0ed0be184945c94325fca089f1f43d14c2dfb5` |

Exact official workbooks:
- August: `https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Small%20Cap%20Fund%20-%20Aug%2031,%202026.xlsx`
- July: `https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Small%20Cap%20Fund%20-%20July%2031,%202026.xlsx`

The generic structured workbook parser already handled all named equities and explicit cash. The only completeness blocker was JM's exact section **`TREPS / Reverse Repo Investments / Corporate Debt Repo`**, whose leaf is **`CCIL`** without an ISIN. Because that heading contains the word "Debt", the generic section-order rule had classified it as Debt before the repo rule. V128 narrowly classifies that exact JM section as Money market and accepts the exact `CCIL` leaf. The retained CCIL weights are **1.1951124861% for August** and **1.0602825455% for July**. No residual/balancing holding is created; all identity, unknown-row, duplicate, market-value, weight and grand-total reconciliation checks remain active.

The website's latest displayed AUM remains the newer **₹955.64 crore as of 2026-09-22** observation; workbook AUM remains separate historical evidence.

Final isolated validation run **36028297259** passed **206 tests** and live API -> browser-compatible AES decode -> workbook ingestion for both months. It verified exact URLs, hashes, AUM, 85/83 position counts, 83/81 quantities, CCIL classification, 100% reconciliation, idempotent second ingestion and non-archival of transient API responses. Production #461 independently logged: **JM current and prior complete portfolios verified: 2026-08-31, 85 positions, 100.000000% weight, complete=1; prior 2026-07-31, 83 positions, 100.000000% weight, complete=1**.

Pages artifact **10820293566** was generated at **231,175,257 bytes** with digest `sha256:2202eb39718fcf682151a23edc0fe7452aad2667ac8c6aac386292b74f40ca23`. JM is now included in normal nightly AMC discovery. No UI, schedule, paid-service, permission, archive-retention policy or Python dependency changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/91 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36028297259 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36028576004 .

## Previous completed task: ICICI complete-portfolio source audit — upstream archive DNS blocker

No production data was promoted in this batch. The purpose was to determine whether **ICICI Prudential Small Cap Fund**, currently **83 named positions dated 2026-08-31 and partial**, has a first-party complete monthly portfolio route that can be collected without inventing the factsheet's separately disclosed **"Equity less than 1% of corpus"** aggregate.

The current ICICI downloads application was traced end to end. Its public API base is `https://apimf.icicipruamc.com`. The live Downloads page uses:

- categories: `GET /nms/v1/downloads/categories?userType=Investor`
- files: `POST /nms/v1/downloads/files`
- category: **Other Scheme Disclosures**
- exact subcategory: **Monthly Portfolio Disclosures**
- subcategory ID: `26a073d7-08d2-4a95-95fa-f83a4ee51e40`
- category code passed by the live UI: `OTHERS`

The API only returns the current monthly portfolio records when the exact Monthly Portfolio subcategory is requested without the broken financial-year filter. The first current records include:

- **Monthly Portfolio Disclosure August 2026** -> `/downloads/Files/Monthly Portfolio Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`
- **Monthly Portfolio Disclosure July 2026** -> `/downloads/Files/Monthly Portfolio Disclosures/2026/July/Monthly-Portfolio-Disclosure-July-2026.zip`

The live `www.icicipruamc.com` August ZIP URL responds **307** and redirects to the first-party archive host:
`https://archive.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`.

That archive host is currently not publicly resolvable. The GitHub runner receives a DNS failure, and an independent public DNS-over-HTTPS check on 2026-09-24 returned **no A and no CNAME Answer** for both `archive.icicipruamc.com` and `www.archive.icicipruamc.com`; the authoritative response contains only the `icicipruamc.com` SOA. The historical `archive.icicipruamc.trafficmanager.net` alias also returns NXDOMAIN. Requesting the same archive path on `apimf.icicipruamc.com` returns the API wrapper's **404 Resource not found**. Therefore the tracker cannot currently obtain the ZIP bytes from a working first-party transport.

Do **not** bypass this by assigning an old IP address, disabling TLS verification, using a third-party cached ZIP as source evidence, or turning the factsheet aggregate into fabricated holdings. ICICI remains **83 positions · 2026-08-31 · partial · current** until the AMC restores a resolvable archive host or exposes the portfolio archive through another working first-party endpoint.

Temporary investigation workflow was removed from the working branch. No production code, parser rule, UI, dependency, permission, schedule, archive-retention policy or source-trust rule changed in this batch. The production state therefore remains the verified Invesco deployment below.

Investigation evidence is in temporary branch Actions runs **36024082115** (exact download category), **36024181676** (valid request variants), **36024378270** (307 redirect target), and **36024773905** (public DNS verification). These runs are diagnostic evidence only; `main` remains the production source of truth.

## Previous completed task: Invesco complete current + prior monthly portfolio recovery

Merged PR #90 as commit `fb2548153b360612366006afe6c7a8a0f36f0970`. Production workflow **#460**, run **36019462111**, passed cumulative-history restore, parser v127 recovery, all **199 tests**, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T15:20:56Z**, status was recorded at **2026-09-24T15:21:18Z**, and the workflow completed successfully at **2026-09-24T15:21:58Z**.
Invesco's current Next.js site exposes the same first-party read-only API used by its Monthly Holdings page: `GET https://www.invescomutualfund.com/api/CompleteMonthlyHoldings?year=<YEAR>&classification=equity`. The API returns exact fund/month workbook URLs. Discovery now selects only the exact **Invesco India Small Cap Fund** row and only the newest two closed calendar months, including January/year rollover handling. Registered-host and workbook-extension checks remain mandatory.

Official source evidence retained in production:

| Reporting date | Positions | Complete | Weight | Quantities | Workbook AUM | SHA-256 |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| 2026-08-31 | 72 | Yes | 100.00% | 70 | ₹15,744.4025 Cr | `f8c3405c0c83ed24502bb4b2f95bff7a0e1022d4dceaf7df3b414029716df83d` |
| 2026-07-31 | 67 | Yes | 100.00% | 65 | ₹14,474.7868 Cr | `7d4924d152355a89a3359176857e5cb7d20d9df1071d3fd3387b5e2e6277fb00` |

Exact official workbooks:
- August: `https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/small-cap.xlsx?sfvrsn=7d249fc2_0`
- July: `https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/smallcap1d1dfe07eee8616aaa28ff00007d74af.xlsx?sfvrsn=6f59fc2_0`

No holdings-parser relaxation was required. The existing structured parser already reconciles the August workbook's **95.25% equity section + 5.19% Triparty Repo + other explicit rows to Grand Total 100%**, with no unknown rows. July also reconciles to 100%. The source-reported quantities are retained, so current/prior share-change comparisons can use 70 August and 65 July quantity-bearing positions where the holdings align.

The website's latest displayed AUM remains the newer **₹16,369.99 crore as of 2026-09-22** observation; the August/July workbook AUM values remain separate historical evidence and are not promoted over a newer observation.

`amc_discovery` now includes Invesco in the normal nightly collector. Parser v127's one-time push recovery is marked successful only after **both** the August current and July prior snapshots are complete and reconcile to 100%. Failed retrieval preserves prior data and leaves the upgrade retryable.

Final isolated validation run **36019264349** passed **199 tests** and live API → workbook ingestion. It verified exact scheme identity, two closed months, January rollover, registered-host rejection, nightly integration, the verified Triparty Repo workbook layout, exact hashes/dates/position counts/AUM, and 70/65 source quantities. Production #460 independently logged: **Invesco current and prior complete portfolios verified: 2026-08-31, 72 positions, 100.00% weight, complete=1; prior 2026-07-31, 67 positions, 100.00% weight, complete=1**.

Pages artifact **10815962825** was generated at **231,158,139 bytes** with digest `sha256:b584e3dad71a95cdf36b0bdd49079d33c4b3f9365110077d4bb4393a06802c32`. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/90 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36019264349 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36019462111 .

## Previous completed task: Sundaram richer current portfolio with verified completeness blocker

Merged PR #89 as commit `49a271401b12813465b69a4f9b8a64b294b29ff5`. Production workflow **#459**, run **36017028358**, passed cumulative-history restore, parser v126 recovery, all regression tests, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T15:01:33Z**, status was recorded at **2026-09-24T15:01:56Z**, and the workflow completed successfully at **2026-09-24T15:03:15Z**.

Sundaram's existing first-party `Fund_Card_data.json` points directly to the official August workbook:

- URL: `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx`
- SHA-256: `663e7170e2810e7f8e89cef9422cb6c4b653b098591eb6530ff61b4d582cb031`
- reporting date: **2026-08-31**
- workbook month-end AUM: **₹4,155.352174 crore**
- retained exact numeric rows: **77 positions**
- known numeric weight sum: **100.000005%**
- completeness: **partial by design**

Before this batch the retained snapshot had **73 positions / 96.560709%** because the generic fallback kept mainly numeric ISIN rows and omitted several explicit non-equity rows. V126 now retains the richer exact-source partial, including **TREPS 5.145861%**, **Margin Money For Derivatives 0.006016%**, and **Cash and Other Net Current Assets -1.761188%**.

The one remaining holding cannot be assigned an exact numeric weight without fabrication. The official workbook gives **Hindustan Dorr Oliver Ltd @**, ISIN `INE551A01022`, quantity 375,961, with the literal percentage cell **`#`**. Sundaram's own footnote defines `#` as **"percentage to NAV of security is less than 0.01%"** and states that the security was delisted on 18 July 2018 and written off in FY 2018-19. The cell is a literal string, not a formula or hidden numeric value. Therefore do **not** convert it to zero, derive an exact ratio, or mark this snapshot complete under the current numeric-weight schema.

The same-source partial-refresh path added in `disclosures.portfolio(..., replace_existing_partial=True)` is deliberately narrow: it can replace holdings only for the exact retained **partial** snapshot with the same source hash. Complete snapshots and different source hashes are untouched.

Final isolated validation run **36016841718** passed **195 tests**. Live ingestion produced **77 positions, complete=0, 100.000005% known numeric weight**, retained the exact source hash/AUM/date above, and confirmed the censored holding was not stored with a fabricated weight. Production #459 independently logged: **Sundaram richer partial portfolio verified: 2026-08-31, 77 positions, 100.000005% known weight, complete=0**, then passed the full site and deployment path.

Pages artifact **10814549515** was generated at **231,253,234 bytes** with digest `sha256:59cd39c0ad8f0c72d575d20c37682638934cd802732b55e22a29e10f76bb02db`. Sundaram's normal nightly discovery remains active through the existing first-party JSON `PORTFOLIO_PATH`. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/89 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36016841718 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36017028358 .

## Previous completed task: TRUSTMF complete monthly portfolio recovery

Merged PR #88 as commit `e9a085165dca5354a533757087222874d348074d`. Production workflow **#458**, run **36013433301**, passed cumulative-history restore, parser v125 recovery, all regression tests, static-site generation/validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T14:32:07Z**, status was recorded at **2026-09-24T14:32:29Z**, and the workflow completed successfully at **2026-09-24T14:34:04Z**.

Before this batch, **TRUSTMF Small Cap Fund** had a current **70-position partial** snapshot dated 2026-08-31. The existing first-party disclosure discovery already exposed the exact monthly workbook through TRUSTMF's read-only API:

- title: **TRUSTMF Monthly Portfolio Report as on 31.08.2026**
- URL: `https://trustmf.com/Content/2026/9/Monthly%20Port_20260909123835.xlsx`
- SHA-256: `834f1709a30b972b5fb5f6322b3dd5687262daaadf32d38ded33df4c6b5ae102`
- parsed portfolio: **73 positions, complete=1, 100.00% weight, as_of=2026-08-31**
- workbook month-end AUM: **₹3,438.9023 crore as of 2026-08-31**

The workbook already reconciled **95.50%** through named securities. The only blocking row was the explicitly published money-market position `TRP_010926 · TREPS 01-Sep-2026` at **4.50%**. Parser v125 recognizes that exact TRUSTMF row only when it appears in the workbook's money-market section. No cash residual, balancing holding or inferred weight is created. Existing scheme-identity, unknown-row, duplicate, market-value, weight and grand-total checks still gate completeness.

The website's latest AUM remains the newer AMFI observation, **₹3,861.35 crore as of 2026-09-22**; the workbook's August AUM is retained separately as dated source evidence.

Final isolated validation run **36013257862** passed **193 tests** and live end-to-end ingestion of the exact official workbook. It produced 73 positions at exactly 100.00%, retained the TREPS row as `Money market`, and retained the workbook AUM/hash/date above. Production run #458 independently verified **TRUSTMF current complete portfolio: 2026-08-31, 73 positions, 100.00% weight, complete=1**, then passed the full site-validation and deployment path.

Pages artifact **10813342822** was generated at **231,252,779 bytes** with digest `sha256:8e9c3f96f5c3ee00f00a7913a2bb1207a04f00120e2db6ad2b2ebea09ed1a299`. The normal nightly `amc_discovery` path already includes TRUSTMF's first-party monthly-disclosure API, so future monthly workbooks remain automatically discoverable after the one-time v125 upgrade. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/88 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36013257862 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36013433301 .

## Previous completed task: Tata complete monthly portfolio recovery

Merged PR #87 as commit `9e503300fd917c6d98e7b4c991322ab6a682c5a5`. Production workflow **#457**, run **35969060794**, passed the full build, archive, static-site validation and GitHub Pages deployment. The published coverage was built at **2026-09-24T07:20:42Z** and the status audit at **2026-09-24T07:20:59Z**.

Before this batch, **Tata Small Cap Fund** exposed only the official top-10 view in the tracker and was stored as a current partial portfolio. Tata's live portfolio page is client-rendered, but its production frontend calls the public read-only endpoint `https://prod-dist-api.tatamfdev.com/cms-data/api/CMSDATA_portfolio?type=monthly`. Discovery now uses that exact endpoint and accepts only dated workbook URLs on Tata's registered publication domain.

The official August workbook is:

- title: **Portfolio as on 31st August, 2026**
- URL: `https://betacms.tatamutualfund.com/system/files/2026-09/Monthly%20Portfolio%20as%20on%2031st%20August%202026.xlsx`
- SHA-256: `40de15ff002fbfa93a7bbc9e54bbb4f0c547e643cd1b6779dd3bf33011457f37`
- parsed portfolio: **67 positions, complete=1, 100.00% weight, as_of=2026-08-31**
- workbook month-end AUM: **₹13,093.88375 crore as of 2026-08-31**

The workbook's 67 positions are the explicitly published securities plus its explicit `I) REPO` and `CASH / NET CURRENT ASSET` rows. Completeness uses the workbook's own `NET ASSETS` value/weight total. No balancing position is inferred. The current AMFI daily AUM observation remains separate and newer; the website therefore still prefers **₹13,471.89 crore as of 2026-09-22** for its latest-AUM display while retaining the August workbook AUM as historical source evidence.

Parser v124 adds only verified structured-layout support: numeric `31-08-26` report dates, the `MKT VAL` header abbreviation, repeated asset-section headers, Tata's explicit repo/cash leaves and Tata's `NET ASSETS` grand total. Existing unknown-row, duplicate, market-value, weight and scheme-identity checks still gate completeness.

Final isolated validation run **35968914879** passed **191 tests** and live end-to-end ingestion of the exact official workbook. Production run #457 independently recovered Tata as **67 complete positions**, then passed the same regression suite, site generation, `validate_site.py`, cumulative-history publication, status recording and Pages deployment. Pages artifact **10795242635** was generated at 231,260,634 bytes with digest `sha256:b383479fa3c1da9787ed1cf142caafbeb60d68cc0e929aad4edd7e2b8eccb5c7`.

Normal nightly `amc_discovery` already includes Tata, so future monthly workbooks use the API-first route automatically. The previous conservative HTML/file-link discovery remains as a fallback if Tata changes frontend transport.

### Axis investigation completed without a data promotion

Axis was investigated first because it was the previous handoff priority. Its official statutory-disclosure area confirms a portfolio section, but the complete download list is client-rendered. The nested first-party CMS route returned access failures from the GitHub runner, alternate static disclosure routes did not expose workbook bytes, and bounded current-month filename probes returned 404. No third-party source, guessed value or weakened source check was used.

**Axis therefore remains a valid 10-position partial snapshot dated 2026-09-16.** Treat the complete Axis portfolio as a verified source-access/discovery blocker until a genuinely reachable first-party workbook/API path appears. Do not repeatedly probe guessed filenames.

## Previous completed task: SBI monthly portfolio recovery

Merged PR #86 as commit `12307fefd86bce92f34b5c56d6f47302acd5cc03`. Production workflow **#456**, run **35965260621**, successfully built, validated, saved cumulative history and deployed GitHub Pages. Deployment completed **2026-09-24T06:37:13Z**. The published coverage was built at **2026-09-24T06:36:16Z**.

Before this batch, SBI's latest portfolio was a **68-position partial snapshot dated 2026-07-31**. It is now a **73-position complete snapshot dated 2026-08-31**, with the **74-position complete July workbook** retained as its prior-month comparator. Both workbooks reconcile to 100.00% using explicitly disclosed rows, actual values and the stated grand total. No balancing holding was invented.

| Reporting date | Positions | Completeness | Weight sum | SHA-256 |
| --- | ---: | --- | ---: | --- |
| 2026-08-31 | 73 | Complete | 100.00% | `71b589984c9b3db4bbb1baf7365072e0e6f604cf18ccfc215a1dc9c1d3183b48` |
| 2026-07-31 | 74 | Complete | 100.00% | `b080c169962567f08b34dc4117368dcfb0fe4e49c182a2f60da842682e6dd1c1` |

Exact official sources:
- August: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---august-2026.xlsx?sfvrsn=9c20b052_2
- July: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---july-2026.xlsx?sfvrsn=e69601db_2

## Implementation and safety boundaries

`tracker/sbi_portfolios.py` uses the public endpoint called by SBI's Portfolios.js: `POST https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets`, with `FundId: 0`, `PSYear`, `PSMonth` and `PSFrequency: Monthly`. It checks only the latest two closed calendar months. It accepts the exact SBI Small Cap Fund monthly workbook title and rejects passive Smallcap index funds/ETFs, mismatched periods, non-workbooks and unregistered hosts. The separate recent-portfolios endpoint returned a server error; do not revert to it or guess attachment filenames.

The verified workbooks contain the exact leaf `Margin amount for Derivative positions`. The parser now recognizes that explicit SBI row as cash/margin. Unknown rows, duplicate holdings, and value/weight mismatches still prevent completeness. Negative receivables are retained; supplementary derivative turnover after the grand total is not added to portfolio assets.

`amc_discovery` includes SBI in normal nightly collection. `scripts/refresh_sbi_portfolios.py` runs a one-time push recovery, with setting `source_upgrade_sbi-monthly-portfolio-v1`. It is marked complete only after successful collection and a current complete portfolio. Failure preserves prior data and a retryable state. The source-scoped extraction key `sbi-monthly-portfolio-v1` retains older extraction audit rows without superseding the independent Quant upgrade. Future scheduled collection remains active after the one-time key is set.

The existing daily schedule remains **18:30 UTC / midnight Asia/Kolkata**. No UI, dependency, permission, paid-service or archive-retention changes were made.

## Validation and publication evidence

Eight new regression tests cover exact source identity/period/host filtering, two-month/year rollover, nightly integration, explicit margin and negative receivables, reconciliation failure cases, source-scoped replay, and retry/idempotency behavior. **All 188 tests passed** with locked dependencies in successful validation run **35965069569**; both real official workbooks also passed live end-to-end ingestion and an idempotent second invocation. Production run #456 passed its full regression gate, generated-site/download validation, cumulative-history save and Pages deployment.

The exact deployed Pages artifact was downloaded and independently checked: artifact **10794395282**, ZIP SHA-256 `db97a0e8916c008381d98654231ac9b610c1dc296d51a8b3721b11833cf89ec8`. It contains SBI snapshot **243** (August, 73 positions, complete, 100.00%) and prior snapshot **244** (July, 74 positions, complete), with the official source hashes above. The August payload has **69 reported equity quantities with prior-month/share-change values**. Its CSV export has 73 rows and the comparison columns. All SBI plan/option entries use the current complete family portfolio.

Verification boundary: the successful Pages deployment and the exact published artifact/data/CSV were verified. Direct HTTP/browser inspection of the public Pages URL was unavailable through this environment's web tool; do not claim a visual browser check was performed. Temporary investigation workflow and encoded patch transport were removed before merge. An initial runner push was rejected for workflow-write permissions after its tests had passed; publication was completed using the authorized connector for workflow edits, without changing permissions or credentials.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/86 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965069569 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965260621 . This final handoff-only commit intentionally skips CI; it does not change deployed code or data.

## Verified coverage after this batch

Coverage at **2026-09-24T16:37:11Z**: **36 funds; 143 NAV series; 281,300 NAV observations; latest NAV 2026-09-23**. AUM, a dated Direct fee figure and reported benchmark identity each have **36/36** coverage.

Portfolios are now **34/36 with holdings; 28 complete; 33 current; 28 current and complete; 6 partial**. The expected month-end is **2026-08-31**. JM improved complete/current-complete coverage **27 -> 28** without changing the 33-fund freshness count because its Top-25 factsheet snapshot was already current.

The remaining collected partials are **Axis, Bajaj Finserv, Edelweiss, ICICI Prudential, Sundaram and UTI**. Bajaj Finserv is the only stale collected portfolio; the other five partials are current under the August freshness target.

The production status audit at **2026-09-24T16:37:33Z** records **113 retained portfolio snapshots, 1,489 archived document records, 1,929,550,764 archive bytes, 99,340,288 database bytes and 2,028,891,052 total retained bytes**. The Pages publication-file budget remains unchanged at 250 MiB.

## Next backend task and remaining blockers

1. **Bandhan Small Cap Fund is the next preferred source-recovery target because it is one of only two funds with no retained portfolio at all.** Re-read the existing WordPress attachment/API discovery and prior failure evidence first. Recover holdings only from an obtainable first-party Bandhan portfolio workbook/PDF/structured attachment; do not promote top-holdings or inferred rows merely to close the zero gap.
2. **Union Small Cap Fund** is the other zero-portfolio gap and remains an official-host transport blocker. Do not weaken source or robots checks.
3. **ICICI Prudential** is a documented first-party transport blocker: its live API exposes exact August/July monthly portfolio ZIPs, but both redirect to `archive.icicipruamc.com`, whose authoritative public DNS had no A/CNAME record on 2026-09-24. Retry only if that official transport changes.
4. **Sundaram** remains a source-precision/data-model blocker because one written-off holding is disclosed only as `<0.01%`. **UTI** remains partial because its current exposure source abbreviates small/short-term positions. Do not infer exact weights.
5. **Axis** remains a first-party access/discovery blocker. **Edelweiss** remains a supported top/named-holdings partial; prior v89-v103 source tracing should be reviewed before any new attempt.
6. **Bajaj Finserv** remains the only stale collected portfolio: **13 partial positions dated 2026-07-31**. Retry only with genuinely new first-party access evidence.
7. Quant, SBI, Tata, TRUSTMF, Invesco and JM are completed structured recovery targets; do not rerun those batches unnecessarily. Re-read `main`, this handoff, current coverage and latest Actions/deployment state before continuing.

Continue backend/data work only unless UI changes are explicitly requested. Preserve exact source URL/hash/report date, units, nulls, conflicts and original archive bytes. Retain the current plus immediately previous calendar-month holdings window and cumulative original evidence. Never invent an exact number or unnamed constituent merely to improve completeness. Avoid broad historical reparses unless a source/parser change genuinely requires them. Update this handoff after the next completed batch.