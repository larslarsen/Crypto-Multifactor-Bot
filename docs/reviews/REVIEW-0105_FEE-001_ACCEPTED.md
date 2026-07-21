# REVIEW-0105 - FEE-001 ACCEPTED

**Ticket:** FEE-001 - Point-in-Time Fee Schedules and Conservative Assumptions
**Status:** ACCEPTED
**Accepted implementation commit:** `44af03a`
**Next required actor:** Reviewer
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FEE-001 is accepted. The reference store now supports exact instrument/tier fee schedules with
bitemporal valid/known windows, deterministic Decimal identity, atomic overlap rejection and
supersession, explicit evidence class, and no missing-data fallback.

This acceptance provides fee-schedule substrate only. It does not establish any provider rate,
historical fee authority, conservative numeric assumption, spread/impact model, route, costed label,
portfolio simulation, or closure of architecture risk D-06.

## Acceptance Evidence

- Migration `0007` passes on fresh and previously migrated databases.
- Canonically equal Decimal rates share stored text and deterministic IDs; non-Decimal, non-finite,
  negative, and `>= 1` inputs fail closed.
- Half-open valid/known boundaries, exact tier lookup, no fallback, overlap rejection, rollback,
  cross-tier independence, contiguous supersession, and historical as-of stability are covered by 23
  focused tests.
- `uv run ruff format --check src/cryptofactors/reference tests/reference`: passed.
- `uv run ruff check src/cryptofactors/reference tests/reference`: passed.
- `uv run mypy src/cryptofactors/reference`: passed with no issues in four files.
- `python3 scripts/check_layer_imports.py`: passed.
- `uv run pytest -q tests/reference/test_fee_schedule.py`: passed.
- `uv run pytest -q`: passed with one pre-existing duplicate-ZIP-member warning.
- `python3 scripts/check_repo_control.py`: `Repo control check: PASS`.
- Commit `44af03a` is published at `origin/main`; the reviewed worktree was clean.

## Model-Routing Record

Grok Build 4.5 authored the production design and source drop. GPT-5.4 mini accidentally applied the
three exact normalization corrections prescribed by REVIEW-0104 while performing Jr integration. The
Reviewer inspected those production lines directly and independently reproduced every acceptance gate.
This bounded, fully specified correction is accepted as an exception; it does not grant Jr models
general production-source authority. The existing `test_ref_store.py` change is formatter-only.
