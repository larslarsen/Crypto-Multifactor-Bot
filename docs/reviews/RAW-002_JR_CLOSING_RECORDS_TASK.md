# RAW-002 - JR CLOSING RECORDS TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Close RAW-002 consistently under REVIEW-0078.

## Exact Required Changes

- Set ticket and handoff state to `ACCEPTED`, name Reviewer as next actor, and state that no Jr work
  remains.
- Remove stale ticket/handoff assignment to the completed acceptance-publication task.
- Set REVIEW-0072 status to resolved by the later source reviews.
- Set REVIEW-0074 status to integrated and accepted by REVIEW-0077.
- Set REVIEW-0077 status to `PUBLICATION COMPLETED - RAW-002 CLOSED` and name Reviewer as next actor.
- Before publication, set REVIEW-0078 status to `RESOLVED - RAW-002 CLOSED` and name Reviewer as
  next actor.
- Before publication, set this task's own status to `COMPLETED`.
- Keep the acceptance-publication task completed and the change report's exact mypy evidence
  unchanged.
- Verify README and backlog show `ACCEPTED`, retain `Next ticket authorized: NONE`, add REVIEW-0078
  and this task to the governing chain, run repository control, commit, and push.

## Completion Condition

The published repository shows RAW-002 accepted and closed, no RAW-002 authorization remains
active, no Jr work remains, and no next ticket is authorized.
