# CURRENT_TASK

Ticket: EXP-001
State: IN_PROGRESS
Next required actor: Sr Dev — Grok Build (source)
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
- docs/reviews/REVIEW-0145_LABEL-001_ACCEPTED.md
- all accepted foundation tickets (ASOF-001, SPLIT-001, LABEL-001)

## Authorized work

1. Sr Dev — Grok Build produces `src/cryptofactors/validation/experiment.py` per EXP-001 contract.
   Stop for Reviewer after source only. No tests, no commits, no pushes.
   **Flag:** Sr source drop requires verification by DeepSeek V4 Pro (or equivalent strong
   engineering model) before Reviewer acceptance.
2. Jr Dev — Hermes integrates after Reviewer approves source: tests + gates + change report +
   governance updates; all states AWAITING_REVIEW.

## Stop condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE. Stop after push.

## Reminder (next week)

Re-verify Sr source drops with a strong engineering model (DeepSeek V4 Pro or equivalent).
Starting with LABEL-001 (labels.py, integrated at 2786537)
Then EXP-001 (experiment.py, pending Sr drop)
And all future drops. Big Pickle's reviews are governance-only — code quality needs a
stronger model check when budget allows.
