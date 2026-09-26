# Historical performance and benchmark coverage audit

Prepared: 2026-09-26T16:32:19+00:00

**Read-only:** retained NAV/benchmark evidence only; no forward-fill, return fabrication, source fetch or UI change.

## Summary

- Plans: **143**; Growth plans eligible for displayed returns: **72**.
- Reported benchmark identity families: **36 / 36**.
- Explicit reported TRI identities on Growth plans: **72**.
- Growth plans with the relevant reported TRI series and at least two exact overlapping dates: **52**.
- Growth plans with their reported TRI series retained: **52**; reported TRI series missing: **20**.
- Growth plans with at least one retained explicit-only alternate comparison: **20**.
- Verified official-history NAV gaps: **5 intervals across 2 Growth plans**; retained as evidence, not actionable missing-value repairs.

| Horizon | NAV return eligible Growth plans | Relevant benchmark overlap eligible Growth plans |
| --- | ---: | ---: |
| 1Y | 62 | 42 |
| 3Y | 48 | 32 |
| 5Y | 44 | 30 |

## Repair priorities

| Priority | Repair | Affected funds | Affected Growth plans | Reason |
| ---: | --- | ---: | ---: | --- |
| 1 | collect_bse_250_smallcap_tri | 10 | 20 | Funds explicitly report BSE 250 SmallCap TRI, but no matching historical TRI series is retained; the first-party daily-history route is currently subscription-distributed. |

### Affected funds

- **collect_bse_250_smallcap_tri:** Aditya Birla Sun Life Small Cap Fund, Bajaj Finserv Small Cap Fund, Bandhan Small Cap Fund, DSP Small Cap Fund, HDFC Small Cap Fund, Invesco India Small Cap Fund, Mahindra Manulife Small Cap Fund, Quantum Small Cap Fund, SBI Small Cap Fund, Union Small Cap Fund

## Verified official-history NAV gaps

These raw date gaps remain visible, but current official histories do not supply intermediate NAV observations. No value is interpolated or inferred.

- **Aditya Birla Sun Life Small Cap Fund · Regular · Growth · 105804**: 2010-05-31 → 2010-06-08 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **Aditya Birla Sun Life Small Cap Fund · Regular · IDCW · 105805**: 2010-05-31 → 2010-06-08 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2007-08-08 → 2007-08-16 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2008-08-27 → 2008-09-04 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2010-03-17 → 2010-03-25 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2010-04-07 → 2010-04-15 (8 calendar days) · verified_official_history_gap · verified 2026-09-25

## Per-plan audit

| Fund / plan | NAV range / obs | 1Y | 3Y | 5Y | Reported benchmark | Reported TRI series | Exact overlap | Issues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Abakkus Small Cap Fund · Direct · Growth · 154215 | 2026-03-20 → 2026-09-25 · 129 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-20 → 2026-09-25 · 128 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Abakkus Small Cap Fund · Regular · Growth · 154214 | 2026-03-20 → 2026-09-25 · 129 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-20 → 2026-09-25 · 128 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Aditya Birla Sun Life Small Cap Fund · Direct · Growth · 119556 | 2013-01-07 → 2026-09-25 · 3376 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Aditya Birla Sun Life Small Cap Fund · Direct · IDCW · 119557 | 2013-01-02 → 2026-09-25 · 3379 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Aditya Birla Sun Life Small Cap Fund · Regular · Growth · 105804 | 2007-05-31 → 2026-09-25 · 4751 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Aditya Birla Sun Life Small Cap Fund · Regular · IDCW · 105805 | 2007-05-31 → 2026-09-25 · 4751 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Axis Small Cap Fund · Direct · Growth · 125354 | 2013-12-05 → 2026-09-25 · 3159 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-25 · 3148 | none |
| Axis Small Cap Fund · Direct · IDCW · 125351 | 2013-12-05 → 2026-09-25 · 3159 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-25 · 3148 | none |
| Axis Small Cap Fund · Regular · Growth · 125350 | 2013-12-05 → 2026-09-25 · 3159 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-25 · 3148 | none |
| Axis Small Cap Fund · Regular · IDCW · 125352 | 2013-12-05 → 2026-09-25 · 3159 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-25 · 3148 | none |
| Bajaj Finserv Small Cap Fund · Direct · Growth · 153612 | 2025-07-22 → 2026-09-25 · 291 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing |
| Bajaj Finserv Small Cap Fund · Direct · IDCW · 153611 | 2025-07-22 → 2026-09-25 · 291 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bajaj Finserv Small Cap Fund · Regular · Growth · 153609 | 2025-07-22 → 2026-09-25 · 291 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing |
| Bajaj Finserv Small Cap Fund · Regular · IDCW · 153610 | 2025-07-22 → 2026-09-25 · 291 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bandhan Small Cap Fund · Direct · Growth · 147946 | 2020-02-26 → 2026-09-25 · 1632 | yes | yes | yes | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bandhan Small Cap Fund · Direct · IDCW · 147943 | 2020-02-26 → 2026-09-25 · 1632 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bandhan Small Cap Fund · Regular · Growth · 147944 | 2020-02-26 → 2026-09-25 · 1632 | yes | yes | yes | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bandhan Small Cap Fund · Regular · IDCW · 147945 | 2020-02-26 → 2026-09-25 · 1632 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Bank Of India Small Cap Fund · Direct · Growth · 145678 | 2018-12-27 → 2026-09-25 · 1910 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-25 · 1907 | none |
| Bank Of India Small Cap Fund · Direct · IDCW · 145675 | 2018-12-27 → 2026-09-25 · 1910 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-25 · 1907 | none |
| Bank Of India Small Cap Fund · Regular · Growth · 145677 | 2018-12-27 → 2026-09-25 · 1910 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-25 · 1907 | none |
| Bank Of India Small Cap Fund · Regular · IDCW · 145676 | 2018-12-27 → 2026-09-25 · 1910 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-25 · 1907 | none |
| Baroda Bnp Paribas Small Cap Fund · Direct · Growth · 152128 | 2023-11-01 → 2026-09-25 · 715 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-25 · 712 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Baroda Bnp Paribas Small Cap Fund · Direct · IDCW · 152129 | 2023-11-01 → 2026-09-25 · 715 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-25 · 712 | none |
| Baroda Bnp Paribas Small Cap Fund · Regular · Growth · 152130 | 2023-11-01 → 2026-09-25 · 715 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-25 · 712 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Baroda Bnp Paribas Small Cap Fund · Regular · IDCW · 152131 | 2023-11-01 → 2026-09-25 · 715 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-25 · 712 | none |
| Canara Robeco Small Cap Fund · Direct · Growth · 146130 | 2019-02-19 → 2026-09-25 · 1872 | yes | yes | yes | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-25 · 1869 | none |
| Canara Robeco Small Cap Fund · Direct · IDCW · 146131 | 2019-02-19 → 2026-09-25 · 1872 | n/a | n/a | n/a | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-25 · 1869 | none |
| Canara Robeco Small Cap Fund · Regular · Growth · 146127 | 2019-02-19 → 2026-09-25 · 1872 | yes | yes | yes | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-25 · 1869 | none |
| Canara Robeco Small Cap Fund · Regular · IDCW · 146128 | 2019-02-19 → 2026-09-25 · 1872 | n/a | n/a | n/a | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-25 · 1869 | none |
| DSP Small Cap Fund · Direct · Growth · 119212 | 2013-01-02 → 2026-09-25 · 3382 | yes | yes | yes | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| DSP Small Cap Fund · Direct · IDCW · 119213 | 2013-01-03 → 2026-09-25 · 3381 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| DSP Small Cap Fund · Regular · Growth · 105989 | 2007-06-20 → 2026-09-25 · 4213 | yes | yes | yes | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| DSP Small Cap Fund · Regular · IDCW · 113153 | 2010-08-03 → 2026-09-25 · 3980 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Edelweiss Small Cap Fund · Direct · Growth · 146196 | 2019-02-14 → 2026-09-25 · 1877 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-25 · 1872 | none |
| Edelweiss Small Cap Fund · Direct · IDCW · 146197 | 2019-02-14 → 2026-09-25 · 1877 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-25 · 1872 | none |
| Edelweiss Small Cap Fund · Regular · Growth · 146193 | 2019-02-14 → 2026-09-25 · 1877 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-25 · 1872 | none |
| Edelweiss Small Cap Fund · Regular · IDCW · 146194 | 2019-02-14 → 2026-09-25 · 1877 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-25 · 1872 | none |
| Franklin India Small Cap Fund · Direct · Growth · 118525 | 2013-01-01 → 2026-09-25 · 3381 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-01 → 2026-09-25 · 3378 | none |
| Franklin India Small Cap Fund · Direct · IDCW · 118524 | 2013-01-01 → 2026-09-25 · 3381 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-01 → 2026-09-25 · 3378 | none |
| Franklin India Small Cap Fund · Regular · Growth · 103360 | 2006-04-03 → 2026-09-25 · 5043 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5040 | none |
| Franklin India Small Cap Fund · Regular · IDCW · 103361 | 2006-04-03 → 2026-09-25 · 5043 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5040 | none |
| Groww Small Cap Fund · Direct · Growth · 154063 | 2026-02-02 → 2026-09-25 · 162 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-25 · 161 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Groww Small Cap Fund · Direct · IDCW · 154104 | 2026-02-02 → 2026-09-25 · 162 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-25 · 161 | none |
| Groww Small Cap Fund · Regular · Growth · 154102 | 2026-02-02 → 2026-09-25 · 162 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-25 · 161 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Groww Small Cap Fund · Regular · IDCW · 154103 | 2026-02-02 → 2026-09-25 · 162 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-25 · 161 | none |
| HDFC Small Cap Fund · Direct · Growth · 130503 | 2014-06-30 → 2026-09-25 · 3012 | yes | yes | yes | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| HDFC Small Cap Fund · Direct · IDCW · 130504 | 2014-06-30 → 2026-09-25 · 3012 | n/a | n/a | n/a | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| HDFC Small Cap Fund · Regular · Growth · 130502 | 2014-06-30 → 2026-09-25 · 3012 | yes | yes | yes | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| HDFC Small Cap Fund · Regular · IDCW · 130501 | 2014-06-30 → 2026-09-25 · 3012 | n/a | n/a | n/a | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| HSBC Small Cap Fund · Unspecified · Other · 151130 | 2022-11-28 → 2026-09-25 · 944 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-25 · 941 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151131 | 2022-11-28 → 2026-09-25 · 944 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-25 · 941 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151132 | 2022-11-28 → 2026-09-25 · 944 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-25 · 941 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151133 | 2022-11-28 → 2026-09-25 · 944 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-25 · 941 | none |
| Helios Small Cap Fund · Direct · Growth · 153912 | 2025-11-28 → 2026-09-25 · 205 | no | no | no | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-25 · 204 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Helios Small Cap Fund · Direct · IDCW · 153910 | 2025-11-28 → 2026-09-25 · 205 | n/a | n/a | n/a | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-25 · 204 | none |
| Helios Small Cap Fund · Regular · Growth · 153909 | 2025-11-28 → 2026-09-25 · 205 | no | no | no | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-25 · 204 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Helios Small Cap Fund · Regular · IDCW · 153911 | 2025-11-28 → 2026-09-25 · 205 | n/a | n/a | n/a | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-25 · 204 | none |
| ICICI Prudential Small Cap Fund · Direct · Growth · 120591 | 2013-01-03 → 2026-09-25 · 3351 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-25 · 3348 | none |
| ICICI Prudential Small Cap Fund · Direct · IDCW · 120870 | 2013-01-08 → 2026-09-25 · 3348 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-08 → 2026-09-25 · 3345 | none |
| ICICI Prudential Small Cap Fund · Institutional · Growth · 106821 | 2007-10-19 → 2020-04-24 · 3016 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2020-04-24 · 3016 | none |
| ICICI Prudential Small Cap Fund · Regular · Growth · 106823 | 2007-10-19 → 2026-09-25 · 4602 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2026-09-25 · 4599 | none |
| ICICI Prudential Small Cap Fund · Regular · IDCW · 106822 | 2007-10-19 → 2026-09-25 · 4602 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2026-09-25 · 4599 | none |
| Invesco India Small Cap Fund · Direct · Growth · 145137 | 2018-11-02 → 2026-09-25 · 1945 | yes | yes | yes | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Invesco India Small Cap Fund · Direct · IDCW · 145138 | 2018-11-02 → 2026-09-25 · 1945 | n/a | n/a | n/a | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Invesco India Small Cap Fund · Regular · Growth · 145139 | 2018-11-02 → 2026-09-25 · 1945 | yes | yes | yes | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Invesco India Small Cap Fund · Regular · IDCW · 145140 | 2018-11-02 → 2026-09-25 · 1945 | n/a | n/a | n/a | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Iti Small Cap Fund · Direct · Growth · 147919 | 2020-02-19 → 2026-09-25 · 1627 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-25 · 1625 | none |
| Iti Small Cap Fund · Direct · IDCW · 147917 | 2020-02-19 → 2026-09-25 · 1627 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-25 · 1625 | none |
| Iti Small Cap Fund · Regular · Growth · 147920 | 2020-02-19 → 2026-09-25 · 1627 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-25 · 1625 | none |
| Iti Small Cap Fund · Regular · IDCW · 147918 | 2020-02-19 → 2026-09-25 · 1627 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-25 · 1625 | none |
| Jm Small Cap Fund · Direct · Growth · 152614 | 2024-06-24 → 2026-09-25 · 559 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-25 · 557 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Jm Small Cap Fund · Direct · IDCW · 152615 | 2024-06-24 → 2026-09-25 · 559 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-25 · 557 | none |
| Jm Small Cap Fund · Regular · Growth · 152612 | 2024-06-24 → 2026-09-25 · 559 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-25 · 557 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Jm Small Cap Fund · Regular · IDCW · 152613 | 2024-06-24 → 2026-09-25 · 559 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-25 · 557 | none |
| Kotak Small Cap Fund · Direct · Growth · 120164 | 2013-01-02 → 2026-09-25 · 3380 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-25 · 3377 | none |
| Kotak Small Cap Fund · Direct · IDCW · 120163 | 2013-01-02 → 2026-09-25 · 3380 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-25 · 3377 | none |
| Kotak Small Cap Fund · Regular · Growth · 102875 | 2006-04-03 → 2026-09-25 · 5043 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5040 | none |
| Kotak Small Cap Fund · Regular · IDCW · 102874 | 2006-04-03 → 2026-09-25 · 5043 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5040 | none |
| LIC Mf Small Cap Fund · Direct · Growth · 152004 | 2023-07-31 → 2026-09-25 · 777 | yes | yes | no | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-25 · 774 | nav_5y_return_unavailable, benchmark_5y_overlap_unavailable |
| LIC Mf Small Cap Fund · Direct · IDCW · 152005 | 2023-07-31 → 2026-09-25 · 777 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-25 · 774 | none |
| LIC Mf Small Cap Fund · Regular · Growth · 152003 | 2023-07-31 → 2026-09-25 · 777 | yes | yes | no | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-25 · 774 | nav_5y_return_unavailable, benchmark_5y_overlap_unavailable |
| LIC Mf Small Cap Fund · Regular · IDCW · 152006 | 2023-07-31 → 2026-09-25 · 777 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-25 · 774 | none |
| Mahindra Manulife Small Cap Fund · Direct · Growth · 150915 | 2022-12-14 → 2026-09-25 · 932 | yes | yes | no | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_5y_return_unavailable, reported_tri_series_missing |
| Mahindra Manulife Small Cap Fund · Direct · IDCW · 150913 | 2022-12-14 → 2026-09-25 · 932 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Mahindra Manulife Small Cap Fund · Regular · Growth · 150912 | 2022-12-14 → 2026-09-25 · 932 | yes | yes | no | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_5y_return_unavailable, reported_tri_series_missing |
| Mahindra Manulife Small Cap Fund · Regular · IDCW · 150914 | 2022-12-14 → 2026-09-25 · 932 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Mirae Asset Small Cap Fund · Direct · Growth · 153196 | 2025-02-03 → 2026-09-25 · 406 | yes | no | no | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-25 · 404 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Mirae Asset Small Cap Fund · Direct · IDCW · 153197 | 2025-02-03 → 2026-09-25 · 406 | n/a | n/a | n/a | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-25 · 404 | none |
| Mirae Asset Small Cap Fund · Regular · Growth · 153198 | 2025-02-03 → 2026-09-25 · 406 | yes | no | no | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-25 · 404 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Mirae Asset Small Cap Fund · Regular · IDCW · 153199 | 2025-02-03 → 2026-09-25 · 406 | n/a | n/a | n/a | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-25 · 404 | none |
| Motilal Oswal Small Cap Fund · Direct · Growth · 152237 | 2023-12-29 → 2026-09-25 · 676 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-25 · 673 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Motilal Oswal Small Cap Fund · Direct · IDCW · 152235 | 2023-12-29 → 2026-09-25 · 676 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-25 · 673 | none |
| Motilal Oswal Small Cap Fund · Regular · Growth · 152232 | 2023-12-29 → 2026-09-25 · 676 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-25 · 673 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Motilal Oswal Small Cap Fund · Regular · IDCW · 152234 | 2023-12-29 → 2026-09-25 · 676 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-25 · 673 | none |
| Nippon India Small Cap Fund · Direct · Bonus · 118777 | 2013-01-03 → 2026-09-25 · 3378 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-25 · 3375 | none |
| Nippon India Small Cap Fund · Direct · Growth · 118778 | 2013-01-02 → 2026-09-25 · 3379 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-25 · 3376 | none |
| Nippon India Small Cap Fund · Direct · IDCW · 118775 | 2013-01-03 → 2026-09-25 · 3378 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-25 · 3375 | none |
| Nippon India Small Cap Fund · Regular · Bonus · 113178 | 2010-09-21 → 2026-09-25 · 3943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-25 · 3940 | none |
| Nippon India Small Cap Fund · Regular · Growth · 113177 | 2010-09-21 → 2026-09-25 · 3943 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-25 · 3940 | none |
| Nippon India Small Cap Fund · Regular · IDCW · 113179 | 2010-09-21 → 2026-09-25 · 3943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-25 · 3940 | none |
| Pgim India Small Cap Fund · Direct · Growth · 149019 | 2021-08-02 → 2026-09-25 · 1270 | yes | yes | yes | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-25 · 1267 | none |
| Pgim India Small Cap Fund · Direct · IDCW · 149031 | 2021-08-02 → 2026-09-25 · 1270 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-25 · 1267 | none |
| Pgim India Small Cap Fund · Regular · Growth · 149020 | 2021-08-02 → 2026-09-25 · 1270 | yes | yes | yes | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-25 · 1267 | none |
| Pgim India Small Cap Fund · Regular · IDCW · 149032 | 2021-08-02 → 2026-09-25 · 1270 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-25 · 1267 | none |
| Quant Small Cap Fund · Direct · Growth · 120828 | 2013-01-07 → 2026-09-25 · 3379 | yes | yes | yes | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2013-01-07 → 2026-09-25 · 3367 | none |
| Quant Small Cap Fund · Direct · IDCW · 120827 | 2013-01-07 → 2026-09-25 · 3379 | n/a | n/a | n/a | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2013-01-07 → 2026-09-25 · 3367 | none |
| Quant Small Cap Fund · Regular · Growth · 100177 | 2006-04-03 → 2026-09-25 · 5045 | yes | yes | yes | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5029 | none |
| Quant Small Cap Fund · Regular · IDCW · 100176 | 2006-04-03 → 2026-09-25 · 5045 | n/a | n/a | n/a | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5029 | none |
| Quantum Small Cap Fund · Direct · Growth · 152107 | 2023-11-03 → 2026-09-25 · 710 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing |
| Quantum Small Cap Fund · Regular · Growth · 152108 | 2023-11-03 → 2026-09-25 · 710 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing |
| SBI Small Cap Fund · Direct · Growth · 125497 | 2013-11-18 → 2026-09-25 · 3173 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| SBI Small Cap Fund · Direct · IDCW · 125496 | 2013-11-18 → 2026-09-25 · 3173 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| SBI Small Cap Fund · Regular · Growth · 125494 | 2013-11-18 → 2026-09-25 · 3173 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| SBI Small Cap Fund · Regular · IDCW · 125495 | 2013-11-18 → 2026-09-25 · 3173 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Samco Small Cap Fund · Direct · Growth · 153868 | 2025-12-09 → 2026-09-25 · 198 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2025-12-09 → 2026-09-25 · 197 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Samco Small Cap Fund · Regular · Growth · 153869 | 2025-12-09 → 2026-09-25 · 198 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2025-12-09 → 2026-09-25 · 197 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Sundaram Small Cap Fund · Direct · Growth · 119588 | 2013-01-02 → 2026-09-25 · 3379 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-25 · 3376 | none |
| Sundaram Small Cap Fund · Direct · Growth · 119589 | 2013-01-02 → 2026-09-25 · 3379 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-25 · 3376 | none |
| Sundaram Small Cap Fund · Regular · Growth · 100795 | 2006-04-03 → 2026-09-25 · 5044 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5039 | none |
| Sundaram Small Cap Fund · Regular · IDCW · 100794 | 2006-04-03 → 2026-09-25 · 5044 | n/a | n/a | n/a | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-25 · 5039 | none |
| Tata Small Cap Fund · Direct · Growth · 145206 | 2018-11-13 → 2026-09-25 · 1940 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-25 · 1937 | none |
| Tata Small Cap Fund · Direct · IDCW · 145207 | 2019-06-14 → 2026-09-25 · 1783 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-06-14 → 2026-09-25 · 1780 | none |
| Tata Small Cap Fund · Direct · IDCW · 145209 | 2018-11-13 → 2026-09-25 · 1940 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-25 · 1937 | none |
| Tata Small Cap Fund · Regular · Growth · 145208 | 2018-11-13 → 2026-09-25 · 1940 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-25 · 1937 | none |
| Tata Small Cap Fund · Regular · IDCW · 145205 | 2019-06-14 → 2026-09-25 · 1783 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-06-14 → 2026-09-25 · 1780 | none |
| Tata Small Cap Fund · Regular · IDCW · 145210 | 2018-11-13 → 2026-09-25 · 1940 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-25 · 1937 | none |
| The Wealth Company Small Cap Fund · Direct · Growth · 154269 | 2026-03-30 → 2026-09-25 · 124 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-25 · 123 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| The Wealth Company Small Cap Fund · Direct · IDCW · 154270 | 2026-03-30 → 2026-09-25 · 124 | n/a | n/a | n/a | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-25 · 123 | none |
| The Wealth Company Small Cap Fund · Regular · Growth · 154268 | 2026-03-30 → 2026-09-25 · 124 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-25 · 123 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| The Wealth Company Small Cap Fund · Regular · IDCW · 154267 | 2026-03-30 → 2026-09-25 · 124 | n/a | n/a | n/a | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-25 · 123 | none |
| Trustmf Small Cap Fund · Direct · Growth · 152939 | 2024-11-05 → 2026-09-25 · 468 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-25 · 465 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Trustmf Small Cap Fund · Direct · IDCW · 152937 | 2024-11-05 → 2026-09-25 · 468 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-25 · 465 | none |
| Trustmf Small Cap Fund · Regular · Growth · 152940 | 2024-11-05 → 2026-09-25 · 468 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-25 · 465 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Trustmf Small Cap Fund · Regular · IDCW · 152938 | 2024-11-05 → 2026-09-25 · 468 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-25 · 465 | none |
| UTI Small Cap Fund · Direct · Growth · 148618 | 2020-12-23 → 2026-09-25 · 1419 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-25 · 1416 | none |
| UTI Small Cap Fund · Direct · IDCW · 148619 | 2020-12-23 → 2026-09-25 · 1419 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-25 · 1416 | none |
| UTI Small Cap Fund · Regular · Growth · 148617 | 2020-12-23 → 2026-09-25 · 1419 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-25 · 1416 | none |
| UTI Small Cap Fund · Regular · IDCW · 148616 | 2020-12-23 → 2026-09-25 · 1419 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-25 · 1416 | none |
| Union Small Cap Fund · Direct · Growth · 129649 | 2014-06-17 → 2026-09-25 · 3020 | yes | yes | yes | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Union Small Cap Fund · Direct · IDCW · 129646 | 2014-06-17 → 2026-09-25 · 3020 | n/a | n/a | n/a | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Union Small Cap Fund · Regular · Growth · 129647 | 2014-06-17 → 2026-09-25 · 3020 | yes | yes | yes | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |
| Union Small Cap Fund · Regular · IDCW · 129648 | 2014-06-17 → 2026-09-25 · 3020 | n/a | n/a | n/a | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing |

## Notes

- Return eligibility mirrors the website's seven-day anchor tolerance but does not calculate or store a return.
- Benchmark overlap uses exact common dates only; no forward-fill or interpolation is performed.
- A reported benchmark identity is not treated as historical TRI coverage unless the retained identity explicitly establishes a total-return index.
- The default comparison role is the fund's reported benchmark; no retained alternate series is substituted automatically.
- alternate_comparisons lists retained non-reported TRI series that can be selected explicitly without changing the fund's reported benchmark identity.
- Verified official-history NAV gaps remain visible as raw gaps but are excluded from the actionable missing-data queue; no NAV is inferred.
- This audit is read-only and uses retained NAV, benchmark and metric evidence only.
