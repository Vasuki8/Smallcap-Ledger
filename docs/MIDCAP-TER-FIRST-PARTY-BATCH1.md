# Mid Cap first-party TER recovery batch 1

Prepared: 2026-09-28T19:57:31+00:00

Targets: **7** · recovered: **7** · failed: **0**.

| Family | AMC | Status | As of | Direct TER | Regular TER | Source | Identity |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| Canara Robeco Mid Cap Fund | Canara Robeco Mutual Fund | recovered | 2026-09-28 | 0.8600% | 2.1100% | https://www.canararobeco.com/wp-json/ter/v1/records?from_date=2026-09-14&to_date=2026-09-28 | scheme_name=Canara Robeco Mid Cap Fund, scheme_code=MD |
| HSBC Midcap Fund | HSBC Mutual Fund | recovered | 2026-09-27 | 1.1500% | 2.2100% | https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx | scheme_name=HSBC Midcap Fund, scheme_code=HEMCPF, nsdl_scheme_code=LTMF/O/E/MIF/04/06/0006 |
| ICICI Prudential Mid Cap Fund | ICICI Prudential Mutual Fund | recovered | 2026-09-27 | 1.0900% | 1.8300% | https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx | scheme_name=ICICI Prudential Mid Cap Fund |
| Invesco India Mid Cap Fund | Invesco Mutual Fund | recovered | 2026-09-27 | 0.7800% | 1.8800% | https://www.invescomutualfund.com/api/TotalExpenseRatioOfMutualFundSchemePolicy/GetTERExpenseData?title=Invesco+India+Mid+Cap+Fund&fincialYear=2026&month=9 | scheme_name=Invesco India Mid Cap Fund, nsdl_scheme_code=INVM/O/E/MIF/07/01/0006 |
| JM Mid Cap Fund | JM Financial Mutual Fund | recovered | 2026-09-28 | 0.9500% | 2.4700% | https://jmmfapi.jmfinancialmf.com/api/GetTerPageLatest | scheme_name=JM Mid Cap Fund, scheme_code=MD, nsdl_scheme_code=JMFI/O/E/MIF/21/09/0014 |
| Mahindra Manulife Mid Cap Fund | Mahindra Manulife Mutual Fund | recovered | 2026-09-28 | 0.7500% | 2.0200% | https://www.mahindramanulife.com/uploads/download/6d61db84-f11d-4987-b7a6-929a71d43967.xlsx | scheme_name=Mahindra Manulife Mid Cap Fund, nsdl_scheme_code=MAHM/O/E /MIF/17/11/0006 |
| Mirae Asset Midcap Fund | Mirae Asset Mutual Fund | recovered | 2026-09-27 | 0.9600% | 2.0200% | https://www.miraeassetmf.co.in/DailyUploads/TotalExpenseRatio/IN_MF_EXPENSE_RATIO_SEBI_V3_27092026.xls | scheme_name=Mirae Asset Midcap Fund, nsdl_scheme_code=MIRA/O/E/MIF/19/05/0015 |

## Notes

- All source requests are read-only and archive=False; this audit does not insert metrics, documents or fetch records.
- A result requires the first-party source to contain the staged Mid Cap family identity and a complete Regular/Direct TER pair.
- No Small Cap TER value, NSDL code or scheme code is reused for a Mid Cap fund.
