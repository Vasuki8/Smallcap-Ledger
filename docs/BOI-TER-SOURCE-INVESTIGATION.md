# Bank of India TER source investigation

Reviewed: October 2, 2026 (America/Toronto). Capture clocks below are UTC.
The exact acquired workbook contains valid dated Mid Cap
source rows beyond its declared worksheet dimension. The approved bounded
collector is **implemented and verified by isolated replay**, with independent
review approved; fresh production collection remains pending. This replay does not establish
production recovery. [JSON evidence](BOI-TER-SOURCE-INVESTIGATION.json) preserves the response
identity, raw row facts, historical gap and approved boundaries. No source binary
is tracked.

## Exact acquired September source

The normal read-only capture at **2026-10-03T00:44:51+00:00** acquired:

- URL: `https://www.boimf.in/docs/default-source/investorcorner/total-expense-ratio/expense_ratio_01092026_to_30092026.xls?sfvrsn=1b375908_8`
- SHA-256: `4a4d8482f052c438a5dd664def2c8277c7ecaa5a311c0f3902307e7fdb62fc75`.
- Size: **56,375 bytes**, independently checked against the captured bytes.
  The response is XLSX despite its `.xls` URL and `application/vnd.ms-excel`
  content type.

A second normal provider fetch before parser implementation at
**2026-10-03T01:54:00.759316+00:00** returned the same verified hash and size.

The sole worksheet is **`TER_UPLOAD_FORMAT`**, stored in
**`xl/worksheets/sheet1.xml`**. Its declared dimension is `A1`, but raw XML
contains **713 physical rows**. Headers and identities use shared strings;
dates are styled Excel serials, decoded as dates; TER values are plain numeric
percentage points. A worksheet reader must reset dimensions before iteration,
decode shared strings and date styles, and preserve the numeric units.

There are **29 exact Mid Cap rows**, dated September 1–29, with one NSDL identity
`BOIA/O/E/MIF/25/06/0023`. The unique latest row is **physical row 436**, source
name **Bank of India Mid Cap Fund**, reporting **2026-09-29**:

| Plan | BER | Brokerage | Transaction cost | Statutory levies | Component sum | Published TER |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regular | 2.02 | 0.06 | 0.00 | 0.47 | 2.55 | 2.55 |
| Direct | 0.98 | 0.06 | 0.00 | 0.28 | 1.32 | 1.32 |

Both published totals pass the existing **0.02 percentage-point** reconciliation
tolerance. Actual source zeros must remain zeros; missing components must not
be converted to zero. The NSDL identifier does not establish an AMFI-code or
ISIN mapping. These observations are local source evidence, not accepted staged
production coverage or verified durable publication retention.

## Earlier response and discovery limits

The earlier read-only diagnostic in
[midcap-ter-final4-file-diagnostic.json](../deployment/midcap-ter-final4-file-diagnostic.json)
records the same URL, **48,497 bytes**, SHA-256
`27c3ac086b2c293c89922b3499ad5a1b28298080cbb585bd5788b51f983aa3e7`.
It displayed a 1×1 `TER_UPLOAD_FORMAT` sheet containing `NSDL Scheme Code`, but
did not inspect raw rows beyond that dimension or retain the binary. Its capture
timestamp is not recorded. Bounded searches of the downloaded historical/current
manifests and isolated archive records found no matching retained hash.
That different, unavailable response cannot prove that data rows were absent
and cannot be assigned the current workbook's raw rows or hash.

The official disclosure page
`https://www.boimf.in/siddisclosures/scheme-expense-ratio` returned HTTP 200 at
**2026-10-03T01:37:09.561842+00:00**: **72,147 bytes**, SHA-256
`0a639d79b1d83aa3cb0c5c382590d9f046d4dede83229b96ed01e3ce6eef1f3d`.
No matching TER workbook hrefs were extracted. Dynamic discovery and an October
workbook remain unverified; the September filename does not authorize a guessed
October URL.

## Implemented approved collector contract

The collector may fetch only the reviewed September URL when its source month
is the evaluation month or immediately previous month. It is eligible on
**2026-10-03**; **November 2026 must reject it before fetching**. No dynamic
discovery or new monthly URL is introduced.

Require the exact sole worksheet and A:M header schema. Match the normalized
exact family and expected nonempty NSDL identifier in both directions: the
family cannot appear under another identifier, and the expected identifier
cannot identify another family. Emit exactly **`BANK OF INDIA MID CAP FUND`** for
staged reconciliation. Require valid source dates within the reviewed September
period and no later than evaluation, one latest row, and complete Regular and
Direct plan values. An invalid relevant date must fail the workbook rather than
rescuing an earlier valid row.

Require explicit finite numeric components and published totals in **0–5**
percentage points, allowing actual zero. Preserve the plain percentage-point
format and existing reconciliation rules and tolerance. Return the original
reporting date and actual acquired URL, SHA-256 and byte count; preserve these
fields and the original error on downloaded-source rejection. A transport
failure cannot acquire an invented hash. The observed hash is evidence for a
fixture, **not a fixed acceptance allowlist**: a future response must satisfy
the same contract with its own actual provenance.

Use existing bounded source transport with no database writes. Readiness,
report-generation freshness, portfolio freshness and launch thresholds remain
unchanged. Existing TER readiness has no separate row-age cutoff; September 29
must remain September 29 rather than becoming the fetch date.

## Verified production baseline and local implementation checks

Publisher [#690 / 37084586835](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/37084586835)
generated `372804172faa40f66774a3137aa7a5aa7106be4e`, whose first parent is PR #352
code `19fa310d9b34476883febe4f771955fe909f1422`. Exact-commit verification passed
all **14 input hashes and original clocks**, with zero TER, benchmark, portfolio
or launch mismatches. Baseline counts remain Direct TER **30/34**, benchmarks
**29/34**, current portfolios **22/34**, and six current complete families.
`data_ready`, `launch_ready` and `public_export_enabled` are **false**.

At **2026-10-03T02:04:55+00:00**, an isolated actual-collector replay of the full
freshly captured workbook recovered the expected family and NSDL, September 29,
Direct **1.32%**, Regular **2.55%**, and the actual **56,375-byte** source hash.
Database access was forbidden and production writes were zero. AST comparisons
confirmed existing collector classes and validation functions unchanged; only
the `collect` dispatcher gained the new BOI error-provenance branch.

All **17 BOI tests passed** after the initial run recorded **38 failures and zero
errors**. The full repository run passed **882 tests**. Source-derived OOXML
fixtures cover the incorrect dimension, shared strings, typed dates, conflicting
identity, invalid dates and latest rows, strict numeric units and missing values,
source provenance, current-month eligibility and November rejection. Python
compilation, five production JavaScript syntax checks and diff checks passed.
Independent review approved the change without findings and separately passed
the 17 BOI tests, real-source replay and year/month probes.

A read-only readiness simulation appended this result to the exact #690 baseline
and produced **31/34** Direct TER families, leaving Bandhan, JM and WhiteOak, with
public export still disabled. This is a **historical-input simulation, not
verified production coverage**. Production remains at the #690 **30/34** baseline.
Verify a fresh publisher's source records,
fourteen inputs and gates before claiming production BOI recovery or new counts.
