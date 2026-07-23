# CURRENT_TASK

Ticket: EXP-001
State: AWAITING_REVIEW
Next required actor: Jr Dev — Hermes (integration)
Next ticket authorized: NONE

Accepted foundation context: ASOF-001 + SPLIT-001 + LABEL-001 all ACCEPTED.
LABEL-001 accepted under REVIEW-0145 (integrated at 2786537). Implementation Sequence #14 + #13
done; #15 (costed portfolio simulation) deferred until DF-08 universe snapshots unblocked.

EXP-001 authorized under REVIEW-0146 as Implementation Sequence #16: experiment bundles & fingerprints.
Unblocked — does not require survivorship-free universe. Provides reproducibility scaffold:
immutable ExperimentBundle with deterministic SHA-256 fingerprint, validated by a registry.

Governing documents:
- tickets/EXP-001.md (authorized)
- docs/reviews/REVIEW-0146_EXP-001_AUTHORIZED.md
- docs/reviews/REVIEW-0147_EXP-001_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/REVIEW-0145_LABEL-001_ACCEPTED.md
- src/cryptofactors/validation/experiment.py (approved drop, unchanged)

## Authorized work

EXP-001 Jr integration after REVIEW-0147: tests + gates + change report + governance updates.
No further work authorized.

## Stop condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE. Stop after push.

## Reminder (next week)

Re-verify Sr source drops with a strong engineering model (DeepSeek V4 Pro or equivalent).
Starting with LABEL-001 (labels.py, integrated at 2786537)
Then EXP-001 (experiment.py, pending Sr drop)
And all future drops. Big Pickle's reviews are governance-only — code quality needs a
stronger model check when budget allows.

### LABEL-001 retrospective P1 findings (2026-07-22)

- P1: With min_gap > 0, entry price is taken at decision_time but label interval starts at
  event_start. The return and purge interval disagree.
- P1: Incompatible with canonical BAR-001 timing. Bars become available at period_end, but
  AsOf eligibility requires decision_time < period_end. Boundary lookups can return empty.
