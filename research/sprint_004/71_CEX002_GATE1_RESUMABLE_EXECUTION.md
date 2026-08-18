# CEX-002 Gate 1 Resumable Execution Record

Date: 2026-08-18

Actor: Jr Dev — Hermes

## Outcome

**FOCUSED INTEGRATION SUITE FAILED — NO SOURCE COMMIT, NO NETWORK RUN, NO REAL GATE 1 RUN.**

Per review 70, a focused-command failure requires Hermes to record the exact failure in this
record, publish that evidence, and stop without a network run. The accepted three-path source
drop remains uncommitted and is not integrated. No real qualification was executed.

## Reviewed identities (verified before execution)

Committed control-plane base: `HEAD == origin/main == b2256500f39024c5390a7cf9fa09df75b6e4729c`.

| Path | Expected (review 70) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `9e75242b5ef9c67e5199dac24efe1385c43abdbdb8419cc913f9ec14c40b0aa2` | `9e75242b5ef9c67e5199dac24efe1385c43abdbdb8419cc913f9ec14c40b0aa2` |

All three observed hashes match review 70 exactly. The retained store was intact before
execution: `data/cex002_qualify` at approximately 691 MiB with `fapi_cache`, `list_cache`,
and `raw` present.

## Command sequence (review 70 order)

### 1. Focused CEX-002 suite — FAILED (exit 1)

Command:

```
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short
```

Result: 78 collected, 77 passed, 1 failed, exit 1.

Failed test:

```
tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_abort_after_completed_sample_resumes_missing_objects_only
```

Exact failure (line 1448):

```
tests/acquisition/test_binance_usdm_harmonic_qualification.py:1448: in test_abort_after_completed_sample_resumes_missing_objects_only
    assert vision_object_url(key) in fetched
E   AssertionError: assert 'https://data.binance.vision/data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-01.zip' in
    ['https://data.binance.vision/data/futures/um/monthly/trades/ETHUSDT/ETHUSDT-trades-2019-09.zip.CHECKSUM',
     'https://data.binance.vision/.../BTCUSDT/BTCUSDT-trades-2026-01.zip.CHECKSUM',
     'https://data.binance.vision/data/futures/um/monthly/trades/ETHUSDT/ETHUSDT-trades-2026-01.zip']
E    +  where 'https://data.binance.vision/data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-01.zip'
E       = vision_object_url('data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-01.zip')
```

Interpretation: this is the review-68/70-required injected abort-after-completed-sample test.
It aborts after two completed non-sidecar objects, then resumes on the same store and asserts
that the resumed run fetches only the remaining remote objects while reusing the two proven
objects, and that the resumed result is semantically identical to an uninterrupted run. On
resume, the implementation fetched only the checksum sidecar for the `BTCUSDT` monthly trades
archive and the two `ETHUSDT` objects, but did not fetch the missing `BTCUSDT-trades-2026-01.zip`
sample object that the test's `remaining` set requires. The assertion that every remaining
sample key was fetched therefore failed. This is a resume-plan completeness failure in the
accepted source, not an environment or network failure.

The test was re-run in isolation and deterministically failed identically.

### Commands 2–5 (NOT RUN)

Per review 70, the sequence stops at the first focused-command failure. The atomic-download
suite, Ruff, `check_repo_control.py`, and `git diff --check` were not executed. No source was
staged, committed, or pushed. No network qualification was performed.

## Integrity assertions

- No source/test path was modified, staged, committed, or pushed.
- `data/cex002_qualify` remained at approximately 691 MiB before and after the focused run;
  no object, checkpoint, or progress file was created, deleted, renamed, or mutated.
- No secret value appears in this record. The `.env` key was not loaded or printed.
- `git diff --check` was not run (command 5); the pre-failure staged path list was empty and
  the three reviewed paths were left untouched in the working tree.

## Consequence

The accepted review-70 source does not satisfy the required injected-interruption/resume
equivalence contract at the focused-suite gate. Jr integration, the source commit, and both
real Gate 1 runs remain unauthorized. The reviewer must disposition the resume-plan failure
before any further execution.