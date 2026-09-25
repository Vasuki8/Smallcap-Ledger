# Research desk UI handoff

Prepared: 2026-09-25. Read this together with `docs/HANDOFF.md`; the backend handoff remains authoritative for source collection and financial contracts.

## Product direction

Smallcap Ledger is a fund-research workspace, not a trading terminal or an automatic recommendation engine. The standing user direction is **minimal, attractive, easy to navigate, light only**. Desktop uses an aligned table; phones use compact cards. Research depth is revealed progressively rather than placing every control and diagnostic on the landing page.

This redesign replaces the accumulated stylesheet rather than appending another override layer. The palette is warm off-white, dark slate and restrained emerald. Data and source evidence have priority over decoration. No external font, icon library, analytics service, account, paid infrastructure or data feed is introduced.

## Implemented surfaces

- **Explore:** search fund, AMC or AMFI code; plan/option view; fund-house filter; portfolio completeness filter; sortable columns; empty-state reset; pagination. NAV, AUM, expense, 1Y, 3Y CAGR and 5Y CAGR remain visible. Missing values sort last in either direction. Expense labels retain TER, observed TER, BER or unqualified expense distinctions and reporting dates/source links.
- **Saved:** browser-local shortlist keyed by AMFI scheme code, not only the fund family. Direct, Regular and other options remain distinct. The interface states that this is not synced across devices. Invalid stored preferences are ignored; unavailable storage falls back to the current visit.
- **Compare:** up to three plans in a side-by-side table, a selection tray, removal/clear controls and shareable scheme-code URLs. Every plan retains its own reporting date. Mixed plan types and non-Growth options are explicitly qualified. This is a sourced comparison, not a score or ranking recommendation.
- **Fund pages:** new identity/header, plan selector, save/compare actions and section navigation. Existing financial analytics are reused. Overview retains six metrics, reported-benchmark context and evidence-backed fund facts. Deep details stay in Performance, Portfolio, Fees & AUM and AMC documents.
- **Performance:** existing chart modes, reported benchmark, explicit alternate comparison, custom dates, returns and SIP analysis remain. Advanced sections retain their open state after redraw. Invalid date/SIP inputs are rejected; superseded performance responses do not replace the newest requested result.
- **Portfolio:** existing current-month holdings, shares and previous-month comparison contract are preserved. Adds search by name, ISIN or sector. It does not infer purchases or sales from weight changes.
- **AMC documents:** title search and type filter; fund-specific versus AMC-wide context; explicit publication versus first-found dates; original, saved-copy and archived-version links.
- **Data & sources:** coverage, reporting/build dates, storage separation, methodology and collection history. Uncompressed logical retention is not presented as the daily transfer or site download size.
- **Update status:** searchable/filterable source rows. Disabled/Excluded is inactive; unrecognized statuses are pending/unknown, never automatically healthy.

## Navigation and responsiveness

Desktop primary navigation: Explore / Compare / Saved. Data & sources and update health are secondary tools. Mobile uses Explore / Compare / Saved / Data in a bottom navigation bar. The confusing public refresh button remains absent; real local refresh is retained.

Above 800px the directory is a true table. Any excess width scrolls inside its labelled region, not the whole page. Its header is static, avoiding the old sticky-offset misalignment. At 800px and below, rows become compact cards and preserve all numeric fields. Fund tabs use the actual global header height. Keyboard users have a working skip link, visible focus, normal fund anchors, comparison checkboxes, sortable header buttons and `/` to focus directory search. Reduced motion is respected. This is not a claim of complete WCAG certification.

## Architecture and preservation rules

`dist/research.js` composes the presentation layer after the existing deferred `app.js`. It replaces the original hash-change listener exactly once, delegates unchanged fund calculations to the core, and uses the existing local/static API adapters. `app.js`, `analytics.js`, `static-data.js`, collectors, export data contracts and storage are not rewritten by this change. `index.html` uses revisioned CSS/UI URLs so old cached assets are not silently reused.

Preserve these recent backend contracts:

1. A reported BSE benchmark with missing TRI history remains unavailable by default. Do not silently substitute Nifty Smallcap 250 TRI. Alternate comparisons require explicit selection and remain labelled.
2. IDCW or Bonus NAV alone is not total return; preserve existing distribution/unit-adjustment safeguards and null returns.
3. Portfolio deltas use the backend's previous-calendar-month semantics and completeness/quantity qualifications. Do not reintroduce arbitrary older-snapshot comparisons.
4. Never invent reporting dates, original source hashes, coverage or missing values.
5. The user's current retention decision is to **keep all original evidence**. This UI batch does not delete, prune, migrate or replace retained source data.

## Verification performed before PR

- JavaScript syntax checks passed for the new layer and unchanged core clients.
- Ten new network-free regression tests cover dependency order, cache revision, client syntax, saved-code validation, numeric/missing values, safe source links, numeric AUM sorting without input mutation, expense priority, deterministic tie breaks, and inactive/unknown status semantics.
- An offline Chromium DOM harness using the authentic published Pages data from artifact `10884112452` exercised **59 successful checks**: directory/filter/reset/sorting flows; saved/unsaved plans; three-plan comparison limit and invalid URLs; six overview metrics; reported Nifty and missing BSE behavior; performance/custom dates; disclosure retention; holdings and document search; data/status views; and responsive layouts at 1440, 1280, 1024, 801, 800, 768, 600, 480, 390, 375 and 320px. No unhandled client error occurred in that run.
- Screenshots of desktop directory, comparison, fund overview and mobile views were inspected. The test exposed and fixed screen-reader-only labels causing root overflow on small laptops, and the current-portfolio view having no historical snapshot picker.
- Harness limitation: environment policy blocks browser URL navigation. Data loading and browser storage were shimmed locally for those DOM tests; this is not live-network, native persistence, cross-browser or native-device certification. Downloaded original binaries were not re-fetched. GitHub regression/deployment results must be checked separately before calling the redesign live.

The added `Research UI checks` pull-request workflow runs the repository's full existing regression suite plus these UI tests with read-only repository permissions. It does not collect data, restore production archives, modify release assets or publish Pages.

## Suggested next features — not implemented in this batch

### 1. Portfolio overlap and diversification (highest priority)

Let users compare shared holdings, common positions and overlapping disclosed weight. Inputs: canonical ISIN, same reporting month, fund-family identity, weights, asset type, completeness and source references. Default to complete comparable snapshots. Different dates or partial disclosures require explicit warnings; do not manufacture a full-fund overlap from a partial top-ten list. Explain the selected overlap formula and denominator. Do not describe overlap as a recommendation to buy/sell.

### 2. What changed since my last review

A compact research change log for saved funds: newly published portfolio, reported manager/benchmark changes, revised expenses and new AMC documents. Inputs: immutable field observations, true reporting dates, discovery timestamps, previous values, corrections and source identifiers. Distinguish economic/report changes from collection fixes. Begin with an in-app view; email/push/account features require a separate product and privacy decision.

### 3. Long-term consistency, not only trailing winners

A research view for rolling-return distributions, drawdown/recovery and fund-versus-reported-benchmark periods. Use sufficient matching daily history, label period coverage and handle missing TRI, plan changes and distribution adjustments. Do not introduce unexplained star ratings or an opaque best-fund score. Existing rolling-return and drawdown tools are a starting point, not a complete new feature.

### 4. Multi-category expansion

Before adding categories, generalize category IDs, scheme-family/plan/option identity, official category effective dates, category-specific benchmark mapping and eligibility. Add a category switcher only once populated and validated; no empty Large Cap/Mid Cap navigation placeholders. Retain per-category coverage gaps and source dates. Consider category history when comparing a fund across a strategy change.

### 5. Research exports and saved screens

Export the current comparison with units, dates and source links, then add reusable local filter presets. Avoid extra duplicate download controls on every card. Persist only non-sensitive research preferences by default; no brokerage credentials, holdings imports or account synchronization in this scope.

## Release status

This document records implementation and local verification. PR merge, workflow conclusion and deployed asset verification are separate evidence and must be appended after checking them. Do not equate a branch commit or passing syntax check with a live deployment.
