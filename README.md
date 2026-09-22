# Smallcap Ledger

Indian small-cap mutual fund tracker for **GitHub Pages**, with a daily GitHub Actions updater and a cumulative historical archive. The included Windows edition uses the same data and calculations.

Start with **[GITHUB-SETUP.md](GITHUB-SETUP.md)** to put it online. No cloud database, paid feed, API key, or open browser is needed for the daily workflow. Hosting and updating become active after you upload the project to a public GitHub repository, enable Pages, and complete the first successful workflow run.

## What changed

- AUM and expense ratios are prominent in the directory, mobile fund cards, and individual fund overview, with dates and source links.
- Each overview displays a fund-versus-index chart. The full Performance tab provides dates, returns, drawdown, rolling returns and SIP calculations.
- Third-party news collection has been removed. **Fund communications** retains official AMC factsheets, newsletters, letters, disclosures and market views. Automatic discovery accepts only the corresponding AMC's configured domains and subdomains.
- A static export works under a GitHub project URL such as `https://YOUR-USERNAME.github.io/smallcap-ledger/`.
- The workflow requests a start at **00:00 IST / Asia/Kolkata**, daily. GitHub cron uses UTC: `30 18 * * *`. GitHub can delay or skip scheduled runs; a source check is not a promise that an AMC has published new data.

## Included data and coverage

See **[COVERAGE-AS-OF.md](COVERAGE-AS-OF.md)** for exact included counts, dates and per-fund gaps. The package includes a collected historical starting archive in `bootstrap/`, split into files below GitHub's browser-upload limit.

All AMFI-listed plans and options in the small-cap equity category are retained, including Direct, Regular, IDCW and other published variants. The initial directory filter is Direct/Growth; choose All plans and All options to see every series. Payout and reinvestment can share one AMFI NAV series; the available ISINs and option labels remain visible.

Historical AUM/fee depth, complete portfolios, archived documents and distribution histories are **not complete across all funds**. Current sourced AUM and expense coverage is complete for the tracked fund universe, while older history can still contain gaps. Missing values remain unavailable, never zero or estimated. Every metric has its own reporting or observation date. Old values are retained when a source fails. Historical documents can only be retained if they are still accessible when discovered.

## Sources

| Information | Public source | Coverage |
| --- | --- | --- |
| Category, plans, codes, ISINs, latest NAV | [AMFI](https://www.amfiindia.com/spages/NAVAll.txt) | Official daily values take precedence over other values for the same code/date. |
| Older NAV | [MFapi](https://www.mfapi.in/) | Free third-party numeric history; clearly attributed. This is a data provider, not a news feed. |
| Expense ratios and components | [AMC reports through AMFI](https://www.amfiindia.com/ter-of-mf-schemes) | Direct/Regular figures with separate TER, BER, brokerage, transaction costs and statutory levies. Checks current and previous months; initially backfills three months. |
| AUM | [AMFI Fund Performance](https://www.amfiindia.com/otherdata/fund-performance) plus official AMC pages and dated reports | Daily scheme AUM from AMFI is retained with its NAV/report date and archived response hash. Month-end and average AUM from AMC factsheets remain separate historical observations. Verified current coverage: 36/36 funds. |
| Nifty Smallcap 250 TRI | [NSE Indices](https://www.niftyindices.com/reports/historical-data) | Actual total-return index levels, including historical backfill. |
| Holdings and fund facts | Original AMC Excel/XML/PDF reports | Supported layouts only. Automatically extracted holdings remain labelled partial. |
| Fund communications | `tracker/sources.json` and discovered official AMC pages | Original links and saved versions. Fund-specific and fund-house-wide publications are labelled separately. External publisher news is excluded. |

Sources requiring sign-in, a challenge or unsupported dynamic rendering remain gaps. Checks use timeouts, robots rules and download-size limits. Website layouts can change; sources, dates and collection results make failures visible.

## Calculations

- Growth NAV returns already reflect fund expenses. Tax and exit loads are excluded.
- 1M, 3M and 6M returns are absolute. Year-labelled periods use CAGR and actual days / 365.25. The nearest preceding observation must be within seven calendar days of the target date.
- Fund/index lines use only dates present in both series, rebased to 100 on their first common date. There is no forward fill. The return table uses full matching history through the selected end date.
- If the stated benchmark is unavailable or unverified, Nifty Smallcap 250 TRI is explicitly a **category comparator**. BSE and other index histories require official TRI imports. Historical benchmark changes are not mapped.
- IDCW NAV alone is not total return. Adjusted comparisons and SIP results require complete, user-confirmed distribution history and applicable reinvestment NAVs. Bonus options also need unit adjustments and currently remain NAV-only.
- Drawdown uses the selected range's running peak. Volatility is sample standard deviation of log NAV returns × √252; gaps longer than seven days are excluded. Rolling three-year CAGR is sampled approximately weekly.
- SIPs buy at the first available NAV of each month in the selected range. XIRR uses actual dates; unsupported numerical roots are unavailable.
- AUM is in **₹ crore**, normally fund-wide. Do not sum it across plan rows. Fees are annual percentage points: `0.65` means `0.65%`. BER, TER, website observations and scheme expense ceilings are different fields. A reported TER takes priority in the display.
- Portfolio weight changes can reflect prices, flows and trades. Leaving a partial list is not a confirmed sale.

## Historical storage

`data/ledger.sqlite3` stores schemes, current series, earlier NAV/index observations, dated metrics, holdings, documents and update logs. `data/archive/` retains source bytes by SHA-256. Identical bytes are deduplicated; revised values and document versions remain in history.

GitHub history now uses **split checkpoint format 2**. `latest.json` points to a compact SQLite database checkpoint plus immutable reusable source-file packs. Normal runs restore the database first and materialize source files on demand. New source hashes create new packs; older packs are reused instead of rebuilding the full archive. Restore remains backward-compatible with the original cumulative ZIP format, and legacy migration checkpoints are currently retained for rollback. A failed download or checksum never silently resets history.

To keep GitHub Pages deployable as the archive grows, the public static site uses a fixed **250 MiB publication-file budget**, prioritizing the newest non-source-page AMC files. Publication metadata and original source links remain visible even when a saved copy is not bundled into Pages. The complete saved version history remains preserved in the cumulative `tracker-history` release and is not deleted from the underlying archive.

Collection has a 40-minute budget. If interrupted, completed records are retained, the interrupted job is labelled, and the next run prioritizes the least recently checked sources. A failed later build leaves the last published site online. Builds commit a compact collection audit to `deployment/update-status.json`.

## Local edition and imports

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), extract the package and double-click `START-WINDOWS.cmd`. The first launch restores the bundled starting archive. uv installs Python 3.12 and the locked dependencies; no virtual-environment activation is needed. Local checks run only while the app is running. See [START-HERE.md](START-HERE.md).

Use the local **Data & archive** page to import original fund publications or UTF-8 CSVs:

| Record | CSV columns | Units / meaning |
| --- | --- | --- |
| AUM, fees, facts | `metric,plan,as_of,value` | AUM: `aum`, `All`, ₹ crore. Fees: annual percentage points with Direct/Regular. Dates: YYYY-MM-DD. |
| Holdings | `isin,name,sector,weight,asset_type` | Weight in % of net assets. Enter reporting date; mark complete only for a full portfolio. |
| Benchmark | `date,value` | Official TRI levels under the correct index name. |
| IDCW | `ex_date,amount,reinvestment_nav` | Gross rupees/unit, applicable reinvestment NAV, and confirmed complete coverage interval. |

Supported metrics include `aum`, `ter`, `base_expense_ratio`, `brokerage`, `transaction_cost`, `statutory_levies`, `exit_load`, `benchmark`, `managers`, `fund_launch`, `objective`, `risk`, `minimum_sip` and `minimum_lumpsum`. Imports retain the original file and source URL. The GitHub site is read-only for visitors; its owner can publish local additions using the setup guide.

## Code and verification

| File or folder | Purpose |
| --- | --- |
| `tracker/` | Source adapters, SQLite archive, calculations, local API and updater. |
| `dist/` | HTML/CSS/JavaScript interface; no external frontend CDN. |
| `scripts/export_site.py` | Generate static `site/` with JSON data and downloads. |
| `scripts/github_state.py` | Verified seed restore and cumulative release checkpoints. |
| `scripts/daily_update.py` | Independent public-source update jobs. |
| `.github/workflows/daily.yml` | Schedule, collection, history persistence and Pages deployment. |
| `scripts/validate_site.py` | Generated series, metric coverage and download checks. |
| `tests/test_tracker.py` | Financial, parser, import and archive invariants. |

Python 3.12 runs through uv. Node is used only for automated JavaScript/Python parity checks on the GitHub runner; it is not needed to run the local website.

```powershell
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/export_site.py
uv run --frozen python scripts/validate_site.py site
```

Automated checks run in Linux on GitHub Actions. GitHub Pages deployment has been exercised successfully in the live repository. Windows desktop launch and full browser visual regression testing are still separate checks.


## Handoff for the next prompt — 2026-09-22

Treat the repository, `deployment/update-status.json`, the `tracker-history` release, and the latest GitHub Actions runs as the source of truth before making further changes.

### Incident resolved: daily data was collected but not published

The tracker appeared stale because scheduled GitHub Actions runs were completing the data-collection stage but failing during `scripts/export_site.py`. The public site had grown past the previous 900 MiB safety threshold because archived AMC publication files were being copied into GitHub Pages. The last successfully published NAV had therefore remained stuck at **2026-09-07** even while later scheduled collectors were running.

The publication architecture was repaired without deleting historical evidence:

- The cumulative `tracker-history` release still preserves the complete SQLite archive and all retained source files/versions.
- GitHub Pages now uses a fixed **250 MiB AMC publication-file budget**, prioritizing newer non-source-page publications.
- Publication metadata and original AMC links remain visible even when a saved binary is not included in the static Pages artifact.
- The generated public site has a **400 MiB guard** so archive growth cannot silently push Pages back toward the previous failure state.
- `dist/app.js` explains when older saved versions are available only from the full historical archive.
- `scripts/export_site.py` records `latest_nav_date`, publication-file counts and publication bytes in the status audit.
- The temporary collect-on-push behavior used for recovery was removed. Normal collection is again limited to the daily schedule or an explicitly refreshed manual workflow run.

### Verified recovery state

The one-time catch-up workflow completed collection, tests, site generation, validation, cumulative archive persistence, status recording, artifact upload and GitHub Pages deployment successfully.

Latest verified audit in `deployment/update-status.json`:

| Item | Verified state |
| --- | --- |
| Latest NAV date | **2026-09-21** |
| NAV observations | **280,984** |
| Benchmark observations | **5,326** |
| Portfolio snapshots | **154** |
| Archived document versions | **852** |
| AUM coverage | **36 / 36 funds** |
| Expense coverage | **36 / 36 funds** |
| Full retained archive size | **1,187,418,323 bytes** |
| Publication-file budget | **262,144,000 bytes (250 MiB)** |
| Publication files bundled into Pages | **177** |
| Publication bytes bundled into Pages | **262,143,558 bytes** |

The repaired catch-up Pages artifact was approximately **338 MB** and passed `scripts/validate_site.py`. The successful recovery deployment was GitHub Actions run **35680822286**.

### AUM coverage completed

The final missing AUM fund was **Bandhan Small Cap Fund**. Bandhan's public CMS pages did not expose a direct factsheet file URL and its public WordPress media API returned 401, so no access-control bypass was used. Instead, the tracker now uses AMFI's official Fund Performance feed in `tracker/amfi_metrics.py`.

The production collector dynamically resolves the open-ended equity / Small Cap filter, checks recent business dates until AMFI has a category-wide response, archives the exact JSON bytes by SHA-256, and stores only matched positive `dailyAUM` values as dated scheme-level AUM observations. It does not overwrite older factsheet observations.

Verified production run **35685317689** collected **36/36** small-cap AUM values from AMFI as of **2026-09-18**. For Bandhan Small Cap Fund, AMFI returned `dailyAUM = 35153.113` with `navDate = 18-Sep-2026`. The run passed **65 tests**, static-site validation, cumulative archive publication and GitHub Pages deployment. Production collector commit: `005a34e583568524afa251c89f30476833b48ac9`.

The AMFI daily-AUM collector is part of the scheduled `metrics` update path. The temporary push-only AUM refresh used for verification has been removed, so ordinary code pushes do not perform the full daily data refresh.

### Current automatic-update behavior

The normal workflow remains `.github/workflows/daily.yml`:

- schedule: `30 18 * * *`
- intended time: **00:00 IST / Asia/Kolkata daily**
- scheduled runs execute `scripts/daily_update.py`
- manual `workflow_dispatch` with `refresh=true` also performs collection
- ordinary pushes rebuild/deploy and run the AMC report-upgrade step, but do **not** run the full daily collector
- every successful publication restores the previous cumulative archive first, validates the generated site, saves a new cumulative checkpoint, records `deployment/update-status.json`, and then deploys Pages


### UI/navigation refresh — 2026-09-22

The public interface received a navigation-focused light-theme refresh in PR #5 (merged as `d9907899c80ee9dae2d21cecd4bdbcb8c6eac7f5`). The change is UI-only: it does not alter collection, calculations, source evidence, or historical storage.

- Primary navigation is simplified to **Funds**, **Data**, and **Updates**.
- Desktop uses a lighter research workspace with clearer search/filter hierarchy.
- Fund-detail tabs remain visible while scrolling.
- Mobile uses a persistent bottom navigation bar and a compact sticky header.
- Fund tables, metric cards, badges, forms, and responsive spacing were cleaned up for easier scanning.


### Fund-detail UI refresh — 2026-09-22

A second UI-only refinement was merged in PR #6 (commit `d98bb4351edc6000257665386eed5fe9b2639e75`). It does not change financial calculations, collectors, source rules, or stored data.

- Fund pages now use a compact fund header with clearer plan/option metadata and plan switching.
- Overview surfaces NAV, AUM, expense ratio, 1-year return, and 3-year CAGR before deeper sections.
- An **At a glance** panel provides fund facts plus direct links to Portfolio, Fees, and official documents.
- The investment objective is collapsed by default to reduce vertical scrolling.
- Performance, Portfolio, and Fees layouts were tightened for faster scanning.
- Fund communications now supports title/type search in addition to document-type filters.
- Mobile fund pages retain sticky section tabs and the bottom navigation introduced in PR #5.


### Fund-directory UI refresh — 2026-09-22

A third UI-only refinement was merged in PR #7 (commit `2322e5c3b7fe2b568f4e4e6fcd392160edb44e36`). It keeps the existing Direct Growth default and does not alter data, collectors, calculations, or source evidence.

- Added one-tap presets for **Direct Growth**, **Regular Growth**, **All Growth**, **IDCW**, and **All series**.
- Search, plan, option, and sort controls are clearer and easier to reset.
- Result counts now show both unique funds and NAV series.
- Desktop discovery controls and table headers stay visible while scrolling.
- Mobile directory cards are simplified and include a direct **Open fund** action.
- Empty search/filter states now include a reset path instead of leaving the user stuck.


### Data and update-health UI refresh — 2026-09-22

A fourth UI-only refinement was merged in PR #8 (commit `5efcb6f932cad58c8f4475249a80e8a5d9d481a4`). It does not change scheduling, collectors, source rules, calculations, or historical storage.

- **Data & archive** now emphasizes retained observations, AUM/expense coverage, portfolio snapshots, source evidence, and archive health.
- Archive actions, maintenance links, and recent update activity are easier to find.
- **Updates** now presents the daily schedule as an operational health view rather than a settings-heavy page.
- Source checks are summarized as **healthy** versus **needs attention** states, with better detail visibility on mobile.
- The source-status table is responsive and easier to scan without horizontal scrolling.


### Accessibility and consistency polish — 2026-09-22

A fifth UI-only refinement was merged in PR #9 (commit `b6db9dfd029129414675ee4282fa862cfa04d694`). It does not change mutual-fund data, calculations, collectors, source rules, schedules, or historical storage.

- Added a keyboard **Skip to main content** link.
- Main navigation, fund tabs, directory presets, document filters, and performance range controls now expose their active state to assistive technology.
- Route loading now uses accessibility status semantics and main content reports busy state while views change.
- Visible keyboard focus, touch target sizing, mobile spacing, small-screen statistics, wrapping, and focused table/document states were tightened across the site.
- Reduced-motion preferences remain respected.


### Minimal UI direction — 2026-09-22

A sixth UI-only refinement was merged in PR #10 (commit `cbfe4da216acd155f87afc2058aed7d92c3170aa`). This pass intentionally removes UI rather than adding more.

- Dashboard summary cards and duplicate fund-view controls were removed.
- Fund discovery now uses one **Fund view** selector plus search and sort.
- The directory table is reduced to the essential comparison fields: NAV, AUM, expense, 1Y, and 3Y CAGR.
- Fund pages use a simpler header and a compact summary strip instead of multiple metric cards and shortcut panels.
- Data and Updates are condensed into focused summaries with optional details.
- The visual system is flatter and quieter: fewer badges, softer borders, less shadow, more whitespace, and simpler navigation.

The standing UI direction is now: **minimal, attractive, and easy to navigate**. Prefer removing or consolidating interface elements before adding new controls.


### Minimal research tabs — 2026-09-22

A seventh UI-only refinement was merged in PR #11 (commit `52b71273301b2d41046075192ec54228e570b7de`). It continues the standing rule to keep the interface minimal while preserving research depth.

- **Performance** now centers on one chart; custom dates and benchmark selection live under Advanced options.
- Return tables and the SIP backtest are collapsed until requested.
- **Portfolio** keeps holdings visible first; sector allocation and snapshot changes are optional details.
- **Fees** surfaces current AUM, expense and exit load; the full dated audit table is collapsed.
- **Documents** now uses search plus one document-type selector instead of multiple filter chips and badges.


### Portfolio freshness and Kotak recovery — 2026-09-22

Portfolio coverage is now measured by both **completeness** and **freshness** instead of a single any-portfolio count. The current expected reporting month-end is calculated with a 10-day new-month grace; on 2026-09-22 the expected date is **2026-08-31**.

Production-verified coverage after GitHub Actions run **35777005426**:

| Portfolio measure | Coverage |
| --- | ---: |
| Any parsed portfolio | **22 / 36 funds** |
| Complete portfolio | **16 / 36 funds** |
| Current portfolio | **15 / 36 funds** |
| Current + complete | **12 / 36 funds** |
| Partial latest portfolio | **6 / 36 funds** |

Kotak Small Cap Fund was recovered from its official August 2026 digital factsheet. The first parser attempt passed synthetic tests but produced zero production records because Kotak serves responsive/duplicate table structures. Commit `16b302e663a674aaf72011359bd1fe805297dbfd` now tries every qualifying table and accepts only one that fully reconciles sector subtotals, equity total, Triparty Repo, net current assets and grand total.

Verified Kotak production record:

- as of **2026-08-31**
- **81 positions**
- marked **complete**
- source: `https://www.kotakmf.com/factsheet/August_2026/kotak/SMALL-CAP.html`
- benchmark identity captured as **NIFTY Smallcap 250 TRI**
- original source remains archived with the cumulative history

Operational reliability also improved: `scripts/validate_site.py` now requires `latest_nav_date` and fails publication when the latest NAV is more than **7 calendar days old**. Run 35777005426 passed with latest NAV **2026-09-21**, age **1 day**, and all automated tests/site validation green.

The next portfolio-source candidates should be handled conservatively one source family at a time. Bandhan exposes official detailed-scheme-portfolio pages, and quant Mutual Fund exposes an official monthly/fortnightly portfolio archive, but neither should be marked covered until the original downloadable evidence is archived and its scheme table is reconciled by the parser.



### Axis partial portfolio recovery — 2026-09-22

Axis Small Cap Fund now has a dated **partial** portfolio from the official fund page. The adapter uses Axis's explicit **Top 10 Stocks (%)** total and its update date, requires the parsed holding percentages to reconcile to that published total, and deliberately stores the snapshot with `complete=false`.

Production-verified after GitHub Actions run **35779546044**:

- portfolio coverage: **23 / 36 funds**
- complete portfolio: **16 / 36**
- current portfolio: **16 / 36**
- current + complete: **12 / 36**
- partial latest portfolio: **7 / 36**
- Axis portfolio: **10 positions**, as of **2026-09-16**, partial
- Axis source: `https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct`
- latest NAV remains **2026-09-21**
- build, tests, site validation, archive save and Pages deployment all passed

Two intermediate Axis development runs failed the test gate because a code insertion left a duplicate/damaged parser tail. Those runs did **not** publish an archive or website. Commit `128db83f96f3da8e3b235f9598cf10629c549c91` removed the duplicate tail; the module now has one definition each for the AMC helpers, `parse_page`, and `update`.



### Minimal navigation and mobile polish — 2026-09-22

A later UI-only refinement was merged in PR #14 (commit `f1d590ad8904bb40d1d7773caee081738e602b87`). It continues the minimal/mobile-first direction without changing data or collection behavior.

- Whole fund rows/cards are now directly openable by click and keyboard.
- Small-screen fund cards hide secondary fields and keep NAV, AUM, and 3Y CAGR visible.
- Fund tabs scroll cleanly on narrow screens without visible scrollbar clutter.
- Charts use quieter gridlines/tooltips and less hover decoration.
- Remaining mobile spacing and navigation density were tightened.


### Split archive storage migration — 2026-09-22

The historical archive has been migrated to **format 2** without deleting source evidence.

- Active database checkpoints are about **12.36 MB compressed**, versus the previous ~**1.09 GB** cumulative checkpoint upload.
- Historical source evidence is stored in immutable reusable `sources-*.zip` packs.
- Daily workflows use database-only restore first and materialize source files on demand.
- Run **#95** verified the thin restore path; database restore completed in about 3 seconds and the new checkpoint upload consisted of a ~12 MB database plus a ~157 KB source pack.
- Parser materialization was subsequently narrowed to only catalog and pending spreadsheet source hashes.
- Legacy cumulative `state-*.zip` files remain in the release as rollback copies. Removing them would be destructive and requires an explicit cleanup decision.

### Recommended next work

Do not re-investigate the September publication-size incident unless a new run shows the same failure. Start by checking the latest scheduled workflow and `deployment/update-status.json`.

The AUM coverage gap is now closed. The highest-value remaining data task is checking **portfolio freshness and completeness**, followed by continuing to improve official AMC-source extraction. Preserve the existing rules: never estimate missing values, retain reporting dates and source evidence, preserve conflicts/revisions, and keep the full historical archive separate from the bounded public Pages payload.

For operational reliability, consider adding a regression/health check that fails or prominently warns when `latest_nav_date` is materially behind the latest available AMFI small-cap NAV date. This would detect a future collection or publication failure before the website remains stale for many days.

Other categories can be added by extending AMFI classification, category selection in the API/UI, and benchmark/source mappings. This edition enables only small-cap equity.
