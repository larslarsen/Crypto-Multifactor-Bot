# REVIEW-0140 — SPLIT-001 AUTHORIZED (Purged Chronological Split Engine)

**Authorized ticket:** SPLIT-001
**Priority:** P0 (research substrate)
**Gate role:** BLOCKING_FOR_VALIDATION
**Date:** 2026-07-22
**Next required actor after ticket creation:** Sr Dev - Grok Build (source) then Jr Dev - Hermes

## Authorization

After ASOF-001 acceptance, authorize creation and implementation of the purged chronological split engine.

This is the next item in the research substrate gate (Implementation Sequence #14 after as-of access).

Objective: Provide a single reviewed implementation that generates deterministic, purged, chronological train/test splits with explicit event-time purging and embargo, so that no future information can leak into training or validation.

Required contract (from architecture):
- Given a decision time, a set of instruments, and a target horizon, produce ordered splits.
- Every split must respect event time: labels and features for a decision must only use data whose availability_time <= decision time.
- Purging: no overlap between training and test on event time for the same instrument.
- Embargo: optional embargo period after training end before test start.
- Deterministic and reproducible from the same inputs + seed.
- Output must be usable by portfolio simulation and experiment bundles.

## Scope for this ticket

- New module under src/cryptofactors (e.g. validation/split.py or similar).
- Protocol + concrete implementation.
- Support for walk-forward / rolling / purged K-fold style chronological splits.
- Integration with as-of access for point-in-time data retrieval during split construction.
- Clear failure modes for insufficient history or leakage risk.

## Out of scope (this ticket)

- Actual factor computation or label generation (that is later).
- Portfolio simulation.
- Experiment bundling (EVD integration later).
- Any data collection or new sources.

## Preserved boundaries

- Must use the reviewed AsOfStore for all temporal data access.
- Must not bypass bitemporal eligibility.
- Must not introduce new data authority claims.

## Next steps after authorization

1. Jr Dev creates the ticket file `tickets/SPLIT-001.md` with exact scope, contract, and acceptance commands.
2. Update backlog, CURRENT_TASK, README.
3. Sr Dev implements the production source only.
4. Jr then adds tests, runs gates, records, commits, pushes.
5. Return to AWAITING_REVIEW. No next ticket authorized.

## Stop condition for this authorization

Return control to Reviewer with `Next ticket authorized: NONE` after acceptance of SPLIT-001. No live work, no factors, no portfolio yet.