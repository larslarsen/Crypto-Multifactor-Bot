# CURRENT_TASK

Ticket: PORT-002
State: ACCEPTED
Next required actor: Jr Dev (Weak Model) — closing records and git handoff
Next ticket authorized: NONE

**Reviewer Decision (Code Review):**

I have reviewed the `PORT-002` Perpetual Long/Short Portfolio Simulator implementation.
**Decision: ACCEPT**

The `LongShortRankAllocator` and `PerpetualSimulator` correctly introduce margin maintenance limits (liquidations) and funding cost integration. The update to `momts_runner.py` properly wires these up so that experiments `EXP-2026-019` and `EXP-2026-020` can be executed under realistic conditions. All acceptance criteria and gates pass.

We are now mechanically capable of fulfilling the registered requirements for the Time-Series Momentum experiments.

## Governing documents

- tickets/PORT-002.md (ACCEPTED)
- docs/reviews/REVIEW-0176_PORT-002_ACCEPTED.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. python3 scripts/check_repo_control.py
2. Commit and push the review records.
