# REVIEW-0003 — GOV-001 governance artifacts and agent controls

**Review date:** 2026-07-18
**Decision:** awaiting_review (submitted by junior; owner acceptance pending) - RESOLVED (superseded by REVIEW-0004_GOV-001_FINAL.md; GOV-001 ACCEPTED)
**Architecture impact:** none
**ADR required:** ADR-0011

## Scope

Reviewed the GOV-001 deliverables and the repository-native control plane:

- `AGENTS.md`
- `tickets/GOV-001.md`
- `docs/adr/0011-repo-governance-and-agent-instructions.md`
- `scripts/check_repo_control.py`
- `tests/test_check_repo_control.py`
- `docs/handoff/CURRENT_TASK.md`
- `docs/handoff/HERMES_START_HERE.md`
- `docs/engineering/WORKFLOW.md`
- `docs/reviews/REVIEW-0002_CAT-001A_FINAL.md`
- `docs/reviews/GOV-001_CHANGE_REPORT.md`

## What this ticket establishes

GOV-001 introduces the minimal governance layer and the control-plane model defined in
ADR-0011:

- All work is ticket-driven; exactly one ticket is active at a time.
- Architecture/process decisions live in ADRs.
- Agents are instructed via `AGENTS.md`.
- `scripts/check_repo_control.py` validates the control plane (single active ticket,
  matching status/state, referenced governing documents, `NONE` next-ticket rule for
  blocked / awaiting-review work).
- The owner publishes commits; development agents commit locally and stop; only the
  owner or a designated reviewer accepts work or authorizes the next ticket.
- Chat instructions are not durable state until recorded in the repository.

## Key corrections applied in this ticket

1. **Validator realignment.** The validator now parses the fixed field format in
   `CURRENT_TASK.md` (`Ticket:`, `State:`, `Governing documents:`,
   `Next ticket authorized:`) instead of the earlier prose form. Valid states are
   `DRAFT`, `READY`, `IN_PROGRESS`, `BLOCKED`, `AWAITING_REVIEW`, `ACCEPTED`,
   `SUPERSEDED`. It requires exactly one `Ticket:` field, requires the referenced
   governing documents to exist, accepts `NONE` or a complete ticket ID for next, and
   requires `NONE` when blocked / awaiting-review. No dependencies were added and the
   design was not redesigned (routine integration per the task).
2. **Removed prohibited language.** `GOV-001.md` and `ADR-0011` no longer require public
   `origin/main` visibility, `git rev-parse origin`, or "self-driving" behavior. The
   owner publishes; the reviewer inspects the reviewed tree directly.
3. **Control-plane instructions.** `AGENTS.md` and `HERMES_START_HERE.md` now state that
   development agents commit locally and stop, and do not push or verify remotes.
4. **CAT-001A recorded accepted.** `tickets/CAT-001A.md` carries `**Status:** ACCEPTED`
   and `docs/reviews/REVIEW-0002_CAT-001A_FINAL.md` records the acceptance.

## Validator acceptance status

| Requirement | Status |
|---|---|
| exactly one `Ticket:` field | implemented |
| active ticket file exists | implemented |
| task state is valid | implemented |
| ticket status matches task state | implemented |
| referenced governing documents exist | implemented |
| `Next ticket authorized` is `NONE` or complete ID | implemented |
| blocked / awaiting-review requires `NONE` | implemented |
| no hard-coded ticket assignment in HERMES | implemented |
| no push/remote-verification requirement in gov docs | implemented |
| focused tests | implemented |

## Decision

Submitted for owner acceptance. GOV-001 is held at `AWAITING_REVIEW` with
`Next ticket authorized: NONE` pending the owner's decision. The junior did not mark
GOV-001 accepted and did not authorize the next ticket, consistent with the control
plane.
