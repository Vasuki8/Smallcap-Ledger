# Historical NAV gap source audit

Audit date: **2026-09-25 UTC**

## Outcome

The six retained >7-calendar-day NAV intervals reviewed so far are **verified official-history gaps**, not values that can currently be recovered from the authoritative sources checked.

No NAV observation was added, estimated, interpolated or forward-filled.

The performance audit should continue to preserve the raw date gaps, and none of these six intervals should appear as unexplained/actionable `nav_large_gap` defects. Their evidence is retained in `tracker/nav_gap_evidence.json`.

## Authoritative AMFI check

AMFI's official historical NAV endpoint was queried by exact AMC/date window and exact scheme code.

For every flagged interval, AMFI returned **exactly two observations: the existing boundary dates** and no intermediate rows.

- **ABSL Small Cap Regular Growth · code 105804:** 2010-05-31 **11.5499** → 2010-06-08 **11.4193**.
- **ABSL Small Cap Regular IDCW · code 105805:** 2010-05-31 **11.5499** → 2010-06-08 **11.4193**; exact AMFI row identity includes payout ISIN **INF209K01EO0** and reinvestment ISIN **INF209K01EP7**.
- **DSP Small Cap Regular Growth · code 105989:** 2007-08-08 **10.5740** → 2007-08-16 **10.1690**.
- DSP: 2008-08-27 **9.1660** → 2008-09-04 **9.3220**.
- DSP: 2010-03-17 **13.2800** → 2010-03-25 **13.4580**.
- DSP: 2010-04-07 **14.1660** → 2010-04-15 **14.4550**.

The exact AMFI query URLs, response SHA-256 values and boundary observations are in the machine-readable evidence file.

ABSL Regular IDCW code **105805** was checked independently at exact scheme-code level in workflow run **36185438441**. AMFI returned exactly the two retained boundary rows and no intermediate observations. The response SHA-256 is **4b0ab23045b78f1e8b143ea8509f3da3f2dc5aa4d138e668f2a9645fd75db5fb**. This closes the last unresolved tracker NAV-gap classification without inserting any NAV.

## DSP first-party confirmation

DSP's current public historical-NAV page identifies **internal option id 157** as **DSP Small Cap Fund · Regular · Growth**.

Using that exact first-party option id, DSP's own historical exporter returned exactly the same two boundary rows for each of the four historical intervals and no intermediate rows.

A control query for **2026-09-01 → 2026-09-10** returned **8 daily business-day observations**, proving the current exporter path is capable of returning normal daily NAV history when those rows exist.

The old rows retain DSP's historical scheme name, **DSP BlackRock Micro Cap Fund - Regular - Growth**, which is consistent with the same option lineage.

## Market-calendar check

These are not merely whole-market weekend/holiday spans. Official NSE archive evidence shows normal-market activity or normal settlements inside each interval, including:

- 2007-08-09 and 2007-08-14;
- 2008-08-29 and 2008-09-01;
- 2010-03-19;
- 2010-04-08 normal-market trading stated by NSE;
- 2010-06-04.

This does **not** establish why the funds lack intermediate NAV rows, and the tracker must not infer the missing values. It establishes only that a blanket market-closure explanation is insufficient.

## Classification contract

`verified_official_history_gap` means:

1. the retained NAV series has a >7-calendar-day interval;
2. the authoritative official history checked for that scheme/period does not supply intermediate NAV observations;
3. no intermediate NAV is reconstructed;
4. the raw gap remains visible in audit evidence;
5. the interval is removed from the actionable missing-data repair queue unless a material official source change later exposes additional observations.

This classification is evidence about **availability in official history**, not a claim about the fund's operational reason for the missing dates.

## Remaining performance-data blocker

The unresolved historical benchmark blocker remains **BSE 250 SmallCap TRI** for the 10 BSE-benchmarked funds. Per `docs/BSE-TRI-SOURCE-AUDIT.md`, first-party daily index-level history is currently subscription-distributed, so that repair remains blocked under the project's free-source constraint.
