# AUD-004 - JR REVIEW-0061 PUBLICATION TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Jr Dev - Hermes
**Status:** AUTHORIZED - RECORDS AND PUBLICATION
**Next ticket:** `NONE`

## Assignment

Integrate and publish:

- `docs/reviews/REVIEW-0061_AUD-004_RUNNER_SERIALIZATION_REQUIRED.md`
- `docs/reviews/AUD-004_SR_RUNNER_SOURCE_TASK.md`
- this publication task and matching ticket/handoff updates

## Required Repository State

- Keep AUD-004 as the sole active ticket with state `IN_PROGRESS`.
- Keep `Next ticket authorized: NONE`.
- After publishing these records, set `Next required actor: Sr Dev - Sandbox` in the handoff.
- Run repository control, commit the control records, and push them.

## Ownership Sequence

Sr Dev - Sandbox supplies a local runner-source drop after publication. Reviewer inspects it
locally. Jr Dev - Hermes later integrates and publishes only after reviewer source approval.

## Completion Condition

The published repository contains REVIEW-0061 and its Sr task, with Sr Dev - Sandbox named as the
next required actor.
