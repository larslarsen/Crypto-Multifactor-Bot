# REF-001 — Sr integrity-fix drop

**Status:** Ready for Jr integration and test coverage  
**Production files (already in tree):**
- `src/cryptofactors/reference/models.py`
- `src/cryptofactors/reference/store.py`

**Migration:** none (schema remains `sql/migrations/0006_reference_master.sql`)

## Code changes (already in production files)

1. **`resolve_alias` honors persisted manual decisions** for the case key
   `(alias_text_norm, venue_id, decision_time, knowledge_time)`.
   - `RESOLVED` → validated target + decision lineage in `evidence`
   - `REJECTED` / `DEFERRED` → typed `ResolutionOutcome` values; never requeue
   - existing `QUEUED` → return that case; no second insert
2. **`resolve_ambiguity_case` (RESOLVED)** only accepts a target in the stored
   candidate set that still exists and (for instruments) is venue-compatible
   with the case; checks run inside the atomic write unit.
3. **`supersede_alias`** requires contiguous knowledge time
   (`replacement.known_from == close_known_at`); replacement fields get normal
   validation (text, confidence, target, same-scope collision).
4. **`supersede_instrument_version`** — atomic knowledge-time close of the prior
   open version, insert of the replacement with lineage, overlap check after
   close; historical as-of answers preserved.
5. **Global vs venue alias collision** is same-scope only (both global or the
   same `venue_id`), independent of insertion order. Cross-scope different
   targets are not silent collisions; they surface at resolve time for manual
   resolution.
6. **Polymorphic existence / semantic checks** that SQLite FKs cannot enforce
   run inside the same atomic write unit as the mutation.
7. **`ResolutionOutcome.REJECTED` / `DEFERRED`** added for typed decided-case
   surfaces from `resolve_alias`.

## Jr work (see `tickets/REF-001.md` and `docs/handoff/CURRENT_TASK.md`)

- Confirm the production files above are present (in-tree Sr drop; no zip merge
  required if already at HEAD working tree).
- Add focused regressions under `tests/reference/` covering the seven items
  above (decided-case honor + no requeue; candidate gate; contiguous supersession;
  instrument-version supersession as-of; global/venue insert-order symmetry).
- Run formatter/linter/type-checker and the reference + full test suites; run
  `python3 scripts/check_repo_control.py`.
- Record evidence in `docs/reviews/REF-001_INTEGRATION.md` and the ticket change
  report (`docs/reviews/REF-001_CHANGE_REPORT.md` when required).
- Commit and push per Hermes duties. Stop. Do not start the next ticket.
