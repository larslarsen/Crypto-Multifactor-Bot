# CURRENT_TASK

Ticket: PAPER-004
State: ACCEPTED
Next required actor: Jr Dev (Weak Model) — closing records and git handoff
Next ticket authorized: NONE

**Reviewer Decision (Code Review):**

I have reviewed the `PAPER-004` MTM equity and broker resume fixes.
**Decision: ACCEPT**

`PaperOpsMonitor` now reports mark-to-market equity when prices are supplied. `PaperBroker.restore_from_store` enables session resume. Both REVIEW-0181 caveats closed.

Policy remains: no LIVE until paper trading is profitable on real data. Next phase is HARDEN (real as-of path / exchange stubs).

## Governing documents

- tickets/PAPER-004.md (ACCEPTED)
- docs/reviews/REVIEW-0182_PAPER-004_ACCEPTED.md

## Acceptance (Jr)

1. python3 scripts/check_repo_control.py
2. Commit and push the review records.
