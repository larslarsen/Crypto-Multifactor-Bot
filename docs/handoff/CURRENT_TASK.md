# CURRENT_TASK

Ticket: MOMTS-001
State: ACCEPTED
Next required actor: Sr Engineer (Weak Model) — record review and next-ticket selection
Next ticket authorized: NONE

**Reviewer Decision:**

MOMTS-001 reviewed and accepted. `TimeSeriesMomentumFactor` (tsmom_30_7 / tsmom_90_7) and confirmatory runner for EXP-2026-019 / EXP-2026-020 are implemented, all gates pass (15 tests). All implementation sequences #1–#26 plus MOM-TS-01 research execution path are complete.

## Governing documents

- tickets/MOMTS-001.md (ACCEPTED)
- research/sprint_004/factor_cards/MOM-TS-01_time_series_momentum.md
- research/sprint_004/05_EXPERIMENT_REGISTRATIONS.csv
- research/sprint_004/01_MOMENTUM_OPERATIONALIZATION.md
- docs/adr/0012-cmc-survivorship-backfill.md

## Acceptance (Jr)

1. pytest on factors + experiments paths
2. ruff + mypy on touched packages
3. python3 scripts/check_repo_control.py
4. Formula + missing-history + dual-fingerprint tests
