# CURRENT_TASK

Ticket: ARCH-002
State: AWAITING_REVIEW
Next required actor: reviewer — Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

## What landed

- `src/cryptofactors/universe/binding.py` — `UniverseBinding` protocol and
  `CMCSurvivorshipBinding` adapter backed by catalog-published CMC graveyard
  dataset. Fail-closed on missing/empty dataset.
- `src/cryptofactors/execution/paper_loop.py` — `FactorDrivenPaperLoop.run_loop`
  now requires a `UniverseBinding`; resolves membership per decision time and
  fingerprints `universe_dataset_id`, `survivorship_policy`, and
  `universe_code_version` in `PaperLoopResult`.
- `src/cryptofactors/universe/__init__.py` — exports the binding protocol,
  adapter, loaders, and `is_survivorship_invalid`.
- `scripts/run_paper_momts.py` + 10 `scripts/research/*.py` — migrated from
  static `PAPER_TO_INSTRUMENT_ID.keys()` membership to
  `load_paper_universe_binding(...)`.
- `tests/universe/test_binding.py` — 11 tests for contract, CMC birth/death
  proxy semantics, empty-universe fail-closed, fingerprinting, and old-list API
  rejection.
- `tests/execution/test_paper_loop.py` + `tests/execution/test_paper_ops.py` —
  updated to use `_StaticUniverseBinding` test stubs.
- Static venue maps (`PAPER_TO_INSTRUMENT_ID`, `PAPER_TO_BINANCE_MAP`) remain
  symbol translation only and are never used for membership.

## Governing documents

- tickets/ARCH-002.md (this ticket, AWAITING_REVIEW)
- research/sprint_004/41_DATA_ARCHITECTURE_GAP.md (survivorship-invalid artifact list)
- docs/reviews/REVIEW-0216_DATA-011_ACCEPTED.md (prior ticket DATA-011)
