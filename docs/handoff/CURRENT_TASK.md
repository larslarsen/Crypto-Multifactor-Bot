# CURRENT_TASK

Ticket: COMP-001
State: ACCEPTED
Next required actor: Reviewer
Next ticket authorized: NONE

COMP-001 (experiment #20, simple composites) accepted under REVIEW-0164.
Round 3 fix applied: tautological rank assertion corrected in integration test.

10 tests pass. ruff, mypy, governance all clean.

## Next in Sequence

ML-001 (experiment #21 — ML challengers) in READY. Ticket skeleton created.
Sr Dev (Grok) fills technical content, then stops for reviewer.

## Governing documents

- tickets/COMP-001.md (ACCEPTED)
- docs/reviews/REVIEW-0164_COMP-001_ACCEPTED.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr) — last pass

1. .venv/bin/python -m pytest tests/test_composite_factors.py -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/factors tests/test_composite_factors.py
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_composite_factors.py
4. python3 scripts/check_repo_control.py
