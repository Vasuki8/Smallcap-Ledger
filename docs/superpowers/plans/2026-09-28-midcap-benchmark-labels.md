# Mid Cap primary benchmark label recovery

## Scope and approved continuation
Continue the existing benchmark audit after the Samco repair already merged in PR #293. Do not reimplement the freshness or Samco tasks from the older handoff. Base: `68774e67c80d5373d36216cc885f7ad841caef4d`.

Bounded approach: extend existing benchmark batch 2 with Axis and Mirae fund-specific HTML contracts. Do not add another producing artifact: the existing 14-input launch-integrity contract remains unchanged. Keep public export disabled, thresholds unchanged, and actual benchmark series availability separate from reported identity.

## Observed source contracts
Isolated read-only diagnostic run `36426086431`, job `108940266495` inspected four official pages with database access forbidden and `archive=False`.

- Axis: exact H1 `Axis Mid Cap Fund`; primary banner `Benchmark Returns` / `BSE Midcap 150 TRI`; explicitly labeled percentage and rupee performance columns agree. `Nifty 50 TRI` is an additional comparator, not primary. Response SHA-256 `9173f7a0ebb2f48d1777fd5f9fd94d7f849526d64b3e395da25112974691c7b7`.
- Mirae: exact H1 `Mirae Asset Midcap Fund`; `div.fund_fact_text` pairs `benchmark index` with `NIFTY Midcap 150 (TRI)`. Response SHA-256 `06163cec57d3111a57bdc4922a573987056acba795fb84b5ad46af62199c1d0d`.
- ABSL's discovered empower factsheet is older; no new coverage claim from it in this slice. Invesco's returned page lacked usable scheme/benchmark HTML; it is not counted or replaced with a category default.
- The diagnostic branch/workflow is throwaway evidence, not included in the production branch.

## Implementation and validation ledger
- [x] Write 23 parser/source-boundary tests; observe failures before the new parser exists.
- [x] Implement exact heading plus source-specific label parsing. Preserve publisher wording, role, source URL/hash, observation time and the original evidence excerpt. Do not infer TRI or take benchmark effective dates from NAV/AUM/performance timestamps.
- [x] Write seven integration/provenance tests against unchanged batch/readiness functions; observe seven failures, then wire the two sources into batch 2 and retain independent copies of source evidence.
- [x] Run all 30 focused tests and syntax checks locally. Original batch/readiness modules were blob-hash verified before modification. The local tree uses dependency shims only for legacy transport/database boundaries; it is NOT the full repository suite and the shims are not uploaded.
- [ ] Run full GitHub regression and actual two-source preflight before merge.
- [ ] Verify exact production reports and deployment after merge; update the focused handoff with current counts, failures and next task.

Ruling: require primary Axis banner/table agreement and both primary column roles, rather than select the first nearby index. Fail closed on conflicting responsive copies or changed source structure. The registered pages have no explicit benchmark effective date, so that field stays null; Axis performance reporting date is retained separately.

Ruling: decode these registered UTF-8 responses explicitly. A synthetic rupee-label fixture exposed BeautifulSoup's otherwise incorrect windows-1252 auto-detection; strict UTF-8 preserves the actual Benchmark(₹) role and rejects malformed encoding.

Ruling: preserve all existing legacy benchmark readers and source records in this bounded extension; do not claim the new fund-specific parser retrospectively revalidated every older benchmark. No public UI, live Mid Cap record, source permission or dependency changes.
