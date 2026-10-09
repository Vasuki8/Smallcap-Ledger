# Mid Cap benchmark identity audit — batch 1

Prepared: 2026-10-09T22:51:54+00:00

Targets: **12** · recovered: **8** · failed: **4** · staged families: **34**.

| Family | AMC | Primary benchmark | Source data as of | Source |
| --- | --- | --- | --- | --- |
| Kotak Mid Cap Fund | Kotak Mahindra Mutual Fund | NIFTY Midcap 150 TRI | Observed current page | https://www.kotakmf.com/factsheet/August_2026/kotak/EMERGING-EQUITY-SCHEME.html |
| The Wealth Company Mid Cap Fund | The Wealth Company Mutual Fund | NIFTY Midcap 150 TRI | Observed current page | https://www.wealthcompanyamc.in/our-funds/fund/the-wealth-company-mid-cap-fund/154479/ |
| BANK OF INDIA MID CAP FUND | Bank of India Mutual Fund | Nifty Midcap 150 Total Return Index | Observed current page | https://www.boimf.in/products/equity-funds/bank-of-india-mid-cap-fund |
| PGIM India Midcap Fund | PGIM India Mutual Fund | Nifty Midcap 150 TRI | 2026-09-30 | https://www.pgimindia.com/mutual-funds/equity-funds/midcap-fund |
| DSP Midcap Fund | DSP Mutual Fund | Nifty Midcap 150 TRI | Observed current page | https://www.dspim.com/invest/mutual-fund-schemes/equity-funds/mid-cap-fund/dspsm-regular-growth |
| Helios Mid Cap Fund | Helios Mutual Fund | NIFTY Midcap 150 Total Return Index | Observed current page | https://www.heliosmf.in/helios-mid-cap-fund/ |
| Nippon India Growth Mid Cap Fund | Nippon India Mutual Fund | Nifty Midcap 150 TRI | Observed current page | https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Growth-Mid-Cap-Fund.aspx?rmfsource=nimfinvesteasy |
| Taurus Mid Cap Fund | Taurus Mutual Fund | Nifty Midcap 150 TRI | Observed current page | https://www.taurusmutualfund.com/node/557 |

## Errors

- Canara Robeco Mid Cap Fund: Client error '403 This request is not authorized to perform this operation.' for url 'https://digitalassets.canararobeco.com/digital-factsheet/2026/august/Scheme/MID-CAP.html'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- Franklin India Mid Cap Fund: First-party page does not contain the exact staged Mid Cap family identity
- UTI - Mid Cap Fund: First-party page does not contain the exact staged Mid Cap family identity
- HDFC Mid Cap Fund: Client error '403 Forbidden' for url 'https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/regular'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403

## Notes

- This is read-only source evidence; it does not insert Mid Cap benchmark metrics.
- Every recovered benchmark requires the exact staged family identity on the first-party page and an explicit Benchmark label nearby.
- The publisher's benchmark wording is retained; TRI is never inferred when the source does not state it.
