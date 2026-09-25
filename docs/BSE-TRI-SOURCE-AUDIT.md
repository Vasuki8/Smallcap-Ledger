# BSE 250 SmallCap TRI source audit

Audit date: **2026-09-25 UTC**

## Outcome

The requested historical **BSE 250 SmallCap TRI** repair is **blocked by the current first-party distribution route under the project's free-source constraint**.

No benchmark observations were inserted, no existing Nifty series was changed, and no UI/performance endpoint was modified.

## First-party identity evidence

BSE Index Services' official BSE 250 SmallCap factsheet establishes the identity boundary that the tracker must preserve:

- index: **BSE 250 SmallCap Index**
- first value date: **16 September 2005**
- base value: **1000**
- price-return ticker: **SML250**
- total-return ticker: **SML250T**
- as of 30 March 2026, the factsheet prints **Total Returns index level 7043.82** and **Price Returns index level 5646.83**

Official factsheet:

`https://www.bseindices.com/Downloads/Factsheet/Factsheet_BSE250SmallCapIndex_Mar2026.pdf`

The official BSE Indices Methodology independently maps **BSE 250 SmallCap** to PR ticker **SML250** and TR ticker **SML250T**.

Official methodology:

`https://www.bseindices.com/Downloads/BSE_Indices_Methodology.pdf`

## Distribution constraint

The same official methodology states in its **Index Data** section that **daily constituent and index level data are available via subscription**.

A bounded first-party search for a public historical `SML250T` CSV/API/download did not identify a free daily TRI history that can be retained with the project's required date/source evidence. The public index page/factsheet is useful for identity and point-in-time verification, but it does not provide a verified free daily `SML250T` history suitable for the tracker.

Current first-party index page:

`https://www.bseindices.com/indices-details/code/103`

## Rejected shortcuts

Do **not**:

- ingest `SML250` or the public price-index chart and relabel it as TRI;
- derive historical TRI from the price index, dividend yield, constituents, or fund-return disclosures;
- substitute a third-party historical series for the missing BSE first-party history;
- add a paid/subscription data source without owner approval;
- overwrite or alias the retained **Nifty Smallcap 250 TRI** series.

These would violate the tracker's evidence and source-policy requirements.

## Tracker impact

The existing performance-coverage audit remains correct:

- **10 funds / 20 Growth plans** explicitly report BSE 250 SmallCap TRI (or equivalent total-return wording);
- those plans remain `reported_tri_series_missing`;
- their `website_default_benchmark_mismatch` findings must remain visible because the website still defaults to the retained Nifty series;
- the database continues to retain only the distinct **Nifty Smallcap 250 TRI** historical series.

The BSE repair should be retried only if BSE Index Services publishes a verifiable free first-party `SML250T` history or the owner separately approves a licensed source.

## Next backend repair

Move to the next evidence-only benchmark task: verify the three retained benchmark identities that do **not** currently establish TRI:

1. Edelweiss Small Cap Fund — `Nifty Smallcap 250`
2. Franklin India Small Cap Fund — `Nifty Smallcap 250`
3. Groww Small Cap Fund — `Nifty Smallcap 250 Index`

Use current first-party AMC scheme/factsheet/KIM/SID evidence only. Promote an identity to **Nifty Smallcap 250 TRI** only when the AMC explicitly establishes total-return benchmark identity. Otherwise retain the current unqualified benchmark text and record the limitation.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; the source-retention audit remains read-only and its 700 link-only candidates remain untouched.
