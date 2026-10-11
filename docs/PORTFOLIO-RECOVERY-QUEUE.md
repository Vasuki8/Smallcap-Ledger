# Portfolio recovery queue

Prepared: 2026-10-11T22:44:56+00:00

**Read-only:** this queue ranks retained evidence only. It does not fetch sources, retry blocked hosts, estimate missing weights, or mutate portfolio data.

## Next actionable recovery target

**Jm Small Cap Fund** — `review_changed_partial_source`

Review the changed first-party source and classify its exact disclosure boundary before any further recovery work.

## Queue

Items: **10** · actionable now: **4** · source changes: **1** · stale partial: **3** · missing: **1**

| Rank | Fund | State | Action | Source change | Reporting date | Limitation | Exact source / recovery URL | Last retained evidence | Retry condition |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Jm Small Cap Fund | partial_current | review_changed_partial_source | none | 2026-09-30 | partial_reason_unclassified | https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Small%20Cap%20Fund%20-%20Sep%2030%2C%202026.xlsx | fetch ok · 2026-10-11T22:29:21+00:00; source page Limited · 2026-10-11T22:34:57+00:00 | Review the changed first-party source and classify its exact disclosure boundary before any further recovery work. |
| 2 | Tata Small Cap Fund | partial_current | review_changed_partial_source | none | 2026-09-30 | partial_reason_unclassified | https://betacms.tatamutualfund.com/system/files/2026-10/Monthly%20Portfolio%20as%20on%2030th%20September%202026.xlsx | fetch ok · 2026-10-11T22:30:54+00:00; source page Checked · 2026-10-11T22:38:23+00:00 | Review the changed first-party source and classify its exact disclosure boundary before any further recovery work. |
| 3 | Trustmf Small Cap Fund | partial_current | review_changed_partial_source | none | 2026-09-30 | partial_reason_unclassified | https://trustmf.com/Content/2026/10/Monthly%20Port_20261009132916.xlsx | fetch ok · 2026-10-11T22:31:07+00:00; source page Limited · 2026-10-11T22:35:44+00:00 | Review the changed first-party source and classify its exact disclosure boundary before any further recovery work. |
| 4 | ICICI Prudential Small Cap Fund | partial_current | review_source_change | new_first_party_portfolio_document | 2026-09-30 | partial_reason_unclassified | https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip | fetch ok · 2026-10-11T22:29:41+00:00; source page Checked · 2026-10-11T22:38:35+00:00 | Review the newly retained first-party source/transport evidence before retrying portfolio recovery; do not assume the prior blocker is resolved. |
| 5 | Union Small Cap Fund | missing | retry_after_source_change | none | Gap | upstream_source_unavailable | https://www.unionmf.com/about-us/downloads/monthly-portfolio | source page Gap · 2026-10-11T22:39:37+00:00 | Retry only after Union's official Downloads/portfolio transport is reachable from the production collection network or an exact first-party attachment is exposed. |
| 6 | Bajaj Finserv Small Cap Fund | partial_stale | retry_after_source_change | none | 2026-07-31 | named_subset_only | https://www.bajajamc.com/downloads | fetch ok · 2026-10-11T22:34:00+00:00; source page Checked · 2026-10-11T22:34:00+00:00 | Retry only when the AMC Downloads transport becomes usable from the production runner or an exact current monthly Small Cap attachment URL is exposed first-party. |
| 7 | Edelweiss Small Cap Fund | partial_stale | retry_after_source_change | none | 2026-08-31 | named_subset_only | https://www.edelweissmf.com/statutory/portfolio-of-schemes | fetch ok · 2026-10-05T23:03:03+00:00; source page Gap · 2026-10-11T22:37:06+00:00 | Retry only when the statutory portfolio route/static application transport becomes reachable again or it exposes an exact monthly portfolio attachment. |
| 8 | Sundaram Small Cap Fund | partial_stale | requires_more_precise_amc_disclosure | none | 2026-08-31 | non_numeric_source_weight | https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx | fetch ok · 2026-10-08T23:41:50+00:00; source page Checked · 2026-10-11T22:41:24+00:00 | Revisit only when the AMC publishes an exact numeric weight for the written-off holding currently disclosed only as less than 0.01%. |
| 9 | Bandhan Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | none | 2026-09-30 | partial_reason_unclassified | https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/10/96969d23-bandhan-small-cap-fund-30-september-2026.xlsx | fetch ok · 2026-10-11T22:30:33+00:00; source page Checked · 2026-10-11T22:38:32+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for positions currently disclosed with a less-than-0.01% marker. |
| 10 | UTI Small Cap Fund | partial_current | requires_more_precise_amc_disclosure | none | 2026-09-30 | partial_reason_unclassified | https://d3ce1o48hc5oli.cloudfront.net/static/generic-zip/Oct-26/FW__UTI_MF_SCHEME_PORTFOLIOS_-_30.09.2026_.zip | fetch ok · 2026-10-11T22:30:28+00:00; source page Checked · 2026-10-11T22:29:23+00:00 | Revisit only when the AMC publishes exact numeric NAV weights for the censored tiny security and short-term deposits. |

## Notes

- Read-only prioritization: generating this queue never fetches sources or mutates portfolio data.
- Actionability score determines rank before stale/missing tie-breakers; retained position count is never a ranking input.
- retry_after_source_change entries should not be re-probed until source_change_watch.changed becomes true from newly retained first-party evidence.
- requires_more_precise_amc_disclosure entries cannot be completed by estimating censored weights.
- A changed partial source that no longer matches a reviewed limitation is prioritized for explicit review.
