# Portfolio recovery queue

Prepared: 2026-09-25T04:49:12+00:00

**Read-only:** this queue ranks retained evidence only. It does not fetch sources, retry blocked hosts, estimate missing weights, or mutate portfolio data.

## Next actionable recovery target

**Axis Small Cap Fund** — `search_fuller_first_party_disclosure`

Search first-party Axis statutory/monthly portfolio disclosures for a constituent-level source that identifies holdings hidden by the current aggregate.

## Queue

Items: **8** · actionable now: **1** · stale partial: **1** · missing: **1**

| Rank | Fund | State | Action | Reporting date | Limitation | Exact source / recovery URL | Last retained evidence | Retry condition |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Axis Small Cap Fund | partial_current | search_fuller_first_party_disclosure | 2026-09-16 | undisclosed_constituents | https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct | fetch ok · 2026-09-24T22:11:56+00:00; source page Checked · 2026-09-24T22:12:17+00:00 | Search first-party Axis statutory/monthly portfolio disclosures for a constituent-level source that identifies holdings hidden by the current aggregate. |
| 2 | Union Small Cap Fund | missing | retry_after_source_change | Gap | upstream_source_unavailable | https://www.unionmf.com/about-us/downloads/monthly-portfolio | source page Gap · 2026-09-24T22:11:52+00:00 | Retry only after Union's official Downloads/portfolio transport is reachable from the production collection network or an exact first-party attachment is exposed. |
| 3 | Bajaj Finserv Small Cap Fund | partial_stale | retry_after_source_change | 2026-07-31 | named_subset_only | https://www.bajajamc.com/downloads | fetch ok · 2026-09-24T22:08:00+00:00; source page Checked · 2026-09-24T22:08:02+00:00 | Retry only when the AMC Downloads transport becomes usable from the production runner or an exact current monthly Small Cap attachment URL is exposed first-party. |
| 4 | Edelweiss Small Cap Fund | partial_current | retry_after_source_change | 2026-08-31 | named_subset_only | https://www.edelweissmf.com/statutory/portfolio-of-schemes | fetch ok · 2026-09-24T21:57:48+00:00; source page Limited · 2026-09-24T22:09:18+00:00 | Retry only when the statutory portfolio route/static application transport becomes reachable again or it exposes an exact monthly portfolio attachment. |
| 5 | ICICI Prudential Small Cap Fund | partial_current | retry_after_source_change | 2026-08-31 | undisclosed_constituents | https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip | fetch ok · 2026-09-24T21:54:56+00:00; source page Checked · 2026-09-24T21:55:13+00:00 | Retry only when the first-party monthly ZIP stops redirecting to an unresolved archive host or ICICI exposes the same archive through another working first-party route. |
| 6 | Bandhan Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | 2026-08-31 | non_numeric_source_weight | https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx | fetch ok · 2026-09-24T21:47:59+00:00; source page Limited · 2026-09-24T22:09:05+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for positions currently disclosed with a less-than-0.01% marker. |
| 7 | Sundaram Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | 2026-08-31 | non_numeric_source_weight | https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx | fetch ok · 2026-09-24T21:49:18+00:00; source page Limited · 2026-09-24T22:10:21+00:00 | Revisit only when the AMC publishes an exact numeric weight for the written-off holding currently disclosed only as less than 0.01%. |
| 8 | UTI Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | 2026-08-31 | non_numeric_source_weight | https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip?VersionId=HDm7fGngbSbB9olwo6wnStXgJC1XWJ16 | fetch ok · 2026-09-09T20:01:32+00:00; source page Checked · 2026-09-24T21:53:15+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for the censored tiny security and short-term deposits. |

## Notes

- Read-only prioritization: generating this queue never fetches sources or mutates portfolio data.
- Actionability score determines rank before stale/missing tie-breakers; retained position count is never a ranking input.
- retry_after_source_change entries should not be re-probed until new first-party transport/source evidence appears.
- requires_more_precise_amc_disclosure entries cannot be completed by estimating censored weights.
- A changed partial source that no longer matches a reviewed limitation is prioritized for explicit review.
