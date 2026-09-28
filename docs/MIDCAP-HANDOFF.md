# Mid Cap backend handoff

Use this handoff with current generated readiness artifacts and the exact GitHub Actions run. Old audits and source preflights are historical evidence, not proof of a new production recovery.

## Latest verified checkpoint

Code PR **#293**, merge `ee24a5b27bdd81e46e2ea1372a77a7b84e5d6a6a`, repairs the Samco Mid Cap TER collection path. The tested branch head is `bd7a34f890a3846d9b7445af01bd90e12a0d1d8f`.

Pre-merge validation: all **657 repository tests** passed (631 existing plus 26 new) in branch run **36383887287**, job **108805105001**. The same job passed the actual Samco source preflight with database/archive access forbidden. PR regression **36383910860** and Research UI checks **36383910851** also passed. Local tests used a limited dependency-facade scratch harness; the full-suite claim comes from actual repository CI, not that harness.

Production [run **#648 / 36384128565**](https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36384128565) completed successfully on **2026-09-28 at 06:05:16 UTC**. Build job **108805815609** and deploy job **108807567741** both passed. Verified stages include staged source audits, launch evaluation, regression tests, site generation, generated-data/download validation, archive publication, status recording and Pages deployment.

Refreshed artifacts were inspected at **`68774e67c80d5373d36216cc885f7ad841caef4d`**. Portfolio readiness was evaluated at **2026-09-28T06:01:48.185913+00:00** and launch readiness at **06:01:48.260975 UTC**. All **14/14 audit-input checks pass**, with **`input_issues=[]`** and **`audit_input_integrity=true`**. These are current-run artifact checks, not a claim that all fund sources are covered.

## Completed Samco investigation: data existed, but collection missed it

The previous verified run #647 reported 30/34 TER coverage with Samco unresolved. Investigation found two observable causes: the category-17 request returned zero rows for Samco, while the exact AMC's all-category feed returned the fund on page 2; the local validator also rejected the publisher's plural category prefix, `Equity Schemes - Mid Cap Fund`.

This demonstrates an AMFI filter/label inconsistency and a local validation limitation. It does not establish AMFI's internal reason or show that Samco stopped publishing expenses. The previous zero-row diagnostic remains valid for the specific filtered requests, but cannot be interpreted as absence from every official source.

The new fallback applies only to **Samco Mid Cap Fund owned by Samco Mutual Fund** when it remains unresolved after ordinary collection. The official AMC selector is resolved dynamically. The accepted NSDL identity is `SAMC/O/E/MIF/25/10/0013`; similarly named Small Cap and Large & Mid Cap schemes do not match.

All reported pages must succeed within a five-page/two-megabyte-per-page bound. Every row must belong to the requested AMC/month; pagination totals must stay stable and complete. Both plans' published TER values must be finite and reconcile with their BER, brokerage, transaction-cost and statutory-levy components. Missing values, conflicts, incomplete pages and future/wrong-period data remain explicit failures, not partial success or zero fees. The current-month request rolls forward automatically.

The source audit and combined TER view retain exact API URL, response SHA-256, source row, original published fields, NSDL identity and observation time. No older value is copied in to cross a threshold. No new audit file is introduced, so the existing fourteen-input integrity contract is unchanged.

The actual read-only preflight examined all **243 AMC records across three pages**, retaining **18 exact daily Samco observations**. The subsequent production report independently confirms **Direct TER 1.58%**, **Regular TER 3.00%**, reporting date **2026-09-25**. Direct BER is **0.81%**, not the Direct TER.

Production source observation: **2026-09-28T05:59:19.600100+00:00**. Exact source: `https://www.amfiindia.com/api/populate-te-rdata-revised?MF_ID=74&Month=09-2026&strCat=-1&strType=1&page=2&pageSize=1000`, response row **44**, SHA-256 **`3c2afe6b1046bb5e0ebb3f79aab5fe0089a23fecf794e8985e10fe86b64ece66`**. The original published row, including category, NSDL, both BER values and component totals, remains in `docs/MIDCAP-TER-READINESS.json`. The September 28 observation/summary times are not substituted for the September 25 reporting date.

## Current staged readiness

| Measure | Verified production count | Existing launch data policy |
| --- | ---: | ---: |
| Scheme/NAV history | 135 / 135 codes; 0 history failures | All staged codes |
| AUM | 34 / 34 families | 34 / 34 |
| Direct TER | **31 / 34** | At least 31 / 34 |
| Reported benchmark identity | 12 / 34 | At least 31 / 34 |
| Current portfolio evidence | 16 / 34 | At least 28 / 34 |
| Complete current portfolios | 4 / 34 | Tracked separately |
| Audit-input integrity | 14 / 14 verified; no input issues | All required inputs |

The fee requirement passes again: **21 families via AMFI plus 10 via first-party AMC evidence**. The remaining TER gaps are **Bandhan, Bank of India and WhiteOak Capital**. This restores the previous 31/34 coverage using a newly verified Samco source observation, not a copied historical value.

The four complete portfolios remain **HDFC, Mirae Asset, Invesco India and Sundaram**. Current portfolio coverage and completeness did not expand in this TER slice. The required portfolio reporting month-end remains **2026-08-31**.

Launch is still **`data_ready=false`**, **`launch_ready=false`**, **`public_export_enabled=false`**. Current blockers are reported benchmark coverage, current portfolio coverage and the separate category-aware public surface. The numerical requirements remain **19 more benchmark identities** and **12 more current portfolio-evidence families**; NAV/AUM/TER and input integrity currently pass. Thresholds were not relaxed.

## Existing safeguards remain in force

PR #290's freshness-safe portfolio reconciliation is complete and must not be reimplemented. Reporting date precedes completeness; old complete portfolios cannot defeat current partial ones. The existing ten-day publication grace and numerical thresholds are unchanged. Valid stale evidence remains visible but uncounted. Source identity, hashes, observation dates and diagnostic alternatives stay preserved.

`MIDCAP_AUDIT_STARTED_AT` is set before staged collection. Five core reports and nine producing batches must belong to the run and pass input checks. Fresh summaries do not make old input files or source observations new. The launch evaluator independently recomputes current portfolio coverage. Missing/failed inputs cannot silently create a green launch signal.

Mid Cap remains staged, with public export disabled. These source/readiness changes do not promote fees, holdings or portfolios to live tables. Normal Small Cap/archive maintenance still writes during the publisher workflow; do not describe the whole workflow as making zero database writes. No new permissions, paid infrastructure, dependencies, public UI or automation tasks were added.

## Source corrections and limitations to retain

- **Mahindra:** the original 63 positions included four sector headings; the corrected 59 issuers, 16 sector subtotals and 97.71% equity weight reconcile. It remains equity-only partial. Keep post-total-footer, duplicate, invalid-weight and responsive-table guards. Correction history remains in `docs/MIDCAP-EVIDENCE-CORRECTIONS.md`; this was a parser correction, not a trade.
- **Sundaram:** the discovery card's old AUM date is separate from its portfolio date. The exact MC workbook independently proves August 31. Preserve fund-code/category/source checks and validate the workbook's own reporting date; never borrow AUM/NAV timestamps.
- **Kotak:** earlier isolated preflight evidence is not current portfolio coverage. Preserve the exact heading/date checks on variable fund-page responses and use only the latest accepted production report.
- **Bandhan, Bank of India and WhiteOak TER:** keep remaining source limitations explicit. Samco's workaround must not be generalized to other AMCs without returned-source proof and separate tests. A filtered empty response alone does not prove absence from all official channels.

## Next coherent task: reported benchmark identities

Samco recovery is now production-verified. Resume the larger reported-benchmark coverage deficit; do not repeat the completed Samco investigation or PR #290 freshness work. Use `docs/MIDCAP-BENCHMARK-READINESS.json::remaining_families`, not assumptions based on AMC or portfolio coverage. Prioritize a coherent group of existing portfolio-covered families with exact first-party factsheet/API evidence, such as Invesco India, Mirae Asset, ICICI Prudential, Axis, ABSL, SBI and UTI where they remain missing. Franklin, UTI and JM's earlier product-page identity failures must not be bypassed by weakening matching.

Keep primary benchmark identity separate from additional comparators, and TRI separate from price-return variants. Preserve the publisher's actual wording and effective/reporting dates. Never infer the usual category benchmark, supply an unavailable series, or silently reuse the Small Cap comparator.

Then expand remaining current portfolio evidence using the same ownership/date/completeness checks, including a dependable source for Kotak. Verify Taurus and WhiteOak registrations before claiming full category-wide document coverage. Every source-recovery slice needs full pre-merge tests, exact production evidence and an updated handoff.

## Launch remains a separate decision

Data policy: all 135 scheme/NAV codes, all 34 AUM families, at least 31 Direct TER families, at least 31 reported benchmark identities, and at least 28 current portfolio-evidence families, plus healthy verified inputs. Complete portfolios remain a distinct measure; partials must stay visibly partial. These are tracker product-quality thresholds, not regulatory rules.

After the data gates pass, separately validate category-aware exporter/static JSON/API/UI routing, actual exportable fee/holding data, source/freshness/partial labels, correct benchmark series or explicit absence, and Small Cap non-regression. A readiness report cannot enable the public category by itself. No browser-level visual/mobile pass is claimed for this backend task.

The existing daily ChatGPT launch-readiness check is unchanged; do not create another. It cannot merge or publish. Notification channel settings were not rechecked in this slice.

## Source-of-truth artifacts

- `docs/MIDCAP-SOURCE-COVERAGE-AUDIT.json`: AMFI source responses, fallback checks, Samco raw row, exact reporting/observation dates and hashes.
- `docs/MIDCAP-TER-READINESS.json` and `.md`: combined current fee evidence and unresolved families.
- `docs/MIDCAP-LAUNCH-READINESS.json`: current threshold/input-integrity evaluation, not a switch.
- `docs/MIDCAP-PORTFOLIO-READINESS.json` and producing batches 1–5: current/stale holdings evidence, source identity and completeness.
- `docs/MIDCAP-BENCHMARK-READINESS.json` and its two batches: reported identities, not proof of available comparison series.
- `deployment/midcap-history-status.json` and `deployment/update-status.json`: history and publication state, separate from fund-source coverage.
- `docs/superpowers/plans/2026-09-28-samco-ter-recovery.md`: investigation and execution ledger.
