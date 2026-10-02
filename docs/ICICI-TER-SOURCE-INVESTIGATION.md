# ICICI TER source investigation

Reviewed: 2026-10-02. This investigation preserves rejected evidence; it does not
recover TER coverage or authorize a parser acceptance change. The accompanying
[JSON evidence](ICICI-TER-SOURCE-INVESTIGATION.json) records the source and observed
boundaries. Original workbook bytes remain in ignored scratch storage and the
retained source archive, not as a new tracked binary.

## Historical source and reproduction

The retained September workbook was fetched at **2026-09-30T22:38:18+00:00**:

- URL: `https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx`
- SHA-256: `e3619e5cae99d4e663e67bf6eaedf21749bc8ec86f3eca351f666cd4d10c9dcc`.
- Size: **303,076 bytes**. The source member's size and hash were independently
  checked; its fetch record was read from the isolated historical database.
- Checkpoint: `database-36785965245-1.zip`, **12,524,413 bytes**, SHA-256
  `324245341e2395deb39028b347ba10d318f61eeac7e0d3c77982bed24e58c4c0`, matching the
  retained release manifest.

Replaying these bytes with the existing parsers and a fixed **2026-09-30** clock
produced `ValueError: ICICI TER workbook columns changed` for Mid Cap and
`ValueError: ICICI TER column C changed` for Small Cap. Discovery/fetch were
replayed locally; the worksheet reader and validation ran against the actual
workbook. This is separate from the earlier Mid Cap batch-1 failure at
**22:32:44**: that failed response had no recorded URL/hash, so equal bytes cannot
be claimed.

The mismatch is present in **`xl/worksheets/sheet1.xml`, physical row 3**.
Header cells are inline strings, not unresolved shared-string indexes. The source
labels C/H as **Base TER**, D/I and E/J as additional expenses under Regulations
**52(6A)(b)** and **52(6A)(c)**, and F/K as **GST**. These differ from the parser's
BER, brokerage, transaction-cost and statutory-levy contracts. L also differs in
spacing. Relabelling these source columns as BER or treating every difference as
formatting is unsupported.

The exact latest family rows both report **2026-09-29**. Component sums below are
diagnostic arithmetic in percentage points, not accepted TER observations:

| Family / worksheet row | Plan | Source component sum | Reported Total TER | Difference |
| --- | --- | ---: | ---: | ---: |
| ICICI Prudential Mid Cap Fund / 1973 | Regular | 1.85 | 1.85 | 0.00 |
| ICICI Prudential Mid Cap Fund / 1973 | Direct | 1.21 | 1.11 | 0.10 |
| ICICI Prudential Small Cap Fund / 4177 | Regular | 2.10 | 2.10 | 0.00 |
| ICICI Prudential Small Cap Fund / 4177 | Direct | 1.30 | 1.18 | 0.12 |

The workbook says TER disclosure is net of reversals under regulatory provisions,
but it supplies no quantified adjustment for these rows. That footnote cannot
establish how to reconcile the differences. Preserve the existing **0.02
percentage-point** rejection tolerance and published Total TER values; do not
invent a reversal or derive an accepted TER from the component sum.

## Current production evidence is distinct

[Production run 37075265591](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37075265591)
completed successfully on merged PR #350 code
`b11f49c4d264ea860b9fc9c45f4149fceea902dd`: build completed at
**2026-10-02T23:22:44Z**, deploy at **23:23:02Z**. Generated commit
`031571cf94b7b2dd79ec69558ce16c370577ff04` has that code commit as its parent.
The committed export clock is **23:22:13+00:00**, latest included NAV
**2026-10-01**, with **36 funds, 143 series and 282,152 NAV observations**.
The live host was blocked by the environment network policy; this is committed
build/deployment evidence, not an independent live-website freshness check.

Current Mid Cap batch 1, built **2026-10-02T23:00:56+00:00**, instead reports
`ICICI exact Mid Cap scheme name is not unique`. Its rejected workbook was not
captured or bound to a hash. Do not attribute this different error to the retained
September workbook. Read-only inspection of `database-37075265591-1.zip` found no
successful October ICICI TER fetch with an archived hash. That ZIP's size and
checksum matched its manifest.

Current staged Direct TER coverage remains **29/34**; gaps are Bandhan, Bank of
India, ICICI, JM and WhiteOak. Mid Cap launch/public export remains disabled, and
the existing freshness and launch gates remain in force. A successful publisher
does not resolve individual source failures.

## Implemented diagnostics and validation

The diagnostic change retains the selected URL, actual returned SHA-256
and byte count whenever a downloaded ICICI workbook is rejected, while preserving
the original error. It changes no header, identity, numeric, reconciliation,
freshness or launch acceptance rule. Failed Markdown audit rows display the
selected source URL; hashes and byte counts remain in the JSON error record.

- All **852 repository tests passed**, including eight new real-OOXML diagnostic
  cases. They cover changed headers, inconsistent components, missing exact
  identity, corrupt worksheet CRC, unavailable downloads, accepted legacy rows,
  readiness exclusion and Markdown/JSON output.
- Python compilation, production JavaScript syntax and diff checks passed.
- Replaying the full verified **303,076-byte** workbook produced the expected
  rejection with its exact URL/hash/size, **zero recovered rows**, **zero
  production writes**, and public export disabled.

## Next source preflight

After the four approved network-domain additions in the environment draft are
applied, run the normal first-party discovery/fetch preflight with `archive=False`
and database connections forbidden. Capture each actual rejected workbook and
its provenance, then inspect its worksheet, exact family/plan identity, date,
headers and source reconciliation evidence. Compare this new response with the
retained source above. A parser correction requires that evidence and a failing
fixture from the actual response; relaxing validation to raise coverage is not
supported.
