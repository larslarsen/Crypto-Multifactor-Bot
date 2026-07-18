# GOV-001 Change Report

**Date:** 2026-07-18
**Ticket:** GOV-001 — Establish repository governance artifacts and agent controls
**Author:** junior developer (Hermes)
**State:** AWAITING_REVIEW (owner acceptance pending)
**Based on:** ADR-0011, REVIEW-0002 (CAT-001A acceptance), `tickets/GOV-001.md`
**Senior commits included:** `e35d306` (semantic validator + focused tests)

## Objective

Complete the GOV-001 governance documentation, perform the routine validator
integration, validate, and stop for review. GOV-001 is held at `AWAITING_REVIEW` with
`Next ticket authorized: NONE`. The junior does not accept GOV-001 or authorize the next
ticket.

## Design choices

- **Control plane, not autonomous workflow.** No self-driving or autonomous ticket
  progression. Development agents commit locally and stop; the owner publishes and
  accepts. Chat instructions are not durable state until recorded in the repository.
- **Fixed field format in `CURRENT_TASK.md`.** The validator parses an explicit format
  rather than free prose, which makes the single-active-ticket invariant machine-checkable.
- **Validator realignment (routine, not a redesign).** `scripts/check_repo_control.py`
  was updated to parse the new `Ticket:` / `State:` / `Governing documents:` /
  `Next ticket authorized:` fields. No dependencies were added.
- **State set.** `DRAFT`, `READY`, `IN_PROGRESS`, `BLOCKED`, `AWAITING_REVIEW`,
  `ACCEPTED`, `SUPERSEDED`.
- **CAT-001A recorded accepted** so the catalog layer is formally closed before any
  downstream work is authorized.

## Files changed

- `scripts/check_repo_control.py` — realigned to the fixed field format; widened
  `VALID_STATES`; require exactly one `Ticket:`; require referenced governing documents
  to exist; `NONE`/ID next-ticket rule; blocked / awaiting-review requires `NONE`; reject
  hard-coded ticket assignments and push/remote-verification requirements in gov docs.
- `tests/test_check_repo_control.py` — rewritten for the new format; added coverage for
  valid case, missing ticket, invalid state, status mismatch, missing governing document,
  multiple `Ticket:` fields, unauthorized next when awaiting-review, explicit next ID when
  in-progress, all valid states, push/remote requirement, and hard-coded ticket in HERMES.
- `tickets/GOV-001.md` — acceptance wording corrected (owner publishes; no public-main
  requirement).
- `docs/adr/0011-repo-governance-and-agent-instructions.md` — rewritten to the control-
  plane model; removed "self-driving", public-`origin/main` visibility, and
  `rev-parse origin` requirements.
- `AGENTS.md` — agent behavior corrected: exactly one active ticket; commit locally and
  stop; no push/remote verification; chat instructions not durable until recorded.
- `docs/handoff/HERMES_START_HERE.md` — added a "Repository control plane" section.
- `docs/handoff/CURRENT_TASK.md` — written in the exact mandated field format
  (GOV-001 / AWAITING_REVIEW / Next NONE).
- `docs/engineering/WORKFLOW.md` — new operational workflow document (roles, field format,
  state values, validator rules, lifecycle, review/change-report conventions).
- `docs/reviews/REVIEW-0002_CAT-001A_FINAL.md` — new review recording CAT-001A acceptance.
- `docs/reviews/REVIEW-0003_GOV-001.md` — new review of GOV-001 (submitted, awaiting owner
  acceptance).
- `docs/reviews/GOV-001_CHANGE_REPORT.md` — this report.
- `tickets/CAT-001A.md` — added `**Status:** ACCEPTED`.

## Commands run and results

```bash
uv run pytest -q tests/test_check_repo_control.py
# 11 passed

uv run pytest -q tests/catalog
# 32 passed

uv run ruff check src tests
# All checks passed!

uv run mypy src
# Success: no issues found in 11 source files

python3 scripts/check_repo_control.py
# Repo control check: PASS
```

(Exact pass counts recorded by the actual run; see the validator/change-report execution
above. `tests/catalog` result reflects the pre-existing CAT-001A suite, unchanged by this
ticket.)

## Acceptance criteria demonstrated

- Exactly one active ticket (`Ticket: GOV-001`) parsed from `CURRENT_TASK.md`.
- `State: AWAITING_REVIEW` is valid and matches `tickets/GOV-001.md` status.
- Both governing documents listed exist.
- `Next ticket authorized: NONE` (required for `AWAITING_REVIEW`).
- No governance doc hard-codes a ticket assignment or requires push/remote verification.
- `scripts/check_repo_control.py` reports PASS on the repository.
- CAT-001A recorded `ACCEPTED`.

## Unresolved risks

- The validator checks structure and referenced paths, not the full prose correctness of
  every governance document. Reviewer inspection of `AGENTS.md` / `ADR-0011` prose is still
  required.
- No CI wiring was added in this ticket (not required by GOV-001); the owner may add it
  later via a ticket.

## Stop condition

Commit locally and stop for review. GOV-001 remains `AWAITING_REVIEW`; the next ticket is
not authorized. Progression is the owner's/reviewer's decision.
