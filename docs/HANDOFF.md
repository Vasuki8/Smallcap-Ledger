# Smallcap Ledger backend handoff

Updated: 2026-09-24, after Bandhan production recovery and the UTI/Axis/Union portfolio-source audit. Read this file, README.md, current COVERAGE-AS-OF.json and the latest Actions/deployment state before continuing. This handoff supersedes older portfolio-backlog paragraphs retained in README.md. Live repository and source evidence override summaries.

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
