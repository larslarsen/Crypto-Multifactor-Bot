# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-326 exact integration and focused validation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: the first acquisition wrote no network or raw fact. The rejected old plan and
its unfinished zero-fact run remain untouched. Review 326 accepts Grok's complete ADR-0030
source/test correction at exact hashes for Hermes integration. Corrected code must not open or
mutate the real old store; retirement and replanning remain unauthorized until integrated
validation is accepted.

Hermes must perform review 326's single exact round: preprove the two accepted dirty paths,
stage/commit/push only them, run focused Gate-2 Ruff once, then run the targeted acquisition
pytest once only if Ruff passes. Stop on the first failure without repair or rerun. On two
passes publish only evidence record 327 in a second commit/push, run final shared-tree
`git diff --check` once, and stop.

Full-suite pytest, repository-wide Ruff, control, old-store retirement, corrected real
planning, acquisition, replay, `verify`, Gate 3, normalization, catalog, NautilusTrader,
Harmonic Trader, experiments, PAPER/LIVE, and next-ticket work remain unauthorized. Next
ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `docs/adr/0030-exact-retained-credit-and-pre-network-plan-retirement.md`
- `research/sprint_004/324_CEX002_RETAINED_AUTHORITY_FAILURE_AND_PLAN_RETIREMENT_ARCHITECTURE.md`
- `research/sprint_004/325_CEX002_GROK_RETAINED_AUTHORITY_COMPLETE_STATIC_REJECTION.md`
- `research/sprint_004/326_CEX002_RETAINED_AUTHORITY_SOURCE_ACCEPTANCE_AND_INTEGRATION.md`
