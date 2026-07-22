# REVIEW-0141 — SPLIT-001 SOURCE APPROVED / JR INTEGRATION AUTHORIZED

**Ticket:** SPLIT-001 — Purged Chronological Split Engine
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-22

## Decision

SPLIT-001 Sr production source drop is approved for integration.

- `src/cryptofactors/validation/split.py` (487 lines) implements `ChronologicalSplitter` protocol + `PurgedChronologicalSplitter`.
- Supports `WALK_FORWARD`, `EXPANDING`, `PURGED_KFOLD` modes.
- `split(events, config)` returns `list[OuterFold]` with train/test partitions, purge_gap, embargo.
- `purge_train_events` enforces no overlap on event intervals + embargo horizon.
- Injected `AsOfDataAccess` protocol (structural, no catalog import) used for instrument eligibility via `as_of`.
- `EventInterval`, `SplitConfig`, `OuterFold` etc. match ticket contract.
- Event-time rule, purging, fail-closed on insufficient history, deterministic ordering.
- Ticket authorized under REVIEW-0140; source matches required contract exactly.

## Jr authorization

Jr Dev - Hermes owns:
1. Focused tests for eligibility, all three modes, purging/embargo, AsOf injection, error cases (insufficient data, missing instruments, bad config).
2. Run acceptance gates (pytest on validation, ruff, mypy, repo-control).
3. Record exact results in SPLIT-001 change report.
4. Update ticket/backlog/README/handoff/CURRENT_TASK to AWAITING_REVIEW.
5. Commit and push only intended changes; return hash + summary.

No reviewer acceptance claim. No next ticket. Stop after push.