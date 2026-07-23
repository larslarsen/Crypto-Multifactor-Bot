# REVIEW-0151 — NULL-001 SOURCE REJECTED

**Ticket:** NULL-001 — Null Factor Test (Experiment #18)
**Status:** REJECTED
**Date:** 2026-07-22
**Reviewer:** DeepSeek V4 Pro
**Next required actor:** Sr Dev (corrections required)
**Next ticket authorized:** NONE

## Findings

### P1 — Test bypasses research substrate

`tests/test_null_factor.py:58-75` proves independent PRNG streams lack correlation, not that ASOF/LABEL/EXP or portfolio processing avoids false edge. The test uses synthetic independent Gaussian returns directly, bypassing all accepted substrate components (CatalogAsOfStore, AsOfLabelEngine, PurgedChronologicalSplitter, ExperimentBundle). To validate the substrate, the null test must exercise the actual data flow: factor → labels → split → simulation.

### P2 — Generic contracts live in concrete null module

`src/cryptofactors/factors/null.py:50-78` defines `FactorValue`, `FactorFrame`, and `Factor` protocol. These are repository-wide contracts that should reside in a neutral factor contract module (e.g. `src/cryptofactors/factors/contract.py`), not embedded in the concrete null implementation. Every future factor implementation would import from a null test module — incorrect layering.

### P2 — String universe treated as character sequence

`NullFactor.compute("btc", as_of)` at `null.py:108` iterates the string and treats it as instruments `"b"`, `"t"`, `"c"`. Should reject string/bytes universe inputs with a clear error message.

### P2 — Scores change when universe changes

`null.py:121-126` seeds PRNG with sorted unique universe. Adding/removing one instrument changes scores for all existing instruments. If stable point-in-time reproducibility per instrument is required, seed per instrument rather than per universe.

## Decision

REJECT source. P1 finding requires correction before this can validate experiment #18. P2 findings should be corrected in the same pass.

## Corrected source must

1. Move `FactorValue`, `FactorFrame`, `Factor` to a neutral contract module under `src/cryptofactors/factors/`.
2. Reject string/bytes universe inputs.
3. Rebuild the test to exercise the accepted research substrate (ASOF → labels → split → simulation) or explicitly document why the current synthetic approach is acceptable for this specific validation step.
4. Consider per-instrument seeding if universe-stable scores are required.

No next ticket authorized. Stop after push.
