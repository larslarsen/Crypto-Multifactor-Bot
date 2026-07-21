# AUD-005 - JR INTEGRATION TASK

**Ticket:** `tickets/AUD-005.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - AWAITING_REVIEW PUBLISHED
**Next ticket:** `NONE`

## Assignment

Integrate the local source approved by
`docs/reviews/REVIEW-0068_AUD-005_SOURCE_APPROVED_JR_AUTHORIZED.md`.

## Required Tests

- Use an actual `set[str]` to select dimensions and assert canonical `compared_dimensions` and
  `not_comparable_dimensions` ordering.
- Verify mappings may omit unselected fields and fail when a selected field is absent.
- Verify omitted selection preserves all historical requirements and comparisons.
- Verify excluded provider trade-count differences never produce a trade-count mismatch.
- Reject empty, unknown, duplicate, scalar string/bytes, and non-string selections.
- Verify the Sprint-003 runner completes comparison with quote volume from kline column 7,
  recognizes column-8 provider trade count, and never equates it to aggTrades record count.

## Research And Evidence

Correct the factual contradiction in `research/sprint_003/12_AUDIT_EXECUTION.md` and
`research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md`: Binance kline trade count exists but is
semantically non-comparable to aggTrades-record count. Regenerate affected deterministic audit
outputs and execution-manifest hashes through the existing runner; do not hand-edit generated
results.

## Acceptance Gates

Run and record:

1. `PYTHONPATH=src uv run pytest tests/test_bars.py -q --tb=short`
2. `PYTHONPATH=src uv run pytest tests/test_audit_runner_sprint003.py -q --tb=short`
3. `PYTHONPATH=src uv run ruff check src/source_audit scripts/audit/run_sprint003_audit.py tests/test_bars.py tests/test_audit_runner_sprint003.py`
4. `PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_bars.py`
5. `PYTHONPATH=src uv run pytest -q --tb=short`
6. `python3 scripts/check_repo_control.py`

## Records And Publication

Create `docs/reviews/AUD-005_CHANGE_REPORT.md` with exact gate output and generated-evidence paths.
Set the ticket and handoff to `AWAITING_REVIEW`, name Reviewer as next actor, retain
`Next ticket authorized: NONE`, update README/backlog/task status, commit approved source, tests,
research evidence, and records, then push.

## Completion Condition

The published repository contains the approved source, complete regressions, corrected research
evidence, passing gates, and an `AWAITING_REVIEW` handoff.
