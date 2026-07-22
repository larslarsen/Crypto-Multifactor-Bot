# DF-03 — Point-in-Time Funding Cashflow Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY
**Priority:** P0
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Authorized under:** REVIEW-0132

## Objective
Determine whether accepted repository evidence authorizes point-in-time funding cashflows
(realized funding payments as position-dependent cashflows in a common numeraire). Evidence
synthesis only.

## Gate results (8, all blocking)
- **G01 FAIL_PARTIAL** (blocking Yes) — Binance archive fields are `calc_time`, `funding_interval_hours`, `last_funding_rate` (matched against REST `fundingRate`/`fundingTime`, not relabeled); `calc_time` classification remains incomplete. OKX `fundingTime` settlement semantics pass only for its accepted scope.
- **G02 FAIL_PARTIAL** (blocking Yes) — Binance archive rate field `last_funding_rate` (REPO, not relabeled as `fundingRate`) unit/sign/formula fail (not a normalized, position-dependent cashflow). OKX archive predicted-vs-realized distinction remains partial.
- **G03 FAIL_PARTIAL** (blocking Yes) — interval and formula history are incompletely versioned; observed intervals do not establish historical rules.
- **G04 FAIL_PARTIAL** (blocking Yes) — Binance historical availability remains partial; OKX only has a conservative 2026 bound, not historical publication-time authority.
- **G05 FAIL_UNKNOWN** (blocking Yes) — funding-specific replacement/correction history is not established.
- **G06 FAIL_PARTIAL** (blocking Yes) — Binance raw lineage passes its bounded samples; OKX full request identity fails.
- **G07 FAIL_UNKNOWN** (blocking Yes) — intended internal acquisition/retention licensing remains unestablished or ambiguous (Binance E07/E08; OKX E11/E12). Tickets/acceptances record final status but are not the primary legal-semantics evidence.
- **G08 FAIL_BLOCKED** (blocking Yes) — provider funding-rate events are not position-dependent realized cashflows (FUND-001 E03/E04/E05). Required notional/side/mark/index inputs are absent (provider rate-event evidence E07/E11), and accepted FX-003 evidence (E14/E15/E16) does not authorize USD conversion.

## Decision
`NO_POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY`.

## Preserved acceptances (exact)
- FUND-001 readiness/substrate remains accepted.
- Binance and OKX bounded observations remain valid evidence.
- FUND-002 and FUND-003 remain accepted with NO_IMPLEMENTATION_AUTHORITY.
- FX-003 remains NO_PRIMARY_SOURCE_AUTHORITY.
- Sprint-003 RD-02 was a feasibility statement/next action, not implementation authority.

## Evidence provenance
Sixteen repository-native accepted artifacts used (paths/hashes/sizes in
`EVIDENCE_REGISTER.csv`): sprint_002/06; sprint_003/08; FUND-001 ticket/report/REVIEW-0093;
FUND-002 ticket/report/matrix/REVIEW-0098; FUND-003 ticket/report/matrix/REVIEW-0110;
FX-003 ticket/REVIEW-0114/matrix. No original raw source bodies are claimed as repository-native
beyond these accepted records.

## No-authority scope
No funding-event normalizer, realized cashflow, CARRY factor, USD conversion, schema,
migration, or next ticket authorized.

## Validation
- Repo control: PASS; `git diff --check`: clean.
- Evidence register: 16 rows, hashes/sizes verified; 0 CR bytes.
- Decision matrix: 8 gates, all blocking, as specified.
- Allowed-file scope only; no gate results or historical Sprint evidence altered.
