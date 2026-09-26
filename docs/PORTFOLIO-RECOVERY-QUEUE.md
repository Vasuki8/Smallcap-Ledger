# Portfolio recovery queue

Prepared: 2026-09-26T00:48:01+00:00

**Read-only:** this queue ranks retained evidence only. It does not fetch sources, retry blocked hosts, estimate missing weights, or mutate portfolio data.

## Queue

Items: **7** · actionable now: **0** · source changes: **0** · stale partial: **1** · missing: **1**

| Rank | Fund | State | Action | Source change | Reporting date | Limitation | Exact source / recovery URL | Last retained evidence | Retry condition |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Union Small Cap Fund | missing | retry_after_source_change | none | Gap | upstream_source_unavailable | https://www.unionmf.com/about-us/downloads/monthly-portfolio | source page Gap · 2026-09-25T22:13:23+00:00 | Retry only after Union's official Downloads/portfolio transport is reachable from the production collection network or an exact first-party attachment is exposed. |
| 2 | Bajaj Finserv Small Cap Fund | partial_stale | retry_after_source_change | none | 2026-07-31 | named_subset_only | https://www.bajajamc.com/downloads | fetch ok · 2026-09-25T22:08:55+00:00; source page Checked · 2026-09-25T22:09:01+00:00 | Retry only when the AMC Downloads transport becomes usable from the production runner or an exact current monthly Small Cap attachment URL is exposed first-party. |
| 3 | Edelweiss Small Cap Fund | partial_current | retry_after_source_change | none | 2026-08-31 | named_subset_only | https://www.edelweissmf.com/statutory/portfolio-of-schemes | fetch ok · 2026-09-25T22:00:45+00:00; source page Limited · 2026-09-25T22:10:36+00:00 | Retry only when the statutory portfolio route/static application transport becomes reachable again or it exposes an exact monthly portfolio attachment. |
| 4 | ICICI Prudential Small Cap Fund | partial_current | retry_after_source_change | none | 2026-08-31 | undisclosed_constituents | https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip | fetch ok · 2026-09-25T21:58:47+00:00; source page Checked · 2026-09-25T21:59:31+00:00 | Retry only when the first-party monthly ZIP stops redirecting to an unresolved archive host or ICICI exposes the same archive through another working first-party route. |
| 5 | Bandhan Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | none | 2026-08-31 | non_numeric_source_weight | https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx | fetch ok · 2026-09-25T21:52:53+00:00; source page Limited · 2026-09-25T22:10:28+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for positions currently disclosed with a less-than-0.01% marker. |
| 6 | Sundaram Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | none | 2026-08-31 | non_numeric_source_weight | https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx | fetch ok · 2026-09-25T21:54:39+00:00; source page Limited · 2026-09-25T22:11:02+00:00 | Revisit only when the AMC publishes an exact numeric weight for the written-off holding currently disclosed only as less than 0.01%. |
| 7 | UTI Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | none | 2026-08-31 | non_numeric_source_weight | https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip?VersionId=HDm7fGngbSbB9olwo6wnStXgJC1XWJ16 | fetch ok · 2026-09-09T20:01:32+00:00; source page Checked · 2026-09-25T21:55:47+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for the censored tiny security and short-term deposits. |

## Notes

- Read-only prioritization: generating this queue never fetches sources or mutates portfolio data.
- Actionability score determines rank before stale/missing tie-breakers; retained position count is never a ranking input.
- retry_after_source_change entries should not be re-probed until source_change_watch.changed becomes true from newly retained first-party evidence.
- requires_more_precise_amc_disclosure entries cannot be completed by estimating censored weights.
- A changed partial source that no longer matches a reviewed limitation is prioritized for explicit review.
