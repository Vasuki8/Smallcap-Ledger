# Smallcap Ledger backend handoff

Updated: 2026-09-24, after TRUSTMF production deployment. Read this file, README.md, current COVERAGE-AS-OF.json and the latest Actions/deployment state before continuing. This handoff supersedes older portfolio-backlog paragraphs retained in README.md. Live repository and source evidence override summaries.

## Latest completed task: TRUSTMF complete monthly portfolio recovery

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

Coverage at **2026-09-24T14:32:07Z**: **36 funds; 143 NAV series; 281,300 NAV observations; latest NAV 2026-09-23**. AUM, a dated Direct fee figure and reported benchmark identity each have **36/36** coverage. These are coverage counts, not a claim that every metric has the latest reporting date or that every fee is TER.

Portfolios: **34/36 with holdings; 26 complete; 33 current; 26 current and complete; 8 partial**. The expected month-end is **2026-08-31**. TRUSTMF improved complete/current-complete coverage **25 -> 26** without changing the 33-fund freshness count because its previous partial snapshot was already current. Quant, SBI, Tata and TRUSTMF are completed recovery targets; do not rerun those batches unnecessarily.

The production status audit at **2026-09-24T14:32:29Z** records 109 retained portfolio snapshots, 1,485 archived document records, 1,929,010,014 archive bytes and 2,028,264,286 total retained bytes. The Pages publication budget remains unchanged at 250 MiB for saved publication files.

## Next backend task and remaining blockers

1. **Sundaram Small Cap Fund is the next preferred completeness target.** It is current at **73 positions dated 2026-08-31** but partial. Its first-party `Fund_Card_data.json` already supplies the scheme's official `PORTFOLIO_PATH`; inspect that exact August source and determine whether all explicit repo/cash/debt/aggregate rows can be reconciled to a published total before changing completeness.
2. Other current partial portfolios are **Axis, Edelweiss, ICICI Prudential, Invesco India, JM and UTI**. Prefer reusable first-party monthly portfolio sources over top-holdings factsheet views. Axis remains a documented access blocker rather than the immediate retry target.
3. **Bajaj Finserv** remains the only stale collected portfolio: 13 partial positions dated 2026-07-31. Its established official-source access blocker remains. Retry only with a genuinely new first-party route or changed access evidence.
4. **Bandhan and Union** remain the two zero-portfolio gaps (`document_not_archived`). Bandhan requires an obtainable official attachment/API route; Union remains an official-host transport blocker, not a reason to weaken its tested parser.
5. Temporary investigation branches are not production source of truth. Re-read `main`, this handoff, current coverage and the latest Actions/deployment state before continuing.

Continue backend/data work only unless UI changes are explicitly requested. Preserve exact source URL/hash/report date, units, nulls, conflicts and original archive bytes. Retain the current plus immediately previous calendar-month holdings window and cumulative original evidence. Never mark partial holdings complete to improve counts. Do not rerun completed Quant/SBI/Tata/TRUSTMF repair work or a broad historical reparse unnecessarily. Update this handoff after the next completed batch.
