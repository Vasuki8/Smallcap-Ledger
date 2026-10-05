# Mid Cap launch readiness

Evaluated: 2026-10-05T21:36:32.789177+00:00

Data ready: **false** · launch ready: **false**.

| Gate | Actual | Required | Pass? | Remaining |
| --- | ---: | ---: | --- | ---: |
| AUM | 34 | 34 | true | 0 |
| Direct TER | 32 | 31 | true | 0 |
| Reported benchmark identity | 28 | 31 | false | 3 |
| Current portfolio evidence | 21 | 28 | false | 7 |

## Current blockers

- benchmark_identity
- current_portfolio_evidence
- category_aware_public_surface

## Input integrity


## Policy

- aum: 100% of staged families
- direct_ter: at least 90% of staged families; remaining gaps stay explicit
- benchmark_identity: at least 90% exact first-party reported benchmark identity
- current_portfolio_evidence: at least 80% current regulatory month-end evidence
- portfolio_completeness: tracked separately; partial records are not relabelled
- public_surface: category-aware exporter/API/UI dry run must pass separately

## Notes

- Thresholds are product-quality policy, not regulatory rules, and are unchanged.
- Current portfolio counts are independently re-evaluated from source evidence at this clock.
- Benchmark identity is not benchmark-series availability; the dry run must show the correct series or its absence.
- No silent Small Cap comparator, inferred values or automatic public-category promotion is authorized.
