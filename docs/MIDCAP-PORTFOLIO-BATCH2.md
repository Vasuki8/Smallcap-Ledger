# Mid Cap structured current portfolio evidence — batch 2

Prepared: 2026-10-05T21:34:39+00:00

Expected month-end: **2026-08-31** · targets: **3** · recovered: **3** · failed: **0**.

| Family | AMC | As of | Positions | Complete? | Source |
| --- | --- | --- | ---: | --- | --- |
| HDFC Mid Cap Fund | HDFC Mutual Fund | 2026-08-31 | 81 | true | https://files.hdfcfund.com/s3fs-public/2026-09/Monthly%20HDFC%20Mid%20Cap%20Fund%20-%2031%20August%202026.xlsx |
| DSP Midcap Fund | DSP Mutual Fund | 2026-08-31 | 65 | false | https://www.dspim.com/media/pages/mandatory-disclosures/portfolio-disclosures/8a6dbe504f-1789452169/dsp-monthend-portfolio-as-on-31-aug-2026.zip |
| Helios Mid Cap Fund | Helios Mutual Fund | 2026-08-31 | 74 | true | https://www.heliosmf.in/wp-content/uploads/2026/09/helios-mid-cap-fund-monthly-portfolio-as-on-31st-august-2026.xlsx |

## Notes

- This audit downloads official current month-end disclosure files but performs no portfolio, holding, metric, document or fetch writes.
- All sources are parsed through the existing exact-family structured portfolio parser in memory.
- Completeness is reported exactly as the parser proves it; no balancing cash or missing rows are invented.
