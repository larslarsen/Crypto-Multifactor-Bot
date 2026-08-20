# CEX-002 Grok Stable-Identity Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Base commit: `cb5b2d04a01140049fc4cdb220358194a2af3150`

## Decision

**ACCEPT THE TWO-PATH SOURCE DROP FOR INTEGRATION.**

Accepted identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `e2dd17fc71884bc83703f1609383e6b79eec60b54da30382f5a163b85f8bcd6a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5df4511baaf8b31938af1972430451f3012058fe2bc0da42b88a228c2fafc6f0` |

This is source acceptance, not Gate 1 data acceptance. The reviewer has not executed tests,
acceptance commands, or a real source run.

## Inspection

The production change makes the Gate 2 storage incident categorical and stable while
retaining exact local capacity and shortfall values in `storage.gate2_feasibility` and the
unchanged CLI output. It does not broadly remove incidents or storage state from semantic
identity.

`coinalyze_perp_symbol` now preserves an existing `_PERP` native suffix. It maps
`BTCUSDT` to `BTCUSDT_PERP.A` and `AAVEUSD_PERP` to `AAVEUSD_PERP.A`. The existing
full-market loop still validates every Binance perpetual native/provider pair, refuses
empty native identities, rejects mismatches, and rejects duplicate native identities.

The restored accumulated test source remains present at 3,786 lines and 139 unique test
functions. Four review-89 cases cover capacity churn with exact differing feasibility
values and equal semantic identities, both Coinalyze native forms, acceptance of a valid
already-suffixed row, and rejection of its mismatched provider label.

No membership classification, immutable-plan, ledger, checkpoint, source/coverage,
transfer, CLI, fixture, data, or report code was changed. The 63 unresolved candidates
and exact storage requirement remain visible blockers.

## Integration And Execution

At the owner's standing direction, the reviewer may integrate this small accepted
two-path drop together with this exact review publication. Jr Dev - Hermes then performs
only the command and preserved-store execution sequence below.

Hermes first verifies the two accepted hashes and `HEAD == origin/main`, then runs in
order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Any failure stops before a real source run. Do not substitute `-k`, edit source/test/data,
or clean, reset, restore, checkout, stash, delete, rename, replace, or relock the store.

If all five commands pass, load `.env` only into the environment and run the qualifier
twice against the same preserved `data/cex002_qualify` store and progress path. Write the
first report to `/tmp/cex002_gate1_stable_corrected_first.json` and the second to
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`. Capture and report the
actual process exit status for each invocation. Exit 1 stops immediately. Exit 2 is an
honest blocked matrix and permits the second run and comparison; it is not success.

After both exit-2 runs, compare `drop_identity_volatility` for the two reports and require
equality. Record the exact Coinalyze qualification/support result, membership classes,
product matrix, plan and ledger identities, listing/sample transfer counts, physical
storage values, and both raw exit statuses in
`research/sprint_004/91_CEX002_GATE1_CORRECTED_EXECUTION.md`.

Hermes may update only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/91_CEX002_GATE1_CORRECTED_EXECUTION.md`; and
- `tickets/CEX-002.md`.

Hermes commits and pushes only those four paths, establishes `HEAD == origin/main`, sets
the next actor to the reviewer, and stops. It performs no source/test edit, acquisition,
Gate 2, catalog mutation, Nautilus integration, other-ticket work, or Harmonic Trader
work.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. The corrected execution may still honestly
block on unresolved historical membership, liquidation coverage, cumulative legacy
budget, and physical storage. No reduced universe, omitted derivatives fields, or
price-only substitute is authorized. Next ticket remains `NONE`.
