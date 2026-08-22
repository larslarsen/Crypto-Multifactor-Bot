# CEX-002 Authority Source Integration

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/167_CEX002_AUTHORITY_SOURCE_ACCEPTANCE.md`

## 1. Preproof

Hermes established:

`HEAD == origin/main == 451de42b6f9479add1b444ada5e75e9778ae9239`

before staging.

Accepted source hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` |

The accepted CEX test path contained 305 unique `test_` function definitions. No `python3`
qualification process was running.

## 2. Integration

Hermes staged exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`

and committed:

`1e62cd854176177d25ddc9f5043c15f827aa5b86`

Commit message:

`CEX-002: integrate authority source`

After push:

`HEAD == origin/main == 1e62cd854176177d25ddc9f5043c15f827aa5b86`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
Hermes made no source or test edit after integration.

## 3. Focused command sequence

Review 167 required a stop-on-first-failure command sequence. Command 1 exited nonzero, so
commands 2-5 were not authorized and were not run.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 2

Elapsed seconds: 1

Material output:

```text
==================================== ERRORS ====================================
_ ERROR collecting tests/acquisition/test_binance_usdm_harmonic_qualification.py _
tests/acquisition/test_binance_usdm_harmonic_qualification.py:26: in <module>
    from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py:1842: in <module>
    class CostSampleValidation:
src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py:1859: in CostSampleValidation
    observation: str = COST_OBSERVATION_PRICEABLE
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   NameError: name 'COST_OBSERVATION_PRICEABLE' is not defined
=========================== short test summary info ============================
ERROR tests/acquisition/test_binance_usdm_harmonic_qualification.py - NameErr...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
elapsed_seconds=1
exit_status=2
```

### C2-C5

Not run because C1 exited nonzero.

## 4. Final source state

Final source hashes still match review 167:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` |

The CEX test path still contains 305 unique `test_` function definitions.

## 5. Disposition

No live `--apply-reviewed-v4-source-correction-only` invocation, data mutation,
source-data network operation beyond authorized Git pushes, ordinary qualification,
reservation reconciliation, report write, Gate-1 acceptance, sizing, Gate 2, bulk
acquisition, normalization, catalog publication, Nautilus work, Harmonic Trader work,
payoff analysis, PAPER, LIVE, paid source, reduced scope, or next-ticket work occurred.

This publication records the exact integration and C1 collection failure only. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.
