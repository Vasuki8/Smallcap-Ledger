# Samco Mid Cap TER recovery implementation plan

> Use superpowers:executing-plans to complete this bounded repair inline.

**Goal:** Recover exact currently observable Samco TER without copying old fees or relaxing launch/identity rules.
**Architecture:** Keep the existing category-scoped audit as primary. Only unresolved, exactly staged Samco gets a bounded all-category request for its resolved AMC. Validate complete pagination, exact NSDL/category/name, date, and both plans' published TER/component reconciliation before returning any rows. Preserve source proof into the current readiness reports.
**Tech stack:** Existing Python, standard library, providers.fetch and unittest. No dependencies added.
**Spec:** docs/MIDCAP-HANDOFF.md at 31cc0a811f1a1469f346c3b1847f247f9523c44d, Samco TER task, plus the verified source observations below.

## Constraints and review focus
No live Mid Cap financial writes, automatic public export, threshold changes, Small Cap comparator substitutions or source-access changes. No industry sweep. Entire AMC page set must succeed before any fallback result is accepted. Validate future dates, response-scoping mismatches, empty feeds, conflicting duplicates and partial/truncated pagination. Keep BER distinct from total TER and evidence observation distinct from reporting dates.

## Verified investigation
Two isolated read-only GitHub runner probes (not production recoveries):
- 36382515647 / job 108801018403 at 05:34 UTC on 2026-09-28: exact official selector Samco Mutual Fund -> MF_ID=74. Category 17 query returned 0 rows, SHA-256 0ddf746cc199ec92af9fda334cae90bd5c727bea58428176d8c43ca7b5f1c308. All-category current-month query reported 243 rows in 3 pages, with server pageSize=100 despite a 1000 request.
- 36382618658 / job 108801314237 at 05:36 UTC: all-category page 2 contains exact Samco Mid Cap Fund, NSDL SAMC/O/E/MIF/25/10/0013, category `Equity Schemes - Mid Cap Fund`, both plans, latest reporting date September 25, 2026. Published Direct TER 1.5800, Regular TER 3.0000; Direct BER is 0.8100 and is not substituted for TER.
- Page 1 SHA-256 bdc42aad40797d2d070c038af788a97204cb763fd4a80589aefdde2ad7f04b40; page 2 3c2afe6b1046bb5e0ebb3f79aab5fe0089a23fecf794e8985e10fe86b64ece66; page 3 1458364ed9bc1dd67e96797e29f0d5001c05ce238bc074e075edd422361bfe51.
- URL contract: `https://www.amfiindia.com/api/populate-te-rdata-revised?MF_ID=74&Month=09-2026&strCat=-1&strType=1&page=2&pageSize=1000`. New code resolves AMC ID dynamically and requests the current month; the observed ID/value/date are not pasted into financial results.

Cause established at the observable boundary: the filtered query omits a scheme present in the broader exact-AMC feed, and the existing local category validator rejects AMFI's plural `Equity Schemes` wording. AMFI's internal reason for the filter inconsistency is unknown. This is not evidence of AMC withdrawal or absence of published TER.

## Tasks and ledger
- [x] Inspect latest handoff/main and compare prior/current fee artifacts; isolate non-publishing source probes.
- [x] Add failing tests proving the plural category and filtered omission lose valid evidence. Original source gives 3 failing integration assertions; provenance passthrough adds another observed failing assertion.
- [x] Add pure bounded Samco feed validator and integrate only for the unresolved exactly owned family; preserve original source row and hashes in both audit and reconciliation.
- [x] Run 26 focused local tests and syntax checks. Full package dependencies are unavailable in the scratch checkout, so the local source-function harness supplies dependency facades; this is not the repository-wide suite.
- [ ] Run full repository regressions and actual Samco source preflight on the development branch, inspect final diff, then merge with exact-head guard.
- [ ] Verify refreshed production reports and terminal deployment; update docs/MIDCAP-HANDOFF.md with exact source/coverage/remaining blockers.

The diagnostic-only branch/workflow is not included in this patch. Existing pre-merge evidence CI receives a Samco-specific read-only preflight on the designated development branches; unrelated batch-5 probes are preserved. No new audit artifact is introduced, so the existing 14-input launch-integrity contract is unchanged.
