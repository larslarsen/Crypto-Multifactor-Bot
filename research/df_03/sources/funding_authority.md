# Source authority note — Point-in-time funding cashflow (DF-03 synthesis)

Synthesis target: whether accepted repository evidence authorizes point-in-time funding
cashflows (realized funding payments as position-dependent cashflows in a common numeraire).
Evidence synthesis only; no new factual inference.

## What is repository-native (used here)
Only accepted inventory, hashes, decisions, and prior accepted review findings are used.
The sixteen artifacts registered in `EVIDENCE_REGISTER.csv` span: sprint_002/06 (DF-03
question/test), sprint_003/08 (RD-02 feasibility), FUND-001 ticket/report/REVIEW-0093,
FUND-002 ticket/report/matrix/REVIEW-0098, FUND-003 ticket/report/matrix/REVIEW-0110,
FX-003 ticket/REVIEW-0114/matrix.

## Preserved acceptances (exact)
- FUND-001 readiness/substrate remains accepted.
- Binance and OKX bounded observations remain valid evidence.
- FUND-002 and FUND-003 remain accepted with NO_IMPLEMENTATION_AUTHORITY.
- FX-003 remains NO_PRIMARY_SOURCE_AUTHORITY.
- Sprint-003 RD-02 was a feasibility statement/next action, not implementation authority.

## Gate results (all blocking)
- G01 FAIL_PARTIAL: Binance archive fields are `calc_time`, `funding_interval_hours`, `last_funding_rate` (matched against REST `fundingRate`/`fundingTime`, not relabeled); `calc_time` classification remains incomplete. OKX `fundingTime` settlement semantics pass only for accepted scope.
- G02 FAIL_PARTIAL: Binance archive rate field `last_funding_rate` (not relabeled as `fundingRate`) unit/sign/formula fail; OKX archive predicted-vs-realized distinction partial.
- G03 FAIL_PARTIAL: interval/formula history incompletely versioned; observed intervals do not establish historical rules.
- G04 FAIL_PARTIAL: Binance historical availability partial; OKX only conservative 2026 bound, not historical publication-time authority.
- G05 FAIL_UNKNOWN: funding-specific replacement/correction history not established.
- G06 FAIL_PARTIAL: Binance raw lineage passes bounded samples; OKX full request identity fails.
- G07 FAIL_UNKNOWN: intended internal acquisition/retention licensing unestablished or ambiguous (Binance E07/E08; OKX E11/E12). Tickets/acceptances record final status but are not the primary legal-semantics evidence.
- G08 FAIL_BLOCKED: provider funding-rate events are not position-dependent realized cashflows (FUND-001 E03/E04/E05); required notional/side/mark/index inputs absent (provider rate-event evidence E07/E11); accepted FX-003 evidence (E14/E15/E16) does not authorize USD conversion.

## Decision
`NO_POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY`. No funding-event normalizer, realized cashflow,
CARRY factor, USD conversion, schema, migration, or next ticket authorized.
