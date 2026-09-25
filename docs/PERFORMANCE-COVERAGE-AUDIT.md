# Historical performance and benchmark coverage audit

Prepared: 2026-09-25T19:37:02+00:00

**Read-only:** retained NAV/benchmark evidence only; no forward-fill, return fabrication, source fetch or UI change.

## Summary

- Plans: **143**; Growth plans eligible for displayed returns: **72**.
- Reported benchmark identity families: **36 / 36**.
- Explicit reported TRI identities on Growth plans: **72**.
- Growth plans with the relevant reported TRI series and at least two exact overlapping dates: **52**.
- Growth plans where the explicit reported TRI differs from the website's current default **Nifty Smallcap 250 TRI**: **20**.
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
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2007-08-08 → 2007-08-16 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2008-08-27 → 2008-09-04 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2010-03-17 → 2010-03-25 (8 calendar days) · verified_official_history_gap · verified 2026-09-25
- **DSP Small Cap Fund · Regular · Growth · 105989**: 2010-04-07 → 2010-04-15 (8 calendar days) · verified_official_history_gap · verified 2026-09-25

## Per-plan audit

| Fund / plan | NAV range / obs | 1Y | 3Y | 5Y | Reported benchmark | Required TRI series | Exact overlap | Issues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Abakkus Small Cap Fund · Direct · Growth · 154215 | 2026-03-20 → 2026-09-24 · 128 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-20 → 2026-09-24 · 127 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Abakkus Small Cap Fund · Regular · Growth · 154214 | 2026-03-20 → 2026-09-24 · 128 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-20 → 2026-09-24 · 127 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Aditya Birla Sun Life Small Cap Fund · Direct · Growth · 119556 | 2013-01-07 → 2026-09-24 · 3375 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Aditya Birla Sun Life Small Cap Fund · Direct · IDCW · 119557 | 2013-01-02 → 2026-09-24 · 3378 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Aditya Birla Sun Life Small Cap Fund · Regular · Growth · 105804 | 2007-05-31 → 2026-09-24 · 4750 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Aditya Birla Sun Life Small Cap Fund · Regular · IDCW · 105805 | 2007-05-31 → 2026-09-24 · 4750 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_large_gap, reported_tri_series_missing, website_default_benchmark_mismatch |
| Axis Small Cap Fund · Direct · Growth · 125354 | 2013-12-05 → 2026-09-24 · 3158 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-24 · 3147 | none |
| Axis Small Cap Fund · Direct · IDCW · 125351 | 2013-12-05 → 2026-09-24 · 3158 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-24 · 3147 | none |
| Axis Small Cap Fund · Regular · Growth · 125350 | 2013-12-05 → 2026-09-24 · 3158 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-24 · 3147 | none |
| Axis Small Cap Fund · Regular · IDCW · 125352 | 2013-12-05 → 2026-09-24 · 3158 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-12-05 → 2026-09-24 · 3147 | none |
| Bajaj Finserv Small Cap Fund · Direct · Growth · 153612 | 2025-07-22 → 2026-09-24 · 290 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| Bajaj Finserv Small Cap Fund · Direct · IDCW · 153611 | 2025-07-22 → 2026-09-24 · 290 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bajaj Finserv Small Cap Fund · Regular · Growth · 153609 | 2025-07-22 → 2026-09-24 · 290 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| Bajaj Finserv Small Cap Fund · Regular · IDCW · 153610 | 2025-07-22 → 2026-09-24 · 290 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bandhan Small Cap Fund · Direct · Growth · 147946 | 2020-02-26 → 2026-09-24 · 1631 | yes | yes | yes | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bandhan Small Cap Fund · Direct · IDCW · 147943 | 2020-02-26 → 2026-09-24 · 1631 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bandhan Small Cap Fund · Regular · Growth · 147944 | 2020-02-26 → 2026-09-24 · 1631 | yes | yes | yes | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bandhan Small Cap Fund · Regular · IDCW · 147945 | 2020-02-26 → 2026-09-24 · 1631 | n/a | n/a | n/a | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Bank Of India Small Cap Fund · Direct · Growth · 145678 | 2018-12-27 → 2026-09-24 · 1909 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-24 · 1906 | none |
| Bank Of India Small Cap Fund · Direct · IDCW · 145675 | 2018-12-27 → 2026-09-24 · 1909 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-24 · 1906 | none |
| Bank Of India Small Cap Fund · Regular · Growth · 145677 | 2018-12-27 → 2026-09-24 · 1909 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-24 · 1906 | none |
| Bank Of India Small Cap Fund · Regular · IDCW · 145676 | 2018-12-27 → 2026-09-24 · 1909 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-12-27 → 2026-09-24 · 1906 | none |
| Baroda Bnp Paribas Small Cap Fund · Direct · Growth · 152128 | 2023-11-01 → 2026-09-24 · 714 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-24 · 711 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Baroda Bnp Paribas Small Cap Fund · Direct · IDCW · 152129 | 2023-11-01 → 2026-09-24 · 714 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-24 · 711 | none |
| Baroda Bnp Paribas Small Cap Fund · Regular · Growth · 152130 | 2023-11-01 → 2026-09-24 · 714 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-24 · 711 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Baroda Bnp Paribas Small Cap Fund · Regular · IDCW · 152131 | 2023-11-01 → 2026-09-24 · 714 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-11-01 → 2026-09-24 · 711 | none |
| Canara Robeco Small Cap Fund · Direct · Growth · 146130 | 2019-02-19 → 2026-09-24 · 1871 | yes | yes | yes | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-24 · 1868 | none |
| Canara Robeco Small Cap Fund · Direct · IDCW · 146131 | 2019-02-19 → 2026-09-24 · 1871 | n/a | n/a | n/a | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-24 · 1868 | none |
| Canara Robeco Small Cap Fund · Regular · Growth · 146127 | 2019-02-19 → 2026-09-24 · 1871 | yes | yes | yes | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-24 · 1868 | none |
| Canara Robeco Small Cap Fund · Regular · IDCW · 146128 | 2019-02-19 → 2026-09-24 · 1871 | n/a | n/a | n/a | Nifty Smallcap 250 Index TRI | Nifty Smallcap 250 TRI | 2019-02-19 → 2026-09-24 · 1868 | none |
| DSP Small Cap Fund · Direct · Growth · 119212 | 2013-01-02 → 2026-09-24 · 3381 | yes | yes | yes | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| DSP Small Cap Fund · Direct · IDCW · 119213 | 2013-01-03 → 2026-09-24 · 3380 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| DSP Small Cap Fund · Regular · Growth · 105989 | 2007-06-20 → 2026-09-24 · 4212 | yes | yes | yes | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| DSP Small Cap Fund · Regular · IDCW · 113153 | 2010-08-03 → 2026-09-24 · 3979 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Edelweiss Small Cap Fund · Direct · Growth · 146196 | 2019-02-14 → 2026-09-24 · 1876 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-24 · 1871 | none |
| Edelweiss Small Cap Fund · Direct · IDCW · 146197 | 2019-02-14 → 2026-09-24 · 1876 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-24 · 1871 | none |
| Edelweiss Small Cap Fund · Regular · Growth · 146193 | 2019-02-14 → 2026-09-24 · 1876 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-24 · 1871 | none |
| Edelweiss Small Cap Fund · Regular · IDCW · 146194 | 2019-02-14 → 2026-09-24 · 1876 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-02-14 → 2026-09-24 · 1871 | none |
| Franklin India Small Cap Fund · Direct · Growth · 118525 | 2013-01-01 → 2026-09-24 · 3380 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-01 → 2026-09-24 · 3377 | none |
| Franklin India Small Cap Fund · Direct · IDCW · 118524 | 2013-01-01 → 2026-09-24 · 3380 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-01 → 2026-09-24 · 3377 | none |
| Franklin India Small Cap Fund · Regular · Growth · 103360 | 2006-04-03 → 2026-09-24 · 5042 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5039 | none |
| Franklin India Small Cap Fund · Regular · IDCW · 103361 | 2006-04-03 → 2026-09-24 · 5042 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5039 | none |
| Groww Small Cap Fund · Direct · Growth · 154063 | 2026-02-02 → 2026-09-24 · 161 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-24 · 160 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Groww Small Cap Fund · Direct · IDCW · 154104 | 2026-02-02 → 2026-09-24 · 161 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-24 · 160 | none |
| Groww Small Cap Fund · Regular · Growth · 154102 | 2026-02-02 → 2026-09-24 · 161 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-24 · 160 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Groww Small Cap Fund · Regular · IDCW · 154103 | 2026-02-02 → 2026-09-24 · 161 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2026-02-02 → 2026-09-24 · 160 | none |
| HDFC Small Cap Fund · Direct · Growth · 130503 | 2014-06-30 → 2026-09-24 · 3011 | yes | yes | yes | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| HDFC Small Cap Fund · Direct · IDCW · 130504 | 2014-06-30 → 2026-09-24 · 3011 | n/a | n/a | n/a | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| HDFC Small Cap Fund · Regular · Growth · 130502 | 2014-06-30 → 2026-09-24 · 3011 | yes | yes | yes | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| HDFC Small Cap Fund · Regular · IDCW · 130501 | 2014-06-30 → 2026-09-24 · 3011 | n/a | n/a | n/a | BSE 250 SmallCap Index (Total Returns Index) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| HSBC Small Cap Fund · Unspecified · Other · 151130 | 2022-11-28 → 2026-09-24 · 943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-24 · 940 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151131 | 2022-11-28 → 2026-09-24 · 943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-24 · 940 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151132 | 2022-11-28 → 2026-09-24 · 943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-24 · 940 | none |
| HSBC Small Cap Fund · Unspecified · Other · 151133 | 2022-11-28 → 2026-09-24 · 943 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2022-11-28 → 2026-09-24 · 940 | none |
| Helios Small Cap Fund · Direct · Growth · 153912 | 2025-11-28 → 2026-09-24 · 204 | no | no | no | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-24 · 203 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Helios Small Cap Fund · Direct · IDCW · 153910 | 2025-11-28 → 2026-09-24 · 204 | n/a | n/a | n/a | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-24 · 203 | none |
| Helios Small Cap Fund · Regular · Growth · 153909 | 2025-11-28 → 2026-09-24 · 204 | no | no | no | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-24 · 203 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Helios Small Cap Fund · Regular · IDCW · 153911 | 2025-11-28 → 2026-09-24 · 204 | n/a | n/a | n/a | Nifty Small Cap 250 Total Return Index (TRI) | Nifty Smallcap 250 TRI | 2025-11-28 → 2026-09-24 · 203 | none |
| ICICI Prudential Small Cap Fund · Direct · Growth · 120591 | 2013-01-03 → 2026-09-24 · 3350 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-24 · 3347 | none |
| ICICI Prudential Small Cap Fund · Direct · IDCW · 120870 | 2013-01-08 → 2026-09-24 · 3347 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-08 → 2026-09-24 · 3344 | none |
| ICICI Prudential Small Cap Fund · Institutional · Growth · 106821 | 2007-10-19 → 2020-04-24 · 3016 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2020-04-24 · 3016 | none |
| ICICI Prudential Small Cap Fund · Regular · Growth · 106823 | 2007-10-19 → 2026-09-24 · 4601 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2026-09-24 · 4598 | none |
| ICICI Prudential Small Cap Fund · Regular · IDCW · 106822 | 2007-10-19 → 2026-09-24 · 4601 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2007-10-19 → 2026-09-24 · 4598 | none |
| Invesco India Small Cap Fund · Direct · Growth · 145137 | 2018-11-02 → 2026-09-24 · 1944 | yes | yes | yes | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Invesco India Small Cap Fund · Direct · IDCW · 145138 | 2018-11-02 → 2026-09-24 · 1944 | n/a | n/a | n/a | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Invesco India Small Cap Fund · Regular · Growth · 145139 | 2018-11-02 → 2026-09-24 · 1944 | yes | yes | yes | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Invesco India Small Cap Fund · Regular · IDCW · 145140 | 2018-11-02 → 2026-09-24 · 1944 | n/a | n/a | n/a | BSE 250 Smallcap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Iti Small Cap Fund · Direct · Growth · 147919 | 2020-02-19 → 2026-09-24 · 1626 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-24 · 1624 | none |
| Iti Small Cap Fund · Direct · IDCW · 147917 | 2020-02-19 → 2026-09-24 · 1626 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-24 · 1624 | none |
| Iti Small Cap Fund · Regular · Growth · 147920 | 2020-02-19 → 2026-09-24 · 1626 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-24 · 1624 | none |
| Iti Small Cap Fund · Regular · IDCW · 147918 | 2020-02-19 → 2026-09-24 · 1626 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-02-19 → 2026-09-24 · 1624 | none |
| Jm Small Cap Fund · Direct · Growth · 152614 | 2024-06-24 → 2026-09-24 · 558 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-24 · 556 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Jm Small Cap Fund · Direct · IDCW · 152615 | 2024-06-24 → 2026-09-24 · 558 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-24 · 556 | none |
| Jm Small Cap Fund · Regular · Growth · 152612 | 2024-06-24 → 2026-09-24 · 558 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-24 · 556 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Jm Small Cap Fund · Regular · IDCW · 152613 | 2024-06-24 → 2026-09-24 · 558 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-06-24 → 2026-09-24 · 556 | none |
| Kotak Small Cap Fund · Direct · Growth · 120164 | 2013-01-02 → 2026-09-24 · 3379 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-24 · 3376 | none |
| Kotak Small Cap Fund · Direct · IDCW · 120163 | 2013-01-02 → 2026-09-24 · 3379 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-24 · 3376 | none |
| Kotak Small Cap Fund · Regular · Growth · 102875 | 2006-04-03 → 2026-09-24 · 5042 | yes | yes | yes | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5039 | none |
| Kotak Small Cap Fund · Regular · IDCW · 102874 | 2006-04-03 → 2026-09-24 · 5042 | n/a | n/a | n/a | NIFTY Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5039 | none |
| LIC Mf Small Cap Fund · Direct · Growth · 152004 | 2023-07-31 → 2026-09-24 · 776 | yes | yes | no | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-24 · 773 | nav_5y_return_unavailable, benchmark_5y_overlap_unavailable |
| LIC Mf Small Cap Fund · Direct · IDCW · 152005 | 2023-07-31 → 2026-09-24 · 776 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-24 · 773 | none |
| LIC Mf Small Cap Fund · Regular · Growth · 152003 | 2023-07-31 → 2026-09-24 · 776 | yes | yes | no | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-24 · 773 | nav_5y_return_unavailable, benchmark_5y_overlap_unavailable |
| LIC Mf Small Cap Fund · Regular · IDCW · 152006 | 2023-07-31 → 2026-09-24 · 776 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2023-07-31 → 2026-09-24 · 773 | none |
| Mahindra Manulife Small Cap Fund · Direct · Growth · 150915 | 2022-12-14 → 2026-09-24 · 931 | yes | yes | no | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| Mahindra Manulife Small Cap Fund · Direct · IDCW · 150913 | 2022-12-14 → 2026-09-24 · 931 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Mahindra Manulife Small Cap Fund · Regular · Growth · 150912 | 2022-12-14 → 2026-09-24 · 931 | yes | yes | no | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| Mahindra Manulife Small Cap Fund · Regular · IDCW · 150914 | 2022-12-14 → 2026-09-24 · 931 | n/a | n/a | n/a | BSE 250 Small Cap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Mirae Asset Small Cap Fund · Direct · Growth · 153196 | 2025-02-03 → 2026-09-24 · 405 | yes | no | no | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-24 · 403 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Mirae Asset Small Cap Fund · Direct · IDCW · 153197 | 2025-02-03 → 2026-09-24 · 405 | n/a | n/a | n/a | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-24 · 403 | none |
| Mirae Asset Small Cap Fund · Regular · Growth · 153198 | 2025-02-03 → 2026-09-24 · 405 | yes | no | no | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-24 · 403 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Mirae Asset Small Cap Fund · Regular · IDCW · 153199 | 2025-02-03 → 2026-09-24 · 405 | n/a | n/a | n/a | Nifty Smallcap 250 (TRI) | Nifty Smallcap 250 TRI | 2025-02-03 → 2026-09-24 · 403 | none |
| Motilal Oswal Small Cap Fund · Direct · Growth · 152237 | 2023-12-29 → 2026-09-24 · 675 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-24 · 672 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Motilal Oswal Small Cap Fund · Direct · IDCW · 152235 | 2023-12-29 → 2026-09-24 · 675 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-24 · 672 | none |
| Motilal Oswal Small Cap Fund · Regular · Growth · 152232 | 2023-12-29 → 2026-09-24 · 675 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-24 · 672 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Motilal Oswal Small Cap Fund · Regular · IDCW · 152234 | 2023-12-29 → 2026-09-24 · 675 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2023-12-29 → 2026-09-24 · 672 | none |
| Nippon India Small Cap Fund · Direct · Bonus · 118777 | 2013-01-03 → 2026-09-24 · 3377 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-24 · 3374 | none |
| Nippon India Small Cap Fund · Direct · Growth · 118778 | 2013-01-02 → 2026-09-24 · 3378 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-24 · 3375 | none |
| Nippon India Small Cap Fund · Direct · IDCW · 118775 | 2013-01-03 → 2026-09-24 · 3377 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-03 → 2026-09-24 · 3374 | none |
| Nippon India Small Cap Fund · Regular · Bonus · 113178 | 2010-09-21 → 2026-09-24 · 3942 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-24 · 3939 | none |
| Nippon India Small Cap Fund · Regular · Growth · 113177 | 2010-09-21 → 2026-09-24 · 3942 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-24 · 3939 | none |
| Nippon India Small Cap Fund · Regular · IDCW · 113179 | 2010-09-21 → 2026-09-24 · 3942 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2010-09-21 → 2026-09-24 · 3939 | none |
| Pgim India Small Cap Fund · Direct · Growth · 149019 | 2021-08-02 → 2026-09-24 · 1269 | yes | yes | yes | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-24 · 1266 | none |
| Pgim India Small Cap Fund · Direct · IDCW · 149031 | 2021-08-02 → 2026-09-24 · 1269 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-24 · 1266 | none |
| Pgim India Small Cap Fund · Regular · Growth · 149020 | 2021-08-02 → 2026-09-24 · 1269 | yes | yes | yes | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-24 · 1266 | none |
| Pgim India Small Cap Fund · Regular · IDCW · 149032 | 2021-08-02 → 2026-09-24 · 1269 | n/a | n/a | n/a | Nifty Smallcap 250 - TRI | Nifty Smallcap 250 TRI | 2021-08-02 → 2026-09-24 · 1266 | none |
| Quant Small Cap Fund · Direct · Growth · 120828 | 2013-01-07 → 2026-09-24 · 3378 | yes | yes | yes | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2013-01-07 → 2026-09-24 · 3366 | none |
| Quant Small Cap Fund · Direct · IDCW · 120827 | 2013-01-07 → 2026-09-24 · 3378 | n/a | n/a | n/a | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2013-01-07 → 2026-09-24 · 3366 | none |
| Quant Small Cap Fund · Regular · Growth · 100177 | 2006-04-03 → 2026-09-24 · 5044 | yes | yes | yes | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5028 | none |
| Quant Small Cap Fund · Regular · IDCW · 100176 | 2006-04-03 → 2026-09-24 · 5044 | n/a | n/a | n/a | NIFTY SMALLCAP 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5028 | none |
| Quantum Small Cap Fund · Direct · Growth · 152107 | 2023-11-03 → 2026-09-24 · 709 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| Quantum Small Cap Fund · Regular · Growth · 152108 | 2023-11-03 → 2026-09-24 · 709 | yes | no | no | BSE 250 SmallCap TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | nav_3y_return_unavailable, nav_5y_return_unavailable, reported_tri_series_missing, website_default_benchmark_mismatch |
| SBI Small Cap Fund · Direct · Growth · 125497 | 2013-11-18 → 2026-09-24 · 3172 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| SBI Small Cap Fund · Direct · IDCW · 125496 | 2013-11-18 → 2026-09-24 · 3172 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| SBI Small Cap Fund · Regular · Growth · 125494 | 2013-11-18 → 2026-09-24 · 3172 | yes | yes | yes | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| SBI Small Cap Fund · Regular · IDCW · 125495 | 2013-11-18 → 2026-09-24 · 3172 | n/a | n/a | n/a | BSE 250 Small Cap Index TRI | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Samco Small Cap Fund · Direct · Growth · 153868 | 2025-12-09 → 2026-09-24 · 197 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2025-12-09 → 2026-09-24 · 196 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Samco Small Cap Fund · Regular · Growth · 153869 | 2025-12-09 → 2026-09-24 · 197 | no | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2025-12-09 → 2026-09-24 · 196 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Sundaram Small Cap Fund · Direct · Growth · 119588 | 2013-01-02 → 2026-09-24 · 3378 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-24 · 3375 | none |
| Sundaram Small Cap Fund · Direct · Growth · 119589 | 2013-01-02 → 2026-09-24 · 3378 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2013-01-02 → 2026-09-24 · 3375 | none |
| Sundaram Small Cap Fund · Regular · Growth · 100795 | 2006-04-03 → 2026-09-24 · 5043 | yes | yes | yes | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5038 | none |
| Sundaram Small Cap Fund · Regular · IDCW · 100794 | 2006-04-03 → 2026-09-24 · 5043 | n/a | n/a | n/a | Nifty Small Cap 250 TRI | Nifty Smallcap 250 TRI | 2006-04-03 → 2026-09-24 · 5038 | none |
| Tata Small Cap Fund · Direct · Growth · 145206 | 2018-11-13 → 2026-09-24 · 1939 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-24 · 1936 | none |
| Tata Small Cap Fund · Direct · IDCW · 145207 | 2019-06-14 → 2026-09-24 · 1782 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-06-14 → 2026-09-24 · 1779 | none |
| Tata Small Cap Fund · Direct · IDCW · 145209 | 2018-11-13 → 2026-09-24 · 1939 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-24 · 1936 | none |
| Tata Small Cap Fund · Regular · Growth · 145208 | 2018-11-13 → 2026-09-24 · 1939 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-24 · 1936 | none |
| Tata Small Cap Fund · Regular · IDCW · 145205 | 2019-06-14 → 2026-09-24 · 1782 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2019-06-14 → 2026-09-24 · 1779 | none |
| Tata Small Cap Fund · Regular · IDCW · 145210 | 2018-11-13 → 2026-09-24 · 1939 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2018-11-13 → 2026-09-24 · 1936 | none |
| The Wealth Company Small Cap Fund · Direct · Growth · 154269 | 2026-03-30 → 2026-09-24 · 123 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-24 · 122 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| The Wealth Company Small Cap Fund · Direct · IDCW · 154270 | 2026-03-30 → 2026-09-24 · 123 | n/a | n/a | n/a | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-24 · 122 | none |
| The Wealth Company Small Cap Fund · Regular · Growth · 154268 | 2026-03-30 → 2026-09-24 · 123 | no | no | no | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-24 · 122 | nav_1y_return_unavailable, nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_1y_overlap_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| The Wealth Company Small Cap Fund · Regular · IDCW · 154267 | 2026-03-30 → 2026-09-24 · 123 | n/a | n/a | n/a | NIFTY SmallCap 250 TRI | Nifty Smallcap 250 TRI | 2026-03-30 → 2026-09-24 · 122 | none |
| Trustmf Small Cap Fund · Direct · Growth · 152939 | 2024-11-05 → 2026-09-24 · 467 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-24 · 464 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Trustmf Small Cap Fund · Direct · IDCW · 152937 | 2024-11-05 → 2026-09-24 · 467 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-24 · 464 | none |
| Trustmf Small Cap Fund · Regular · Growth · 152940 | 2024-11-05 → 2026-09-24 · 467 | yes | no | no | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-24 · 464 | nav_3y_return_unavailable, nav_5y_return_unavailable, benchmark_3y_overlap_unavailable, benchmark_5y_overlap_unavailable |
| Trustmf Small Cap Fund · Regular · IDCW · 152938 | 2024-11-05 → 2026-09-24 · 467 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2024-11-05 → 2026-09-24 · 464 | none |
| UTI Small Cap Fund · Direct · Growth · 148618 | 2020-12-23 → 2026-09-24 · 1418 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-24 · 1415 | none |
| UTI Small Cap Fund · Direct · IDCW · 148619 | 2020-12-23 → 2026-09-24 · 1418 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-24 · 1415 | none |
| UTI Small Cap Fund · Regular · Growth · 148617 | 2020-12-23 → 2026-09-24 · 1418 | yes | yes | yes | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-24 · 1415 | none |
| UTI Small Cap Fund · Regular · IDCW · 148616 | 2020-12-23 → 2026-09-24 · 1418 | n/a | n/a | n/a | Nifty Smallcap 250 TRI | Nifty Smallcap 250 TRI | 2020-12-23 → 2026-09-24 · 1415 | none |
| Union Small Cap Fund · Direct · Growth · 129649 | 2014-06-17 → 2026-09-24 · 3019 | yes | yes | yes | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Union Small Cap Fund · Direct · IDCW · 129646 | 2014-06-17 → 2026-09-24 · 3019 | n/a | n/a | n/a | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Union Small Cap Fund · Regular · Growth · 129647 | 2014-06-17 → 2026-09-24 · 3019 | yes | yes | yes | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |
| Union Small Cap Fund · Regular · IDCW · 129648 | 2014-06-17 → 2026-09-24 · 3019 | n/a | n/a | n/a | BSE 250 SmallCap Index (TRI) | BSE 250 SmallCap TRI | Gap → Gap · 0 | reported_tri_series_missing, website_default_benchmark_mismatch |

## Notes

- Return eligibility mirrors the website's seven-day anchor tolerance but does not calculate or store a return.
- Benchmark overlap uses exact common dates only; no forward-fill or interpolation is performed.
- A reported benchmark identity is not treated as historical TRI coverage unless the retained identity explicitly establishes a total-return index.
- website_default_mismatch flags plans whose explicit reported TRI benchmark differs from the website's current global default comparison series.
- Verified official-history NAV gaps remain visible as raw gaps but are excluded from the actionable missing-data queue; no NAV is inferred.
- This audit is read-only and uses retained NAV, benchmark and metric evidence only.
