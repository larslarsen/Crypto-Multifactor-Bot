# CEX-002 Gate-2 Correction Source Acceptance

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: SOURCE AND TEST SOURCE ACCEPTED FOR HERMES INTEGRATION
Ticket state: IN_PROGRESS
Next required actor: Jr Dev - Hermes
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of the combined Grok review-305 and Spark
review-306 correction at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `9476ccff836542509efe7e5169f0cb9d10d40a831fde0153415a4a667ff97065`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)

The source and test files contain 10,522 and 4,897 lines. The test source has 177 test
functions. Grok and Spark supplied no command result. The reviewer ran no test or acceptance
command.

## Static acceptance

Accept the complete correction for integration. Review 305 and review 306 are satisfied:

- retained raw open failures remain fail-closed and now carry explicit retained-source context;
- predecessor start-snapshot failures explicitly identify watermark disagreement;
- each recoverable charge tail is owned by a legitimate unfinished run, while an orphan tail is
  directly refused;
- interrupted receipts prove the exact `(charge_hi, transition_hi)` values `(1, 1)`, `(1, 1)`,
  and `(1, 2)` before the new run reconciles or retries them;
- publication recovery uses the exact durable-intent fault prefixes instead of deleting
  authenticated history;
- the recovered receipt is proved as the resumed run head's exact predecessor, and the resumed
  receipt is proved as the final head; and
- the injected interruption wrapper iterates the response stream and therefore reaches the
  intended statusless transport-attempt path.

The accepted review-304 state machine remains unchanged. This is static source acceptance, not
Gate-2 acceptance and not authority for a real plan, network, data, or verification command.

## Hermes integration authorization

Hermes owns one bounded correction checkpoint and targeted test cycle.

Preproof must establish:

- `HEAD == origin/main` at the review-307 publication commit;
- the source and test file exactly match the hashes above;
- the CLI remains clean at its unchanged hash above; and
- only the exact two developer paths below are staged.

Hermes must stage, commit, and push exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Before committing, run `git diff --cached --check` and prove the cached path list contains only
those two paths. Use commit message `correct CEX-002 Gate-2 recovery regressions`. Do not stage or
alter any unrelated dirty path.

After the checkpoint push, run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

If it fails, stop immediately without source/test repair or rerun and return the exit code,
complete pytest summary, first distinct failure with original exception/cause, elapsed time,
checkpoint commit, final hashes, and clean status for the two integrated paths. If it passes,
stop and return the exact result, elapsed time, checkpoint commit, pushed remote, final hashes,
and clean status for the two integrated paths.

Ruff, the full suite, control, real plan/acquire/verify, network, data, evidence edits, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and next-ticket work remain
unauthorized until reviewer inspection of this targeted result.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, `docs/handoff/CURRENT_TASK.md`, and
`tickets/CEX-002.md`. Developer source/test paths, state/data/evidence, and unrelated dirty work
are excluded.
