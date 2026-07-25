# ARCH-002 — UniverseBinding Contract (Experiments & Paper Fail-Closed)

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** ADR-0014 (proposed), UNIVERSE-003 (ACCEPTED), UNIVERSE-006 (ACCEPTED), ASOF-001 (ACCEPTED)
**Layer:** architecture / execution / factors
**Architecture:** ADR-0014. **No LIVE. No new data vendors.**

## Objective

Make every experiment and paper session **fail closed** unless membership comes from a
catalog-published survivorship-aware `universe_at(decision_time)`. End the practice of
using `PAPER_TO_INSTRUMENT_ID.keys()` as the research universe.

## Current State

- CMC graveyard CSV exists (1,756 rows) and is now loaded through a catalog-published
  survivorship dataset.
- All TSMOM scripts now load a `UniverseBinding` instead of hardcoding static paper symbols.
- Prior EXP/PAPER results remain survivorship-invalid (see
  `research/sprint_004/41_DATA_ARCHITECTURE_GAP.md`).

## Scope

### In scope

1. **`UniverseBinding` protocol** in `src/cryptofactors/universe/binding.py`:
   - `universe_dataset_id: str`
   - `universe_at(decision_time: datetime) -> frozenset[str]`  # paper or instrument keys
   - `coverage_report(decision_time) -> dict` (eligible, with_bars, missing)
   - Construction requires a catalog-resolvable universe dataset; empty → error.

2. **Adapter** wrapping `CMCSurvivorshipProvider` (and a future composite CEX∩bars provider).

3. **Wire fail-closed** into shared paper-loop entry used by research scripts
   (factor loop / `FactorDrivenPaperLoop` path). Scripts must pass `UniverseBinding`;
   remove `universe = list(PAPER_TO_INSTRUMENT_ID.keys())` as membership source.

4. **Fingerprint** every run artifact with `universe_dataset_id`, binding code version,
   and `survivorship_policy: "cmc_aware_proxy_v1"`.

5. **Mark invalidation** constant or helper: prior sprint_004 EXP/PAPER ids listed in
   gap doc get `survivorship_invalid: true` when re-read (documentation + optional
   registry flag — no silent reuse).

6. **Tests:** empty universe fails; static-map-only construction forbidden; binding
   respects birth/death proxy as-of semantics.

### Out of scope

- Rebuilding bars (DATA-011)
- New factor research (EXP-009)
- DEX survivorship (DEX-003)
- Expanding to MEXC/Kraken/Blofin (UNIVERSE-005)

## Deliverables

1. `src/cryptofactors/universe/binding.py` (+ exports)
2. `src/cryptofactors/execution/paper_loop.py` — requires `UniverseBinding`, fingerprints
   artifacts.
3. Paper/experiment entrypoints updated to require binding (11 scripts under `scripts/`).
4. Unit tests under `tests/universe/test_binding.py` and `tests/execution/` stubs updated.
5. Short note in gap doc that ARCH-002 code landed.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/universe/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/universe src/cryptofactors/execution`
3. A dry-run paper script with no universe dataset **exits non-zero**
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW. Next ticket authorized: NONE (reviewer unlocks next spine
or promotion ticket).
