# Mid Cap current portfolio evidence — batch 5

Prepared: 2026-10-05T22:55:44+00:00

Expected month-end: **2026-08-31** · targets: **8** · recovered: **6** · failed: **2**.

| Family | AMC | As of | Positions | Scope | Complete? | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| JM Mid Cap Fund | JM Financial Mutual Fund | 2026-08-31 | 72 | structured_monthly_portfolio | false | https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Mid%20cap%20Fund%20-%20Aug%2031,%202026.xlsx |
| Mahindra Manulife Mid Cap Fund | Mahindra Manulife Mutual Fund | 2026-08-31 | 59 | factsheet_equity_only | false | https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html |
| Invesco India Mid Cap Fund | Invesco Mutual Fund | 2026-08-31 | 43 | structured_monthly_portfolio | true | https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/mid-cap-fund00cbfe07eee8616aaa28ff00007d74af.xlsx?sfvrsn=eb229fc2_0 |
| Sundaram Mid Cap Fund | Sundaram Mutual Fund | 2026-08-31 | 79 | structured_monthly_portfolio | true | https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx |
| Motilal Oswal Midcap Fund | Motilal Oswal Mutual Fund | 2026-08-31 | 32 | structured_monthly_portfolio | true | https://www.motilaloswalmf.com/content/dam/motilal-mf/sheets/fund-csvs/Month_End_Portfolio_August_2026/YO07.xlsx |
| BANDHAN MID CAP FUND | Bandhan Mutual Fund | 2026-08-31 | 88 | structured_monthly_portfolio | false | https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/31f832d6-bandhan-mid-cap-fund_64601504-9a02-4098-a032-61e6fceefec9_31-august-2026.xlsx |

## Errors

- Kotak Mid Cap Fund: Factsheet lacks the exact staged scheme heading or reviewed alias
- Samco Mid Cap Fund: The read operation timed out

## Notes

- Structured monthly workbooks are preferred for JM, Invesco and Sundaram where available.
- Samco uses the publisher's current All Holdings table, but remains explicitly partial until structured 100% reconciliation is proven.
- Motilal Oswal uses the current fund page only to discover the exact dated monthly workbook, which is parsed through the existing structured parser.
- Bandhan uses the exact scheme/month CMS disclosure post and read-only finance API to resolve one official workbook, which is parsed through the existing structured parser.
- Kotak and Mahindra retain sector-reconciled equity-only evidence, explicitly partial.
- Portfolio dates come from their own disclosure, never from unrelated AUM or NAV dates.
- Every result requires exact staged family identity and the current regulatory month-end; no live records are written.
