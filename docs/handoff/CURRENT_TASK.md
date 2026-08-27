# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Grok Build - review-325 retained-authority residual correction
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: the first acquisition wrote no network or raw fact. The rejected old plan and
its unfinished zero-fact run remain untouched. Grok's first ADR-0030 source/test drop fixes the
central 90-intersection/73-credit behavior, but review 325 rejects integration because receipt
258's retained block is only partially authenticated, an incompatible exact plan-receipt shape
reuses schema/policy v1, compact receipt replay validates only field names, and residual
authority tests are incomplete.

Grok Build XHigh must perform review 325's one consolidated correction in exactly the same
acquisition source and test source. Preserve the accepted exact-set threading and production
90/73 regression. Complete receipt-258 field/report-summary/lineage authentication, exact
progress byte typing, explicit plan-receipt/policy v2, compact v2 replay validation, and all
listed residual tests. Do not run commands/tests, use Git, edit governance/CLI, or touch data.

Hermes integration/testing, old-store retirement, corrected real planning, acquisition,
replay, `verify`, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiments,
PAPER/LIVE, and next-ticket work remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `docs/adr/0029-content-addressed-gate2-acquisition-and-resume.md`
- `docs/adr/0030-exact-retained-credit-and-pre-network-plan-retirement.md`
- `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`
- `research/sprint_004/324_CEX002_RETAINED_AUTHORITY_FAILURE_AND_PLAN_RETIREMENT_ARCHITECTURE.md`
- `research/sprint_004/325_CEX002_GROK_RETAINED_AUTHORITY_COMPLETE_STATIC_REJECTION.md`
