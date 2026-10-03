# ICICI TER source investigation

Reviewed: 2026-10-03. Revised September source bytes pass the unchanged ICICI
parsers and have restored dated Small Cap evidence in verified production run
#689. Staged Mid Cap still rejects the blank October workbook and remains at
**29/34 Direct TER families**. The approved monthly fallback correction below is
implemented and verified locally, with fresh production collection still pending;
no parser acceptance rule changes.
The accompanying [JSON evidence](ICICI-TER-SOURCE-INVESTIGATION.json) separates
each response, replay and publication. No new source binary is tracked.

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

## Revised September source accepts without a parser change

The same September URL returned different bytes at
**2026-10-03T00:01:34.781429+00:00**: SHA-256
`ccf702746465273bb812eda2e91fbbb6166b47dccc5e98daeae4b6307590beb9`,
**306,500 bytes**. A normal read-only `_icici` preflight selected this source via
the successful financial-disclosure API and recovered the exact Mid Cap family.
The API category/file-list responses were not captured, so the metadata reason
for selecting September rather than October is unproved.

Independent inspection of `xl/worksheets/sheet1.xml` found **4,489 physical
rows**, compared with 4,391 in the retained workbook. Physical row 3 now has the
exact twelve A:L headers required by the existing parser, including explicit
**BER, brokerage, transaction cost and statutory levies including GST**. The
footer now references Regulations 66(7), 66(9) and 66(10). These are changes in
the published source, not aliases applied to the historical Base TER columns.

On the comparable September 29 target rows, only K within A:L changed: Mid Cap
Direct levies **0.31% → 0.21%**, Small Cap **0.51% → 0.39%**. The source also
adds unique September 30 rows; each target family now has thirty unique dates.
Actual unchanged Mid Cap and Small Cap parsers accepted those latest rows with
database connections forbidden:

| Exact family / physical row | Reporting date | Regular component sum / TER | Direct component sum / TER |
| --- | --- | ---: | ---: |
| ICICI Prudential Mid Cap Fund / 2043 | 2026-09-30 | 1.85 / 1.85 | 1.11 / 1.11 |
| ICICI Prudential Small Cap Fund / 4263 | 2026-09-30 | 2.10 / 2.10 | 1.18 / 1.18 |

All values remain subject to the original numeric and **0.02 percentage-point**
reconciliation rules. The new footer says `09-Sep-2026 05:00 AM` despite rows
through September 30; that inconsistent footer is not a verified generation
timestamp. No cause or exact time of the source revision has been established.

The accepted bytes are durably retained in
`sources-2026-10-p001-60472edbf22561b3.zip`: **35,078,701 bytes**, SHA-256
`05d86d33b253809cd540cbccb360f6009788e55754bbd11891462080b721ea37`.
The exact member `data/archive/cc/ccf702746465273bb812eda2e91fbbb6166b47dccc5e98daeae4b6307590beb9`
passed size, SHA-256 and ZIP CRC checks and is byte-identical to the independent
capture. The published manifest binds that pack to
`database-37080044847-1.zip`; the retention check downloaded only this source
pack and did not open a production database.

## October rejection is now bound to production bytes

The reviewed October URL is
`https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioOct2026.xlsx`.
The read-only capture at **2026-10-03T00:02:45.874978+00:00** returned SHA-256
`2b136282721167025a5362b339ff2199feea635a3f48d59c6375142a5394de3c`,
**5,010 bytes**. Its single worksheet has fourteen physical rows: title, plan
headings, old Base TER/regulatory/GST headers in row 3, a blank row and footnotes.
There are no dated scheme rows for either target family. The unchanged Mid Cap
parser rejects it with `ICICI TER workbook columns changed`.

Production batch 1 built **2026-10-03T00:01:54+00:00** records that exact URL,
hash, size and error. This binds the current rejection to the captured bytes.
The rejected hash is absent from the published source manifest; its binary
remains in ignored scratch. The URL alone does not establish which discovery
route production used.

## Verified publication and unchanged staging gates

[Production run #689 / 37080044847](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37080044847)
completed successfully on PR #351 code
`2fbd734cbb8539d2beae76043b2326cffc932386`: build completed at
**2026-10-03T00:25:05Z**, deploy at **00:25:23Z**. Generated evidence commit
`db5a0df35df887640411d374447bbc03c09f356b` has that code commit as its parent.
Cache-busted live status, funds and coverage reads at **00:27:07Z** matched the
committed status clock **00:24:33+00:00** and funds/coverage clock
**00:24:14+00:00**. The publication contains **36 funds, 143 series and 282,152
NAV observations**; the latest included NAV date remains **2026-10-01**.

Hosted ICICI Small Cap Direct BER **0.70%** and Total TER **1.18%** are now dated
**2026-09-30**, observed at **2026-10-03T00:05:19+00:00**, and carry the accepted
September hash. This Small Cap recovery does not update staged Mid Cap coverage.

Current staged counts are AUM **34/34**, Direct TER **29/34** (required 31),
benchmark identities **29/34** (required 31), current portfolios **21/34**
(required 28), and six current complete families. Remaining TER families are
Bandhan, Bank of India, ICICI, JM and WhiteOak. All **fourteen launch-input hashes**
were independently recomputed from the generated commit, with no mismatches or
input issues. Source-health and input-integrity gates pass, but `data_ready`,
`launch_ready` and `public_export_enabled` remain **false**. Portfolio freshness
is independently re-evaluated by the existing launch gate.

## Earlier production checkpoint remains separate

[Production run 37075265591](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37075265591)
completed successfully on merged PR #350 code
`b11f49c4d264ea860b9fc9c45f4149fceea902dd`: build completed at
**2026-10-02T23:22:44Z**, deploy at **23:23:02Z**. Generated commit
`031571cf94b7b2dd79ec69558ce16c370577ff04` has that code commit as its parent.
The committed export clock is **23:22:13+00:00**, latest included NAV
**2026-10-01**, with **36 funds, 143 series and 282,152 NAV observations**.
The original live-host check was blocked by environment network policy. Later
baseline reads verified this export before the #689 publication; the current
live checks above supersede that historical checkpoint.

That run's Mid Cap batch 1, built **2026-10-02T23:00:56+00:00**, reports
`ICICI exact Mid Cap scheme name is not unique`. Its rejected workbook was not
captured or bound to a hash. Do not attribute this different error to the retained
September or current October workbook. Read-only inspection of
`database-37075265591-1.zip` found no
successful October ICICI TER fetch with an archived hash. That ZIP's size and
checksum matched its manifest.

## Existing provenance diagnostics

The diagnostic change retains the selected URL, actual returned SHA-256
and byte count whenever a downloaded ICICI workbook is rejected, while preserving
the original error. It changes no header, identity, numeric, reconciliation,
freshness or launch acceptance rule. Failed Markdown audit rows display the
selected source URL; hashes and byte counts remain in the JSON error record.

- PR #351's **852 repository tests passed**, including eight real-OOXML diagnostic
  cases. They cover changed headers, inconsistent components, missing exact
  identity, corrupt worksheet CRC, unavailable downloads, accepted legacy rows,
  readiness exclusion and Markdown/JSON output.
- Python compilation, production JavaScript syntax and diff checks passed.
- Replaying the full verified **303,076-byte** workbook produced the expected
  rejection with its exact URL/hash/size, **zero recovered rows**, **zero
  production writes**, and public export disabled.

## Implemented correction and isolated verification

An isolated October 3 replay used the exact captured October and September bytes,
mocked only transport and a deliberately unavailable API, and forbade database
connections. Baseline `_icici` at `db5a0df` fetched the October file, stopped at its ZIP
signature, then rejected it outside the candidate loop; September was never
fetched. A scratch proof that validates each candidate with the unchanged
workbook parser rejected October and accepted September as **2026-09-30**, with
Mid Cap Direct TER **1.11%** and Regular TER **1.85%**. This simulated API failure
does not establish the discovery route of any production run.

The approved correction now validates each already reviewed current/previous-month
fallback candidate before selecting it, retains each rejected candidate's
URL/hash/size/error even if a later candidate succeeds, and records discovery
channel and API-error provenance. A transport failure records its URL/error
without inventing a hash. API acquisition failure or a non-PK response continues
to use the existing fallback route. A PK workbook selected by a successful API
still fails closed if workbook validation rejects it.

An actual-collector replay of the implementation accepted the exact September
bytes only after rejecting the exact October URL/hash/5,010-byte workbook. Its
successful result preserves the October rejection list and simulated API error,
and retains September 30, Direct **1.11%**, Regular **1.85%**. The API failure in
this replay was simulated, so it does not identify an earlier production route.
AST comparisons confirmed `_icici_workbook_result`, `_reconcile`, `_latest_exact`
and `_icici_fallback_sources` unchanged. Header, exact identity, unique latest
date, plan completeness, numeric and reconciliation rules remain unchanged; no
new source hosts or binaries are introduced.

All **865 repository tests passed**, including **13 monthly-selection tests**;
the focused ICICI run passed **35 tests**. These use actual-source-derived OOXML
fixtures and cover rejected current month followed by accepted previous month,
both candidates rejected, transport failures, invalid API-selected content,
retained provenance, unchanged acceptance checks and fiscal-year/month rollover.
The full captured binaries were separately replayed against the implemented
collector. Python compilation and five production JavaScript syntax checks also
passed. These checks do not establish fresh production coverage.

The accepted reporting date must remain **September 30**, not October 3. Existing
TER readiness counts valid recovered dated rows but has **no independent TER row
age cutoff**. Report-generation freshness and all launch gates still apply;
three-day-old September evidence is not an October observation or a separate TER
freshness certification. A fresh production run must establish any staged
coverage change before publishing new counts or enabling Mid Cap.
