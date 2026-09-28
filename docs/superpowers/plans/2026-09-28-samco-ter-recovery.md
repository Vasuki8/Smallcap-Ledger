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
- 36382515647 / job 108801018403 on 2026-09-28: exact official selector Samco Mutual Fund -> MF_ID=74. Category 17 query returned 0 rows, SHA-256 0ddf746cc199ec92af9fda334cae90bd5c727bea58428176d8c43ca7b5f1c308. All-category current-month query reported 243 rows in 3 pages, with server pageSize=100 despite a 1000 request.
- 36382618658 / job 108801314237 on 2026-09-28: all-category page 2 contains exact Samco Mid Cap Fund, NSDL SAMC/O/E/MIF/25/10/0013, category `Equity Schemes - Mid Cap Fund`, both plans, latest reporting date September 25, 2026. Published Direct TER 1.5800, Regular TER 3.0000; Direct BER is 0.8100 and is not substituted for TER.
- Page 1 SHA-256 bdc42aad40797d2d070c038af788a97204cb763fd4a80589aefdde2ad7f04b40; page 2 3c2afe6b1046bb5e0ebb3f79aab5fe0089a23fecf794e8985e10fe86b64ece66; page 3 1458364ed9bc1dd67e96797e29f0d5001c05ce238bc074e075edd422361bfe51.
- URL contract: `https://www.amfiindia.com/api/populate-te-rdata-revised?MF_ID=74&Month=09-2026&strCat=-1&strType=1&page=2&pageSize=1000`. New code resolves AMC ID dynamically and requests the current month; the observed ID/value/date are not pasted into financial results.

Cause established at the observable boundary: the filtered query omits a scheme present in the broader exact-AMC feed, and the existing local category validator rejects AMFI's plural `Equity Schemes` wording. AMFI's internal reason for the filter inconsistency is unknown. This is not evidence of AMC withdrawal or absence of published TER.

## Tasks and ledger
- [x] Inspect latest handoff/main and compare prior/current fee artifacts; isolate non-publishing source probes.
- [x] Add failing tests proving the plural category and filtered omission lose valid evidence. Original source gives 3 failing integration assertions; provenance passthrough adds another observed failing assertion.
- [x] Add pure bounded Samco feed validator and integrate only for the unresolved exactly owned family; preserve original source row and hashes in both audit and reconciliation.
- [x] Run 26 focused local tests and syntax checks. Full package dependencies are unavailable in the scratch checkout, so the local source-function harness supplies dependency facades; this is not the repository-wide suite.
- [x] Run full repository regressions and actual Samco source preflight on the development branch, inspect final diff, then merge with exact-head guard.
- [x] Verify refreshed production reports and terminal deployment; update docs/MIDCAP-HANDOFF.md with exact source/coverage/remaining blockers.

The diagnostic-only branch/workflow is not included in this patch. Existing pre-merge evidence CI receives a Samco-specific read-only preflight on the designated development branches; unrelated batch-5 probes are preserved. No new audit artifact is introduced, so the existing 14-input launch-integrity contract is unchanged.

## Completed verification checkpoint

- Code PR **#293** merged with an exact-head guard as `ee24a5b27bdd81e46e2ea1372a77a7b84e5d6a6a`; tested head `bd7a34f890a3846d9b7445af01bd90e12a0d1d8f`.
- Branch run **36383887287**, job **108805105001**, passed syntax and **657 repository tests / OK** (631 existing + 26 new). Its database/archive-forbidden actual Samco source preflight also passed. PR regression **36383910860** and Research UI checks **36383910851** passed before merge. The local scratch harness is not the full-repository test evidence.
- Whole-patch review confirmed exactly eight intended files, without the investigation-only workflow or changes to the daily publisher, public UI, dependencies or launch thresholds.
- Exact production **#648 / 36384128565** completed successfully on **2026-09-28 at 06:05:16 UTC**. Build **108805815609** and deploy **108807567741** passed, including source audits, regression tests, generated-site/data validation, archive publication and status recording.
- New artifacts inspected at **`68774e67c80d5373d36216cc885f7ad841caef4d`** independently confirm Samco Direct TER **1.58%**, Regular TER **3.00%**, reported **2026-09-25**. Production observation is **2026-09-28T05:59:19.600100+00:00**, source page 2 row 44, SHA-256 **`3c2afe6b1046bb5e0ebb3f79aab5fe0089a23fecf794e8985e10fe86b64ece66`**. The original published row and components are retained; BER is not substituted for total TER.
- Current readiness: AUM **34/34**, Direct TER **31/34** (21 AMFI + 10 AMC), benchmark identity **12/34**, current portfolio evidence **16/34**, complete current portfolios **4/34**. All **14** input-integrity checks pass with no input issues. Launch/public export remain false. Remaining TER gaps are Bandhan, Bank of India and WhiteOak.
- The updated handoff makes exact first-party benchmark recovery the next coherent task; the current numerical deficits are **19 benchmark identities** and **12 current portfolio-evidence families**, followed by the separate category-aware public-surface dry run.

Verification scope: full repository CI, actual read-only AMFI responses, refreshed production artifacts and terminal build/deploy. No direct browser visual/mobile pass is claimed. Source permissions, original evidence and the existing daily launch-readiness automation are unchanged.
