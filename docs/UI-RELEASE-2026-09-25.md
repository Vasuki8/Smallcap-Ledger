# Research desk UI release — 2026-09-25

This is the release verification addendum to `docs/UI-HANDOFF.md`. Read the backend's `docs/HANDOFF.md` separately; no financial-data or retention rules were changed by this UI release.

## Release evidence

- PR **#149**: https://github.com/Vasuki8/Smallcap-Ledger/pull/149
- Merged commit: `637b68f5224e2209a25474a7566b813991f25cbe`.
- Pre-merge Research UI checks: run `36190479212`, job `108254132376`, **359 tests passed** in 10.552 seconds; source syntax passed. The job tested the PR merge with the then-current main, not only the feature branch.
- Production workflow **#508**, run `36190807602`: **build and deploy both completed successfully**. Site generation, validation, archive persistence and Pages publication succeeded.
- Published Pages artifact `10887539478` was downloaded and inspected. Its `research.js`, `style.css`, `index.html`, `app.js`, `analytics.js` and `static-data.js` matched the locally tested files byte-for-byte.
- The artifact's data snapshot was built at `2026-09-25T21:19:37+00:00`; latest included NAV date `2026-09-24`. These are separate timestamps, not a claim of new NAV at publication time.

## UI verification and limits

Ten new network-free regression tests passed locally and in CI. An offline Chromium DOM harness with authentic published data passed **59 interaction/responsiveness checks**, including widths 320–1440px, plus **seven additional 375px route-overflow checks**. Desktop, mobile, comparison and fund-page screenshots were visually inspected. No unhandled JavaScript error occurred in the harness.

The environment blocks browser URL navigation, so the browser harness supplied locally extracted data and a browser-storage shim. GitHub Pages deployment and its uploaded assets are verified; a live URL rendering, native persistent storage, actual phone/browser combinations, and every original binary download are not independently certified here. Do not describe these tests as full WCAG or cross-browser certification.

## Delivered

Unified light-only visual system; Explore/Compare/Saved navigation; semantic sortable desktop fund table; compact mobile cards; all six numerical metrics including 5Y CAGR; browser-local saved plans; up-to-three-plan comparisons with shareable URLs; fund-house and portfolio-coverage filters; holdings search; evidence-aware fund headers; clearer AMC documents, data and source-health views. Public refresh remains absent.

Core financial calculations and original evidence retention are unchanged. Reported-benchmark-first behavior, missing BSE TRI warnings, non-Growth return safeguards and previous-calendar-month portfolio semantics remain in the existing client/backend.

## Recommended next implementation

Start with **portfolio overlap** using comparable reporting dates and canonical ISINs; keep partial and mixed-period limitations explicit. Next, add **what changed since last review** for saved funds, followed by long-term consistency views and a validated multi-category selector. These are proposals, not shipped features. Detailed data requirements are in `docs/UI-HANDOFF.md`.
