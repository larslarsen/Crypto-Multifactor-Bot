# CEX-002 Migration Test Integration and Focused-Command Stop

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/154_CEX002_MIGRATION_TEST_SOURCE_ACCEPTANCE.md`

## 1. Test-correction integration

Hermes established:

`HEAD == origin/main == 009977ade864d820c33707717001f7848a31ef0f`

before staging.

Accepted path hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a753afc0290708c630198714d574f1ddb65fa43e97b516a100ba32f0a915fd1e` |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |

The corrected test path contained 285 unique `test_` function definitions. `git diff
--check` was clean for the accepted test path.

Hermes staged exactly:

`tests/acquisition/test_binance_usdm_harmonic_qualification.py`

and committed:

`31552933df41b4c8f769fb5b4237299d620a6380`

Commit message:

`CEX-002: integrate migration test correction`

After push:

`HEAD == origin/main == 31552933df41b4c8f769fb5b4237299d620a6380`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
Hermes made no source or test edit after integration.

## 2. Focused command sequence

Review 154 required a full restart of review 151's stop-on-first-failure sequence after
the test-correction integration commit was pushed. C1 and C2 returned exit 0. C3 returned
exit 1, so C4-C5, migration preconditions, the migration-only invocation, and after-proof
were not authorized and were not run.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 0

Output:

```text
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 94%]
......................                                                   [100%]
```

The invocation did not print a collected/pass summary line under `-q --tb=short`; Hermes
does not infer missing pass or collection counts.

### C2

Command:

`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`

Exit: 0

Output:

```text
..................                                                       [100%]
```

The invocation did not print a collected/pass summary line under `-q --tb=short`; Hermes
does not infer missing pass or collection counts.

### C3

Command:

`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`

Exit: 1

Ruff reported five `F401` failures, all in
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`:

- line 178: `execute_reviewed_v4_migration` imported but unused;
- line 188: `install_migrated_lock` imported but unused;
- line 189: `load_migrated_amendment_ledger` imported but unused;
- line 207: `prepare_amendment_ledger` imported but unused;
- line 209: `preserve_prior_lock_bytes` imported but unused.

Ruff reported all five findings as fixable with `--fix`. Hermes did not run `--fix`
because review 154 authorized no source/test edit after integration.

### C4-C5

Not run because C3 exited nonzero.

## 3. Migration disposition

No migration preconditions were captured. No `.env` migration environment was loaded. No
`--apply-reviewed-v4-migration-only` invocation was run. No ordinary resume, second
migration command, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, or next-ticket work
occurred.

No data, state, cache, report, manifest-detail, database sidecar, or unrelated dirty path
was staged by this publication.

## 4. Publication

This record publishes the test integration and required stop point only. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.
