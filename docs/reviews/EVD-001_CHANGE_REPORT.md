# EVD-001 — Change Report

**Ticket:** EVD-001 - Operational Evidence Registry
**Source approved:** REVIEW-0055 (SOURCE APPROVED / JR AUTHORIZED)
**Date:** 2026-07-20
**Actor:** Jr Dev - Hermes
**Integration commit:** (set on push)

## What was integrated

The Sr Dev production source drop for EVD-001 was already present in the working tree
(`src/cryptofactors/evidence/repository.py`, `models.py`, `__init__.py`, and the
`evidence` Typer sub-app in `src/cryptofactors/cli.py`). Jr integration added focused
regression tests and ran every acceptance command; two behavior-preserving strict-typing
fixes were made to satisfy the mypy gate.

## Tests added

`tests/evidence/test_evidence_registry.py` — 26 tests covering the REVIEW-0052/0053/0054
regression checklist from REVIEW-0055 §1:

1. Verified evidence hashes — caller-supplied mismatched hash rejected; verified hash accepted.
2. Immutable idempotence — identical content re-registration is a no-op; same ID with different
   content is rejected.
3. Point-in-time ordering — snapshot `as_of` cannot predate hypothesis creation; link cannot
   predate evidence/hypothesis registration; snapshot includes only links registered by `as_of`.
4. Snapshot + supersession ownership — idempotent snapshot identity; decision requires exact
   snapshot ownership; `CORRECT` requires `supersedes_decision_id` and occurs strictly after.
5. Promotion guards — `SUPPORTED`/`REPLICATED` rejected for literature/legacy-only snapshots and
   for `point_in_time`/`causal_split` integrity `FAIL`.
6. Deterministic exports — JSON byte-stable and complete (unlinked evidence, full version
   content, links, decisions, derived current state); Markdown deterministic.
7. Atomic / idempotent real-seed import — 12 hypotheses imported then 0 on re-import; bad entry
   is atomic (no partial landing).
8. Registry-version rejection — unsupported `registry_version` fails closed.
9. Seed snapshot validation — linked evidence present at seed clock fails closed.
10. Typed SQLite failures — uninitialized database raises `EvidenceRegistryError`; CLI exits
    nonzero with a stable message, no traceback.
11. Clean CLI failures — invalid model payload and missing file both exit nonzero, no traceback;
    end-to-end `seed` command idempotent via CLI.
12. Explicit experiment-link exclusion — repository exposes no `hypothesis_experiment_link`
    mutation path; contract deferred to the experiments layer.

## Behavior-preserving fixes (REVIEW-0055 §3)

- Removed an unused `# type: ignore[misc]` in `tests/evidence/test_models.py` so the mypy gate
  passes (strict-typing artifact; no runtime change).
- Removed an unused `DecisionAction` import from the new test file (ruff gate).
- No production source behavior was changed.

## Acceptance evidence (exact, fresh)

| Gate | Command | Result |
|---|---|---|
| 1 | `PYTHONPATH=src uv run pytest tests/evidence -q` | 27 passed (26 new + 1 pre-existing) |
| 2 | `ruff check src/cryptofactors/evidence src/cryptofactors/cli.py tests/evidence` | All checks passed |
| 3 | `mypy --no-incremental src/cryptofactors/evidence src/cryptofactors/cli.py tests/evidence` | Success: no issues found in 9 source files |
| 4 | `PYTHONPATH=src uv run pytest -q` | 423 passed, 1 pre-existing archive warning |
| 5 | `python3 scripts/check_layer_imports.py` | layer import check passed |
| 6 | `python3 scripts/check_repo_control.py` | Repo control check: PASS |

## Stop condition

Integrated, gated, reported, committed, and pushed. Ticket set to `AWAITING_REVIEW` with the
reviewer as next actor. Next ticket remains unauthorized. The experiment-link deliverable stays
deferred per the ticket scope; EVD-001 did not invent that contract.
