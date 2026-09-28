# Mid Cap launch readiness

Data ready: **false** · launch ready: **false**.

| Gate | Actual | Required | Pass? | Remaining |
| --- | ---: | ---: | --- | ---: |
| AUM | 34 | 34 | true | 0 |
| Direct TER | 31 | 31 | true | 0 |
| Reported benchmark identity | 12 | 31 | false | 19 |
| Current portfolio evidence | 12 | 28 | false | 16 |

- Scheme/NAV identity history gate: **true** (135 / 135 codes; 0 history failures).
- Source-fetch health: **true**.
- Category-aware public surface dry run: **false**.
- Complete current portfolios (tracked, not a hard launch threshold): **2**.

## Current blockers

- benchmark_identity
- current_portfolio_evidence
- category_aware_public_surface

## Policy

- aum: 100% of staged families
- direct_ter: at least 90% of staged families; remaining gaps must stay explicit
- benchmark_identity: at least 90% exact first-party reported benchmark identity
- current_portfolio_evidence: at least 80% current regulatory month-end evidence
- portfolio_completeness: tracked separately; not a launch gate when partial coverage is explicitly labelled
- public_surface: category-aware exporter/API/UI dry run must pass before the switch is enabled
