# Mid Cap structured current portfolio evidence — batch 2

Prepared: 2026-10-11T22:24:37+00:00

Expected month-end: **2026-09-30** · targets: **3** · recovered: **1** · failed: **2**.

| Family | AMC | As of | Positions | Complete? | Source |
| --- | --- | --- | ---: | --- | --- |
| DSP Midcap Fund | DSP Mutual Fund | 2026-09-30 | 65 | false | https://www.dspim.com/media/pages/mandatory-disclosures/portfolio-disclosures/7737577fda-1791551248/dsp-monthend-portfolio-as-on-30-september-2026.zip |

## Errors

- HDFC Mid Cap Fund: Client error '403 Forbidden' for url 'https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- Helios Mid Cap Fund: Helios monthly workbook filename does not prove the exact scheme and date

## Notes

- This audit downloads official current month-end disclosure files but performs no portfolio, holding, metric, document or fetch writes.
- All sources are parsed through the existing exact-family structured portfolio parser in memory.
- Completeness is reported exactly as the parser proves it; no balancing cash or missing rows are invented.
