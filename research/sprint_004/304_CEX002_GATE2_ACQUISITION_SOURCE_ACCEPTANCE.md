# CEX-002 Gate-2 Acquisition Source Acceptance

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: SOURCE AND TEST SOURCE ACCEPTED FOR HERMES INTEGRATION
Ticket state: IN_PROGRESS
Next required actor: Jr Dev - Hermes
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's review-303 return at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `308b818806be9be3393af19ecf306eb24f88a4884dcf470e664bf8cd2d6a19f2`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `e04c47f7485500f1a63d2c505cb5f71df5ff341f3447bb14d34bc4cb27f2c1a8`

The files contain 10,516, 151, and 4,786 lines. The test source has 176 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command.

## Static acceptance

Accept the complete Gate-2 acquisition source and test source for integration. Review 303's
remaining requirements are satisfied:

- worker-level error and capacity-block events are persisted through the coordinator-owned open
  run and used identically by graceful and interrupted finalization;
- transient retries do not become worker errors, exhausted requests retain one worker error,
  and a capacity event remains blocked after process-loss recovery;
- interrupted runs retain their original identity and exact predecessor-owned deltas before any
  new run starts;
- completed publication intents are authenticated through head and historical chain walking;
- receipt recovery remains constant-memory; and
- production and non-production stable-component mappings are compared exactly, including an
  offsetting production-component mutation regression.

This is static source acceptance, not Gate-2 acceptance. No real plan, network, or data command
is authorized.

## Hermes integration authorization

Hermes owns one bounded integration checkpoint and targeted test cycle.

Preproof must establish:

- `HEAD == origin/main` at the review-304 publication commit;
- the three developer files exactly match the hashes above; and
- only the exact developer paths below are staged.

Hermes must first stage, commit, and push exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Before committing, run `git diff --cached --check` and prove the cached path list contains only
those three paths. Use commit message `integrate CEX-002 Gate-2 acquisition engine`. Do not stage
or alter any unrelated dirty path.

After the checkpoint push, run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

If it fails, stop immediately without source/test repair or rerun and return the exit code,
complete pytest summary, first distinct failure with original exception/cause, elapsed time,
checkpoint commit, and final status. If it passes, stop and return the exact command/result,
elapsed time, checkpoint commit, pushed remote, final hashes, and clean status for the three
integrated paths. Ruff, the full suite, control, real plan/acquire/verify, network, data,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, evidence-record edits, and
next-ticket work remain unauthorized until reviewer inspection of this targeted result.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
