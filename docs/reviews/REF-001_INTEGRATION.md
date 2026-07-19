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

## Validation evidence (at integrated commit)

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/reference -q` | 11 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/reference tests/reference` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/reference tests/reference` | Success (5 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Open items / next steps

- REF-001 acceptance not yet recorded (await reviewer verdict).
- Deliverable synthetic tests for ticker reuse, redenomination, migration, delisting,
  and late metadata correction are partially covered; expand before acceptance if required.
