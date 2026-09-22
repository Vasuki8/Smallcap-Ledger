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

Each GitHub run restores the previous cumulative archive from the `tracker-history` release. It uses the bundled seed only when that release does not exist. A failed download or checksum never silently resets history. After collection and site validation, it uploads a new ZIP before updating `latest.json`. The previous checkpoint is also retained. Obsolete whole-checkpoint copies may be removed, while **each checkpoint still contains all retained historical records and original files**. Expiring Actions caches and artifacts are not the primary archive.

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

### Recommended next work

Do not re-investigate the September publication-size incident unless a new run shows the same failure. Start by checking the latest scheduled workflow and `deployment/update-status.json`.

The AUM coverage gap is now closed. The highest-value remaining data task is checking **portfolio freshness and completeness**, followed by continuing to improve official AMC-source extraction. Preserve the existing rules: never estimate missing values, retain reporting dates and source evidence, preserve conflicts/revisions, and keep the full historical archive separate from the bounded public Pages payload.

For operational reliability, consider adding a regression/health check that fails or prominently warns when `latest_nav_date` is materially behind the latest available AMFI small-cap NAV date. This would detect a future collection or publication failure before the website remains stale for many days.

Other categories can be added by extending AMFI classification, category selection in the API/UI, and benchmark/source mappings. This edition enables only small-cap equity.
