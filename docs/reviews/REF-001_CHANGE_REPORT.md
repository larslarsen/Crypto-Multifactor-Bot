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

## Supplement — REF-001 deliverable scenario regressions (Jr Dev — Hermes)

Separate commit (no production-source / migration change). Added focused synthetic
regressions covering the remaining ticket deliverables under `tests/reference/`:

- **S1 ticker reuse:** same symbol → different instruments across nonoverlapping
  half-open valid windows; historical as-of resolve returns the correct instrument
  (`test_S1_ticker_reuse_resolves_correct_instrument_per_valid_window`).
- **S2 redenomination:** typed asset→asset `REDENOMINATION` event preserves endpoints,
  positive ratio, valid/known time, evidence; rejects zero denominator and partial ratio
  (`test_S2_redenomination_event_preserves_endpoints_ratio_time_evidence`,
  `test_S2_redenomination_rejects_zero_denominator_and_partial_ratio`).
- **S3 migration:** typed contract-migration event preserves distinct source/dest
  identities + lineage (`test_S3_contract_migration_preserves_distinct_source_dest_and_lineage`).
- **S4 delisting:** LIST/DELIST lifecycle events retain venue, economic (valid) time,
  known time, and historical identity (`test_S4_delisting_lifecycle_events_retain_venue_time_and_identity`).
- **S5 late-metadata correction:** documented as already covered by D9 and I4; pinned by
  a quick alias-correction test (`test_S5_late_metadata_correction_covered_by_D9_I4`).

All five deliverable scenarios are now covered; the prior "partial coverage" note is
retired. REF-001 remains `IN_PROGRESS`; `Next ticket authorized: NONE`.

## Validation evidence

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/reference -q` | 25 passed (11 v2 D-series + 8 integrity I-series + 6 deliverable S-series) |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/reference tests/reference` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/reference tests/reference` | Success (5 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Status

Integrated and validated. REF-001 remains `IN_PROGRESS` (await reviewer acceptance verdict).
