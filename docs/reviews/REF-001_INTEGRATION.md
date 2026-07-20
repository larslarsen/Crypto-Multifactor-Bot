# REF-001 — Implementation Handoff & Validation Evidence

**Ticket:** REF-001 (Point-in-time asset and instrument master)
**Status:** IN_PROGRESS (v1 + v2 Sr drops integrated; regression suite green)
**Source of truth:** `tickets/REF-001.md`, `docs/handoff/CURRENT_TASK.md`, AGENTS.md

## Drop 1 — `REF001_reference_master.zip` (schema + store)

- `src/cryptofactors/reference/` — `store.py`, `models.py`, `errors.py`, `__init__.py`.
  Bitemporal reference master: venues, assets, instruments, aliases, listings,
  migrations, manual-resolution queue. No automatic merge on symbol text.
- `sql/migrations/0006_reference_master.sql` — additive bitemporal schema
  (`ref_venue`, `ref_asset`, `ref_instrument`, `ref_instrument_version`, `ref_alias`,
  `ref_listing_event`, `ref_migration_event`, `ref_ambiguity_case`). The migration
  runner auto-discovers and applies it (0001–0006 contiguous; no transaction controls).
- Jr integration fix: removed an unused `pathlib.Path` import (ruff F401). The
  AUD-001-class bugs (missing `@dataclass`, untyped returns) were absent — Sr Dev had
  corrected those from prior feedback.

## Drop 2 — `REF001_v2_corrections.zip` (defect corrections)

Identified defects corrected (each pinned by a focused regression in
`tests/reference/test_ref_store.py`):

| ID | Defect corrected | Regression |
|----|------------------|-----------|
| D1 | `dt_to_iso` non-sortable (dropped microseconds) | `test_dt_to_iso_is_fixed_width_lexicographically_sortable` |
| D2 | Writes not atomic (bare commit/rollback) | `upsert_venue`/`register_*`/`add_*` exercised under `_atomic` |
| D3 | Asset/instrument identity derivable from display/ticker text | `test_asset_id_for_rejects_empty_identity_key`, `test_instrument_registration_rejects_empty_salt`, `test_asset_id_for_is_stable_and_display_independent` |
| D4 | Instrument-version overlap check outside atomic unit | `test_instrument_version_overlap_rejected` |
| D5 | Alias collision check outside atomic unit | `test_alias_collision_with_different_target_rejected` |
| D6 | Listing venue not validated vs instrument venue | `test_listing_venue_must_match_instrument_venue` |
| D7 | Ambiguity queue not idempotent (duplicate QUEUED) | `test_queue_ambiguity_is_idempotent` |
| D8 | No typed manual resolution transition | `test_resolve_ambiguity_case_requires_existing_queued`, `test_resolve_ambiguity_case_rejects_invalid_status` |
| D9 | No knowledge-time correction path | `test_supersede_alias_closes_known_to_and_inserts_replacement` |

**Jr integration fixes applied to make drop 2 pass the repo strict gates**
(behavior-preserving; Sr-source omissions, not new behavior):
- Added missing `ReferenceStore._require_instrument_version(version_id, instrument_id)`
  (referenced by `add_instrument_version` supersedes-check but never defined in the drop).
- Added missing `ReferenceStore._row_to_ambiguity(row)` (referenced by `queue_ambiguity`
  / `resolve_ambiguity_case` but never defined in the drop); mirrors `_row_to_alias`,
  reads `ref_ambiguity_case` columns including `resolution_target_kind/id` and note.
- Removed an unused `pathlib.Path` import introduced in the v2 `store.py`.

## Drop 3 — in-tree Sr integrity-fix (`REF-001_SR_INTEGRITY_FIXES.md`)

Sr Dev applied this drop directly in-tree (Grok Build agentic on local code), not as a
zip. No migration change (`0006` unchanged). Jr integration = regressions + validation
+ evidence; no production-source edits were needed (the drop was complete and clean).

Integrity fixes (each pinned by a focused regression `tests/reference/test_ref_store.py`):

| ID | Fix | Regression |
|----|-----|-----------|
| I1 | `resolve_alias` honors persisted manual decisions (RESOLVED/REJECTED/DEFERRED) and never requeues | `test_I1_resolve_alias_honors_resolved_decision_and_does_not_requeue`, `test_I1_resolved_rejected_and_deferred_are_typed_and_never_requeue` |
| I2 | `resolve_ambiguity_case(RESOLVED)` gates target to stored candidate set + existence + venue compatibility, all inside the atomic unit | `test_I2_resolve_ambiguity_case_rejects_target_not_in_candidates`, `test_I2_resolve_ambiguity_case_rejects_venue_incompatible_instrument` |
| I3 | `supersede_alias` requires contiguous knowledge time (`replacement.known_from == close_known_at`) | `test_I3_supersede_alias_requires_contiguous_knowledge_time` |
| I4 | `supersede_instrument_version` closes prior + inserts replacement; historical as-of preserved | `test_I4_supersede_instrument_version_preserves_historical_as_of` |
| I5 | Global vs venue alias collision is same-scope only, insertion-order independent | `test_I5_global_venue_alias_collision_is_same_scope_and_order_independent` |
| I6 | Cross-scope different targets surface at resolve time (no silent merge) | `test_I6_cross_scope_different_targets_surface_at_resolve_time` |
| I7 | Polymorphic existence / semantic checks run inside the same atomic write unit | covered by I2 (candidate gate + venue compat) and I4 (lineage check in-unit) |

`ResolutionOutcome.REJECTED` / `DEFERRED` added to `models.py`.

## Drop 4 — REF-001 deliverable scenario regressions (Jr Dev — Hermes)

No production-source or migration change. Added focused synthetic regressions under
`tests/reference/` covering the remaining ticket deliverables:

| ID | Scenario | Regression |
|----|----------|-----------|
| S1 | Ticker reuse: same symbol maps to different instruments across nonoverlapping half-open valid windows; historical as-of resolve returns the correct instrument | `test_S1_ticker_reuse_resolves_correct_instrument_per_valid_window` |
| S2 | Redenomination: typed asset→asset `REDENOMINATION` event preserves endpoints, positive ratio, valid/known time, evidence (plus zero-denominator / partial-ratio rejection) | `test_S2_redenomination_event_preserves_endpoints_ratio_time_evidence`, `test_S2_redenomination_rejects_zero_denominator_and_partial_ratio` |
| S3 | Migration: typed contract-migration event preserves distinct source/dest identities + lineage | `test_S3_contract_migration_preserves_distinct_source_dest_and_lineage` |
| S4 | Delisting: LIST/DELIST lifecycle events retain venue, economic (valid) time, known time, and historical identity | `test_S4_delisting_lifecycle_events_retain_venue_time_and_identity` |
| S5 | Late-metadata correction: documented as covered by D9 (`test_supersede_alias_...`) and I4 (`test_I4_supersede_instrument_version_...`); pinned by a quick alias-correction test | `test_S5_late_metadata_correction_covered_by_D9_I4` |

## Validation evidence (at integrated commit)

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/reference -q` | 25 passed (11 v2 D-series + 8 integrity I-series + 6 deliverable S-series) |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/reference tests/reference` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/reference tests/reference` | Success (5 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Open items / next steps

- REF-001 acceptance not yet recorded (await reviewer verdict).
- All five ticket deliverable scenarios (ticker reuse, redenomination, migration,
  delisting, late metadata correction) are now covered by focused regressions
  (S1–S5); no partial-coverage gap remains.
