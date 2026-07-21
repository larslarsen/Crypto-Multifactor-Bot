# AUD-004 - JR CONTROL RECORD PUBLICATION TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - CONTROL RECORDS PUBLISHED
**Next ticket:** `NONE`

## Assignment

Integrate and publish the reviewer-authored AUD-004 correction authorization:

- `docs/reviews/REVIEW-0058_AUD-004_SOURCE_CORRECTION_REQUIRED.md`
- `docs/reviews/AUD-004_SR_SOURCE_CORRECTION_TASK.md`
- the matching `tickets/AUD-004.md` and `docs/handoff/CURRENT_TASK.md` updates

## Required Repository State

- Keep AUD-004 as the sole active ticket with state `IN_PROGRESS`.
- Keep `Next ticket authorized: NONE`.
- After publishing these control records, set `Next required actor: Sr Dev - Sandbox` in
  `docs/handoff/CURRENT_TASK.md`.
- Preserve the exact source correction authorized by REVIEW-0058; do not broaden ticket scope.
- Run repository control, commit the control records, and push them.

## Ownership Sequence

Sr Dev - Sandbox edits production source locally after this authorization is published. Sr does
not publish repository state. The reviewer inspects that local source drop, and Jr Dev - Hermes
later owns approved-source integration, tests, evidence, records, commit, and push.

## Completion Condition

The published repository contains the reviewer decision and Sr source task, and the handoff names
Sr Dev - Sandbox as the next required actor.
