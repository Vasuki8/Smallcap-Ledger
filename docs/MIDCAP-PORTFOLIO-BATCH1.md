# Mid Cap current portfolio evidence — batch 1

Prepared: 2026-10-07T23:18:47+00:00

Expected month-end: **2026-08-31** · targets: **7** · current evidence: **3** · failed: **4**.

| Family | AMC | As of | Positions observed | Scope | Complete? | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| Baroda BNP Paribas Mid Cap Fund | Baroda BNP Paribas Mutual Fund | 2026-08-31 | 5 | top_5 | false | https://www.barodabnpparibasmf.in/mutual-fund-schemes/equity-funds/baroda-bnp-paribas-mid-cap-fund/direct-growth |
| ITI Mid Cap Fund | ITI Mutual Fund | 2026-08-31 | 92 | digital_factsheet_named_holdings | false | https://www.itiamc.com/digitalfactsheet/August2026/innerpages/Mid-Cap.html |
| BANK OF INDIA MID CAP FUND | Bank of India Mutual Fund | 2026-08-31 | 10 | top_10 | false | https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund |

## Errors

- Canara Robeco Mid Cap Fund: Client error '403 This request is not authorized to perform this operation.' for url 'https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- Kotak Mid Cap Fund: First-party source does not contain the exact staged Mid Cap family identity
- DSP Midcap Fund: First-party source does not explicitly report current portfolio date 2026-08-31
- HDFC Mid Cap Fund: Client error '403 Forbidden' for url 'https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/regular'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403

## Notes

- This is read-only source evidence and does not insert Mid Cap portfolios or holdings.
- A covered family requires exact staged identity, the regulatory current month-end date, and at least five named holdings with reported weights.
- Every batch-1 snapshot remains complete=false. Full-page source scope does not become a complete portfolio without explicit 100% reconciliation.
