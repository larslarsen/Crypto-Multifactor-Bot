# CURRENT_TASK

Ticket: MOMTS-001
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review MOM-TS-01 factor + confirmatory runner
Next ticket authorized: NONE

**Reviewer Decision (Architecture — Research Execution Path):**

Implementation sequence #1–#26 is complete. Registered confirmatory experiments
**EXP-2026-019** and **EXP-2026-020** (MOM-TS-01, 30-7 and 90-7 time-series momentum)
remain `BLOCKED_DATA` only as a registry stale state — not because the substrate is
missing.

**Survivorship (locked):** ADR-0012 / UNIVERSE-003 CMC proxy death dates are accepted
as sufficient for Aware-level research. Do **not** re-litigate DF-08 final price /
failure-cause residuals on this ticket.

**Authorized work:** **MOMTS-001** — implement MOM-TS-01 skip-window log signals
(`tsmom_30_7`, `tsmom_90_7`), confirmatory runners for EXP-2026-019/020, spot long/cash
+ raw exposure + PORT-001 costs, EXP-001 bundles with distinct fingerprints. Lift
registry status off `BLOCKED_DATA` when code lands.

**Explicitly deferred:** perpetual L/S, funding events, liquidations, vol-managed cells
(follow-on after FUND-* / richer execution realism).

## Governing documents

- tickets/MOMTS-001.md (AWAITING_REVIEW)
- research/sprint_004/factor_cards/MOM-TS-01_time_series_momentum.md
- research/sprint_004/05_EXPERIMENT_REGISTRATIONS.csv
- research/sprint_004/01_MOMENTUM_OPERATIONALIZATION.md
- docs/adr/0012-cmc-survivorship-backfill.md

## Acceptance (Jr)

1. pytest on factors + experiments paths
2. ruff + mypy on touched packages
3. python3 scripts/check_repo_control.py
4. Formula + missing-history + dual-fingerprint tests
