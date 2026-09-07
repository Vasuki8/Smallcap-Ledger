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

Numeric AUM, fees, complete portfolios, archived documents and distribution histories are **not complete across all funds**. Missing values remain unavailable, never zero or estimated. Every metric has its own reporting or observation date. Old values are retained when a source fails. Historical documents can only be retained if they are still accessible when discovered.

## Sources

| Information | Public source | Coverage |
| --- | --- | --- |
| Category, plans, codes, ISINs, latest NAV | [AMFI](https://www.amfiindia.com/spages/NAVAll.txt) | Official daily values take precedence over other values for the same code/date. |
| Older NAV | [MFapi](https://www.mfapi.in/) | Free third-party numeric history; clearly attributed. This is a data provider, not a news feed. |
| Expense ratios and components | [AMC reports through AMFI](https://www.amfiindia.com/ter-of-mf-schemes) | Direct/Regular figures with separate TER, BER, brokerage, transaction costs and statutory levies. Checks current and previous months; initially backfills three months. |
| AUM | Official AMC pages and dated reports | HDFC, Axis, DSP, Kotak, Aditya Birla Sun Life, Tata, ITI and Mahindra Manulife parsers, plus supported PDFs such as Nippon India's. AMFI's fund-performance API was inaccessible here and is not relied on. |
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

Checks ran in Linux. Actual GitHub deployment, Windows desktop launch and browser visual testing have not been performed. GitHub-specific actions require your repository/account; the source is ready for that setup.

Other categories can be added by extending AMFI classification, category selection in the API/UI, and benchmark/source mappings. This edition enables only small-cap equity.
