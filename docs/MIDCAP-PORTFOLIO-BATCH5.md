# Mid Cap current portfolio evidence — batch 5

Prepared: 2026-10-11T22:26:19+00:00

Expected month-end: **2026-09-30** · targets: **8** · recovered: **3** · failed: **5**.

| Family | AMC | As of | Positions | Scope | Complete? | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| JM Mid Cap Fund | JM Financial Mutual Fund | 2026-09-30 | 73 | structured_monthly_portfolio | false | https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Mid%20cap%20Fund%20-%20Sep%2030,%202026.xlsx |
| Invesco India Mid Cap Fund | Invesco Mutual Fund | 2026-09-30 | 45 | structured_monthly_portfolio | true | https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/invesco-india-midcap-fund_sep_2026_equity.xlsx?sfvrsn=91a49ec2_0 |
| Samco Mid Cap Fund | Samco Mutual Fund | 2026-09-30 | 30 | publisher_all_holdings_html | false | https://www.samcomf.com/mutual-funds/samco-mid-cap-fund-direct-growth/midgg |

## Errors

- Kotak Mid Cap Fund: Factsheet lacks the exact staged scheme heading or reviewed alias
- Mahindra Manulife Mid Cap Fund: Factsheet data date does not uniquely prove current portfolio date 2026-09-30
- Sundaram Mid Cap Fund: No exact current Mid Cap portfolio sheet passed the existing structured parser
- Motilal Oswal Midcap Fund: No exact current Mid Cap portfolio sheet passed the existing structured parser
- BANDHAN MID CAP FUND: Bandhan Mid Cap disclosure API exposed no single exact current workbook

## Notes

- Structured monthly workbooks are preferred for JM, Invesco and Sundaram where available.
- Samco uses the publisher's current All Holdings table, but remains explicitly partial until structured 100% reconciliation is proven.
- Motilal Oswal uses the current fund page only to discover the exact dated monthly workbook, which is parsed through the existing structured parser.
- Bandhan uses the exact scheme/month CMS disclosure post and read-only finance API to resolve one official workbook, which is parsed through the existing structured parser.
- Kotak and Mahindra retain sector-reconciled equity-only evidence, explicitly partial.
- Portfolio dates come from their own disclosure, never from unrelated AUM or NAV dates.
- Every result requires exact staged family identity and the current regulatory month-end; no live records are written.
