# REVIEW-0017 — REF-001 FINAL REVIEW: ACCEPTED

**Ticket:** REF-001 — Point-in-time asset and instrument master
**Accepted commit:** `b742e8d2a3cf5239b93a9541aa0013589297cad2`
**Verdict:** `ACCEPTED`
**Reviewer of record:** Senior Quantitative Finance Researcher/Engineer (exclusive
  acceptance authority). Recorded by Hermes (Jr Dev) per control-plane governance.
**Accepted:** 2026-07-19

## Scope accepted

Full REF-001 implementation lineage, integrated and validated by Hermes:

- v1 Sr drop `REF001_reference_master.zip` (store + bitemporal migration `0006`),
  integrated at `8066b4e…`.
- v2 Sr corrections drop `REF001_v2_corrections.zip` (9 defects D1–D9), integrated with
  Jr fixes for two Sr-omitted helpers; committed at `fb86681…`.
- In-tree Sr integrity-fix drop (`REF-001_SR_INTEGRITY_FIXES.md`, Grok Build agentic),
  integrated with 8 regressions (I1–I6; I7 covered); committed at `cee5cc0…`.
- Jr deliverable-scenario regressions (S1–S5: ticker reuse, redenomination, migration,
  delisting, late-metadata correction); committed at `b742e8d…` (the accepted commit).

The accepted commit `b742e8d…` carries the complete REF-001 reference master plus all
focused regressions (25 reference tests) and the governance/role-map records. No
production-source change was required for acceptance beyond confirming the integrated
Sr code as-is.

## Validation evidence (acceptance commands, run at `b742e8d…`)

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/reference -q --tb=short` | 25 passed (11 v2 D-series + 8 integrity I-series + 6 deliverable S-series) |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/reference tests/reference` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/reference tests/reference` | Success: no issues found in 5 source files |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed (1 pre-existing harmless `Duplicate name: 'a.csv'` zip warning in an unrelated test; not an REF-001 failure) |
| `python3 scripts/check_repo_control.py` | PASS |

## Accepted invariants

- **Stable identity:** asset / instrument / venue IDs are derived from opaque keys
  (`identity_key`, `salt`), never from display name or ticker text alone; no automatic
  merge on symbol text.
- **Bitemporal records:** venues, assets, instruments, instrument versions, aliases,
  listings, and migrations carry valid-time × system-known-time windows; half-open
  `[from, to)` semantics are enforced; `dt_to_iso` is fixed-width and lex-sortable.
- **Alias resolution requires decision + knowledge time:** `resolve_alias` keys on
  `(norm, venue, decision_time, knowledge_time)`; persisted manual decisions
  (RESOLVED / REJECTED / DEFERRED) are honored and never requeued.
- **Manual resolution queue:** ambiguity cases are idempotent, queue once, and gate the
  resolution target to the stored candidate set with venue compatibility, all inside the
  atomic write unit.
- **Knowledge-time correction:** `supersede_alias` / `supersede_instrument_version` close
  the prior known window and insert a contiguous replacement; historical as-of answers
  are preserved.
- **Same-scope collision only:** global vs venue alias collisions are same-scope and
  insertion-order independent; cross-scope different targets surface at resolve time for
  manual triage, never silently merged.

## Required synthetic scenarios (all covered)

| Scenario | Regression |
|----------|-----------|
| Ticker reuse (same symbol → different instruments across nonoverlapping valid windows; historical as-of resolves correctly) | `test_S1_ticker_reuse_resolves_correct_instrument_per_valid_window` |
| Redenomination (typed asset→asset `REDENOMINATION` preserves endpoints, positive ratio, time, evidence) | `test_S2_redenomination_event_preserves_endpoints_ratio_time_evidence` (+ rejection tests) |
| Migration (typed contract-migration preserves distinct source/dest identities + lineage) | `test_S3_contract_migration_preserves_distinct_source_dest_and_lineage` |
| Delisting (LIST/DELIST retain venue, economic time, known time, identity) | `test_S4_delisting_lifecycle_events_retain_venue_time_and_identity` |
| Late-metadata correction (knowledge-time correction) | covered by D9 (`test_supersede_alias_…`) + I4 (`test_I4_supersede_instrument_version_…`); pinned by `test_S5_late_metadata_correction_covered_by_D9_I4` |

## Blocking findings

None. All five required synthetic scenarios are covered by focused regressions; the prior
"partial coverage" open item is retired in `REF-001_INTEGRATION.md`.

## Disposition

REF-001 → `ACCEPTED` at `b742e8d…`. `tickets/REF-001.md` and `docs/handoff/CURRENT_TASK.md`
set to `ACCEPTED`. Next ticket authorized: `NONE`.
