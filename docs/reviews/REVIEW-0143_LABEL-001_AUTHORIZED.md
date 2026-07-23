# REVIEW-0143 — LABEL-001 AUTHORIZED (Label / Event Interval Separation)

**Authorized ticket:** LABEL-001
**Priority:** P0 (research substrate)
**Gate role:** BLOCKING_FOR_RESEARCH_SUBSTRATE
**Date:** 2026-07-22
**Next required actor:** Sr Dev (source) then Jr Dev (integration)

## Authorization

After ASOF-001 + SPLIT-001 acceptance, authorize the label/event-interval-separation engine.

This is the next substrate item (Implementation Sequence #13) and is unblocked: as-of access and purged splits are accepted; universe snapshots (blocked by DF-08) are not required for event-interval separation.

Objective: Define a reviewed implementation that produces labeled decision events with explicit event-start/event-end intervals, separated from feature/observation windows, so labels are never derived from data the strategy could not have observed at decision time. Outputs directly feed SPLIT-001 and portfolio simulation.

## Required contract
- Input: instruments, decision cadence, label horizon.
- Output: ordered list of labeled DecisionEvents with instrument_id, decision_time, event_start, event_end, label_direction, label_value.
- Separation: label window (event_start → event_end) must be strictly after feature/observation window.
- Feature data may only use observations with availability_time <= decision_time (via AsOfStore).
- Common label types: forward return, sign, binary up/down.
- Deterministic and reproducible.

## Scope
- New module under src/cryptofactors/ (e.g. labels/ or validation/labels.py).
- Protocol + concrete implementation.
- Uses reviewed AsOfStore for temporal eligibility.
- Produces EventInterval-compatible outputs (consumable by SPLIT-001).

## Out of scope
- Factor materialization, portfolio simulation, experiment bundling.
- Universe construction (still blocked by DF-08).
- New data sources.

## Next
1. Jr creates ticket + governance.
2. Sr produces source drop. Stop for reviewer.
3. Jr integrates + tests + gates. AWAITING_REVIEW.
4. No next ticket authorized.