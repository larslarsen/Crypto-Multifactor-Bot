# AUD-005 - JR CONTROL PUBLICATION TASK

**Ticket:** `tickets/AUD-005.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - RECORDS AND PUBLICATION
**Next ticket:** `NONE`

## Assignment

Publish REVIEW-0066, its Sr source task, the corrected AUD-005 ticket, and matching handoff records.

## Required Repository State

- Make AUD-005 the sole active ticket with state `IN_PROGRESS`.
- Update README and implementation backlog to the corrected active scope.
- Keep `Next ticket authorized: NONE`.
- After publishing these records, set `Next required actor: Sr Dev - Sandbox` in the handoff.
- Run repository control, commit the control records, and push them.

## Ownership Sequence

Sr Dev - Sandbox supplies a local source drop after publication. Reviewer inspects it locally. Jr
Dev - Hermes later owns tests, research/evidence corrections, integration, records, and publication
after reviewer source approval.

## Completion Condition

The published repository contains REVIEW-0066 and the Sr task, with Sr Dev - Sandbox named as the
next required actor.
