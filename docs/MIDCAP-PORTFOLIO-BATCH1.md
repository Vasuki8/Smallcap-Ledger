# Mid Cap current portfolio evidence — batch 1

Prepared: 2026-10-11T22:24:33+00:00

Expected month-end: **2026-09-30** · targets: **7** · current evidence: **1** · failed: **6**.

| Family | AMC | As of | Positions observed | Scope | Complete? | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| Baroda BNP Paribas Mid Cap Fund | Baroda BNP Paribas Mutual Fund | 2026-09-30 | 5 | top_5 | false | https://www.barodabnpparibasmf.in/mutual-fund-schemes/equity-funds/baroda-bnp-paribas-mid-cap-fund/direct-growth |

## Errors

- Canara Robeco Mid Cap Fund: Client error '403 This request is not authorized to perform this operation.' for url 'https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- Kotak Mid Cap Fund: First-party source does not contain the exact staged Mid Cap family identity
- DSP Midcap Fund: Only 0 named current holdings were visible; need at least 5
- HDFC Mid Cap Fund: Client error '403 Forbidden' for url 'https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/regular'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- ITI Mid Cap Fund: First-party source does not explicitly report current portfolio date 2026-09-30
- BANK OF INDIA MID CAP FUND: First-party source does not explicitly report current portfolio date 2026-09-30

## Notes

- This is read-only source evidence and does not insert Mid Cap portfolios or holdings.
- A covered family requires exact staged identity, the regulatory current month-end date, and at least five named holdings with reported weights.
- Every batch-1 snapshot remains complete=false. Full-page source scope does not become a complete portfolio without explicit 100% reconciliation.
