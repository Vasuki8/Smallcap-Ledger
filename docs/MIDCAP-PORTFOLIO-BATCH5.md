# Mid Cap current portfolio evidence — batch 5

Prepared: 2026-09-28T13:24:35+00:00

Expected month-end: **2026-08-31** · targets: **5** · recovered: **3** · failed: **2**.

| Family | AMC | As of | Positions | Scope | Complete? | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| JM Mid Cap Fund | JM Financial Mutual Fund | 2026-08-31 | 72 | structured_monthly_portfolio | false | https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Mid%20cap%20Fund%20-%20Aug%2031,%202026.xlsx |
| Mahindra Manulife Mid Cap Fund | Mahindra Manulife Mutual Fund | 2026-08-31 | 59 | factsheet_equity_only | false | https://www.mahindramanulife.com/digital-factsheet/August-2026/Equity-funds/Mid-Cap-Fund.html |
| Sundaram Mid Cap Fund | Sundaram Mutual Fund | 2026-08-31 | 79 | structured_monthly_portfolio | true | https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/MIDCAP.xlsx |

## Errors

- Kotak Mid Cap Fund: Factsheet lacks the exact staged scheme heading
- Invesco India Mid Cap Fund: Server error '502 Bad Gateway' for url 'https://www.invescomutualfund.com/api/CompleteMonthlyHoldings?year=2026&classification=equity'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502

## Notes

- Structured monthly workbooks are preferred for JM, Invesco and Sundaram where available.
- Kotak and Mahindra retain sector-reconciled equity-only evidence, explicitly partial.
- Portfolio dates come from their own disclosure, never from unrelated AUM or NAV dates.
- Every result requires exact staged family identity and the current regulatory month-end; no live records are written.
