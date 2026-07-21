# RAW-002 - JR INTEGRATION TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Integrate the local source approved by
`docs/reviews/REVIEW-0074_RAW-002_SOURCE_APPROVED_JR_AUTHORIZED.md`.

## Required Tests

- Final-path symlink substitution after a valid publication.
- Parent-component symlink substitution after a valid publication.
- Lexical `..` receipt-path rejection before normalization.
- Escaping object prefix/path, missing component, non-directory parent, and non-regular final
  component rejection.
- Existing canonical receipt, object-ID, URI, byte-size, digest, and writer/catalog behavior.
- Assert failures are `CatalogRegistrationError` and do not accept/hash a substituted symlink
  target.

## Acceptance Gates

Run and record:

1. `PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q --tb=short`
2. `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/raw tests/test_raw_object_writer.py`
3. `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest/raw tests/test_raw_object_writer.py`
4. `PYTHONPATH=src uv run pytest -q --tb=short`
5. `python3 scripts/check_layer_imports.py`
6. `python3 scripts/check_repo_control.py`

## Records And Publication

Create `docs/reviews/RAW-002_CHANGE_REPORT.md` with exact gate output. Set the ticket and handoff to
`AWAITING_REVIEW`, name Reviewer as next actor, retain `Next ticket authorized: NONE`, update
README/backlog/task status, commit approved source/tests/records, and push.

## Completion Condition

The published repository contains approved source, adversarial regressions, passing gates, truthful
records, and an `AWAITING_REVIEW` handoff.
