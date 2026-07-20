# REF-001 — Change Report: Sr integrity-fix drop (in-tree)

**Ticket:** REF-001
**Source of change:** in-tree Sr Dev drop via Grok Build (agentic local edit), described in
`docs/reviews/REF-001_SR_INTEGRITY_FIXES.md`. Not a zip merge.
**Migration:** none (`sql/migrations/0006_reference_master.sql` unchanged).
**Integrated at:** see `git log` for the integration commit; gates below run against it.

## What changed

- `src/cryptofactors/reference/models.py`: added `ResolutionOutcome.REJECTED` and
  `ResolutionOutcome.DEFERRED` (typed decided-case surfaces from `resolve_alias`).
- `src/cryptofactors/reference/store.py` (+~460 lines):
  - `resolve_alias` honors persisted manual decisions for the
    `(alias_text_norm, venue_id, decision_time, knowledge_time)` key; RESOLVED returns
    the validated target + lineage, REJECTED/DEFERRED return typed outcomes and never
    requeue; only undecided (missing or QUEUED) cases enter the queue path.
  - `resolve_ambiguity_case(RESOLVED)` only accepts a target in the stored candidate set
    that still exists and (for instruments) is venue-compatible; checks run inside the
    atomic write unit.
  - `supersede_alias` requires contiguous knowledge time
    (`replacement.known_from == close_known_at`); replacement fields get full validation.
  - `supersede_instrument_version` — atomic knowledge-time close of the prior open version,
    insert of the replacement with lineage, overlap check after close; historical as-of
    answers preserved.
  - Global vs venue alias collision is same-scope only (both global or the same `venue_id`),
    independent of insertion order; cross-scope different targets are not silent collisions
    (they surface at resolve time).
  - Polymorphic existence / semantic checks that SQLite FKs cannot enforce run inside the
    same atomic write unit as the mutation.
- `docs/reviews/REF-001_SR_INTEGRITY_FIXES.md`: Sr-authored drop note (already in tree).
- `tests/reference/test_ref_store.py`: +8 focused regressions (I1–I6; I7 covered by I2/I4).
- `docs/reviews/REF-001_INTEGRATION.md`: evidence + drop-3 section appended.

## Jr integration notes

- The in-tree drop was complete; no missing helpers or strict-mypy fixes were required
  (unlike v2). No production-source edits by Jr beyond confirming the Sr code as-is.
- CURRENT_TASK.md was already updated by Sr to reflect the integrity-fix scope.

## Validation evidence

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/reference -q` | 19 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/reference tests/reference` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/reference tests/reference` | Success (5 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Status

Integrated and validated. REF-001 remains `IN_PROGRESS` (await reviewer acceptance verdict).
