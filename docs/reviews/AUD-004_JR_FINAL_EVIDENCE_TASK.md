# AUD-004 - JR FINAL EVIDENCE TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Jr Dev - Hermes
**Status:** RESOLVED - superseded by REVIEW-0061
**Next ticket:** `NONE`

## Assignment

Resolve the two final integration-evidence findings in
`docs/reviews/REVIEW-0060_AUD-004_INTEGRATION_EVIDENCE_REQUIRED.md`.

## Required Work

- Strengthen `test_headerless_short_first_row_counts_malformed` to assert that the same sampled
  archives support the unit transition when their malformed rate is within the configured limit
  and reject it when a stricter limit is exceeded.
- Assert malformed counts and sampled-row counts for both archives.
- Provision the repository-supported Sprint-003 test environment and run the full suite without
  skipping, weakening, or deselecting tests.
- Correct the change report and handoff so gate claims exactly match observed results.

## Acceptance Gates

Run and record every command from `docs/reviews/AUD-004_JR_INTEGRATION_TASK.md`, including the
complete `PYTHONPATH=src uv run pytest -q --tb=short` gate.

## Records And Publication

If every gate passes, set the ticket and handoff to `AWAITING_REVIEW`, name Reviewer as next actor,
retain `Next ticket authorized: NONE`, commit the tests/evidence/records, and push. If a required
environment remains unavailable, record exact failure evidence, set the ticket and handoff to
`BLOCKED`, name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, and push.

## Completion Condition

The published records contain truthful, exact evidence for every required gate and return control
to the Reviewer.
