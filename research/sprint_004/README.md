# Research Sprint 004 - Protocol Reconciliation

**Status:** Research-design update; no empirical results
**Created:** 2026-07-20
**Research cutoff:** 2026-07-18 (unchanged from Sprint 002)
**Ticket:** RES-001
**Depends on:** Accepted Sprints 001-003 and Evidence Registry v1

## Purpose

Sprint 004 converts a reviewer-triaged external scientific critique into precise,
non-redundant research rules. It adds no literature item, empirical result, supported factor,
or implementation authorization.

Sprint 001 remains frozen. Sprint 002 remains the governing literature refresh. Sprint 003
remains the governing source-feasibility audit. This sprint appends decisions rather than
rewriting those records.

## Decisions

- Keep MOM-01 as the existing cross-sectional 30-7/90-7 baseline.
- Register MOM-TS-01/H-012 as a separate, untested time-series hypothesis using matched
  lookbacks and realistic wealth-path accounting.
- Do not register a joint momentum/carry test until standalone momentum and carry pass their
  own data and evidence gates.
- Match inference to the estimand; do not require every estimator on every result.
- Define regimes from lagged information before evaluating outcomes; regime cells are
  reporting diagnostics, not model-selection permission.
- Keep the single sealed prospective holdout and once-per-version opening rule.
- Put performance/capacity diagnostics in experiment bundles, not the Evidence Registry.
- Measure DIL-01/NET-01 data readiness quantitatively, but freeze source-specific thresholds
  only after an audit and before factor outcomes are observed.

## Layout

```text
research/sprint_004/
├── README.md
├── 00_EXTERNAL_REVIEW_TRIAGE.md
├── 01_MOMENTUM_OPERATIONALIZATION.md
├── 02_VALIDATION_CAPACITY_AND_REGIMES.md
├── 03_DEFERRED_FACTOR_DATA_GATES.md
├── 04_RESEARCH_DECISIONS.csv
├── 05_EXPERIMENT_REGISTRATIONS.csv
└── factor_cards/
    └── MOM-TS-01_time_series_momentum.md
```

## Boundary

These records specify future research. They do not satisfy the data-foundation or research-
substrate gates in `docs/handoff/IMPLEMENTATION_SEQUENCE.md` and authorize no factor run.
