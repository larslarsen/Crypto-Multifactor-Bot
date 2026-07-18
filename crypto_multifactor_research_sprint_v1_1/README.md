# Crypto Multifactor Research Program — Sprint 1

**Status:** Research foundation complete; empirical factor estimation not yet run  
**Research freeze:** 2026-07-17  
**Legacy repository reviewed:** https://github.com/larslarsen/Trading-Bot  
**Purpose:** Supply the research contracts that should precede architecture and implementation.

## What this package is

This is a clean-room research specification for a new cross-sectional cryptocurrency multifactor initiative. The legacy repository is treated as an evidence archive and a source of potentially reusable components—not as the architecture or research design to preserve.

The sprint produced:

- a research charter and falsifiable hypotheses;
- a documented audit of the legacy research;
- point-in-time data, universe, and validation contracts;
- canonical factor cards;
- a transaction-cost and portfolio-construction protocol;
- a matched replication protocol for the legacy volume-bar result;
- a literature synthesis and machine-readable ledger;
- preregistered experiments with no results filled in;
- a reuse register and an architecture handoff.

## Important limitation

The public repository excludes its raw CSV/Parquet data and many generated research outputs. Commit `fb737ae` now includes information-bar model artifacts, but the raw observations and complete prediction lineage needed to reproduce them remain unavailable. Therefore:

1. code, documentation, and the newly committed information-bar artifacts were inspected;
2. dataset counts and date spans reported by the repository are recorded as **author claims**;
3. no local raw-data checksum, schema, timestamp, or return replication was possible in this sprint;
4. no historical performance claim is accepted as validated by this package.

The next empirical step is a local data audit using `02_DATA_AUDIT_PLAN.md`. Architecture should begin only after the Tier-0 data acceptance gates pass.

## Binding decisions

1. The primary problem is cross-sectional asset ranking, not per-bar long/short/flat classification.
2. Daily/weekly research precedes five-minute research.
3. Missing data is never silently replaced with zero.
4. Universe membership is reconstructed point in time.
5. Accuracy and ROC-AUC are diagnostics, not promotion criteria.
6. Transaction costs, funding, and shortability enter before a factor is called viable.
7. Historical data through the research freeze is considered contaminated by prior experimentation.
8. A prospective holdout beginning after the freeze is required for a production-strength claim.
9. Machine learning must beat transparent equal-weight and regularized-linear composites net of costs.
10. The volume-bar result is a replication candidate, not an established edge.
11. Committed information-bar models remain quarantined from serving until causal representation and parity tests pass.

## Recommended reading order

1. `00_RESEARCH_CHARTER.md`
2. `01_LEGACY_REPOSITORY_AUDIT.md`
3. `11_LITERATURE_SYNTHESIS.md`
4. `03_POINT_IN_TIME_DATA_CONTRACT.md`
5. `04_UNIVERSE_SPECIFICATION.md`
6. `05_FACTOR_SPECIFICATIONS.md`
7. `06_VALIDATION_PROTOCOL.md`
8. `07_COST_AND_PORTFOLIO_PROTOCOL.md`
9. `10_EXPERIMENT_REGISTRY.csv`
10. `12_ARCHITECTURE_HANDOFF.md`
11. `15_POST_SPRINT_COMMIT_REVIEW.md`

## Evidence labels

- **VERIFIED_REPO:** directly observed in versioned public code or documentation.
- **CLAIMED_LOCAL:** stated by the repository, but the underlying local data/result was unavailable.
- **LITERATURE_PUBLISHED:** peer-reviewed published evidence.
- **LITERATURE_WORKING:** working-paper evidence; useful for hypotheses, not treated as settled.
- **DESIGN_DECISION:** preregistered choice for the new initiative.
- **UNRESOLVED:** must be answered by the local audit.

## Definition of “Sprint 1 complete”

Sprint 1 is complete when the research question, evidence boundary, factors, universe, validation, costs, and experiment registry are specified before new results are observed. This package meets that definition. It deliberately does **not** claim that any factor has passed.
