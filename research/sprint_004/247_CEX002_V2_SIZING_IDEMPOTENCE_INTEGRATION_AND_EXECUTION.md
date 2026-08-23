# CEX-002 V2 Sizing Idempotence Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/246_CEX002_V2_SIZING_IDEMPOTENCE_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** focused validation failed; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 246 through exact-byte preproof, staged only the two accepted
modified sizing paths, and ran the authorized focused pytest validation once. The focused
pytest command exited nonzero. Per review 246, Hermes stopped before Ruff and before any
real v2 sizing invocation. Hermes did not request network access, load `.env`, acquire
data, normalize a release, publish a catalog, perform NautilusTrader or Harmonic Trader
work, or start later work.

## Preproof

`HEAD == origin/main` before execution:

```text
f325fda5a7d22ee0c1a1933031b305b30be438f4
f325fda5a7d22ee0c1a1933031b305b30be438f4
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `f0f4f89d5e571ea586f0d6746f20cb7aad2115156b73719e8d1c7ac1cec7d550` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `5029d4cf7d1a7af507cc49d0766bf87c477c60ea13c3647e8092fe8fbfc46bf9` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The sizing test source contained 139 `def test_` functions.

No sizing or qualification process was running:

```text
ps -eo pid=,args= | rg '[b]inance_usdm_harmonic_sizing|[s]ize_binance_usdm_harmonic_release|[p]ytest.*harmonic_sizing|[q]ualify_binance_usdm_harmonic'
exit status: 1
stdout: empty
```

Receipt 231 was absent:

```text
test -e research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json
exit status: 1
```

The v2 evidence directory had no Parquet files:

```text
find data/cex002_qualify/evidence/sizing/v2 -type f -name '*.parquet' -print
exit status: 1
stderr: find: 'data/cex002_qualify/evidence/sizing/v2': No such file or directory
```

The accepted manifest detail existed:

```text
data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
test -f exit status: 0
```

Hermes did not delete or rewrite any v1 receipt or v1 envelope.

## Focused Pytest

Hermes ran the exact focused validation command from review 246:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Result:

```text
exit status: 1
tool-reported wall time: 7.3892 seconds
publication_utc_after_failure=2026-08-23T07:20:38Z
```

Pytest reported three failing tests:

```text
test_end_to_end_receipt_is_complete_and_durably_identical
test_rerun_returns_the_identical_receipt_under_changed_observations
test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt
```

The first failure was a product-name assertion in the receipt block:

```text
tests/acquisition/test_binance_usdm_harmonic_sizing.py:3150:
assert block["required_product"] == product
E   AssertionError: assert 'binance_usdm...t_calibration' == 'official_fee_schedule'
E     - official_fee_schedule
E     + binance_usdm_cost_calibration
```

The two rerun/idempotence tests failed because the second receipt differed from the first:

```text
tests/acquisition/test_binance_usdm_harmonic_sizing.py:5014:
assert second["receipt"] == first["receipt"]

tests/acquisition/test_binance_usdm_harmonic_sizing.py:5031:
assert second["receipt"] == first["receipt"]
```

Pytest reported differing `counts` and `coverage_authority` receipt sections. The output
was truncated by pytest's short traceback rendering.

## Commands Not Run

Because focused pytest exited 1, review 246 prohibited further execution. Hermes did not
run:

- exact-path Ruff;
- the first real v2 sizing invocation;
- the second idempotence invocation.

## Receipt and Data Evidence

No valid `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` receipt was
produced. The real sizing CLI was not run, so there are no v2 receipt facts, capacity
equations, post-publication storage facts, or idempotence facts to report. Gate 2 remains
not accepted.

## Publication

Hermes stages only the two accepted modified sizing paths, this record, and the two
control-plane files. The unchanged CLI, unrelated dirty files, database sidecars, data
evidence, v1 receipts, and v1 envelopes remain untouched and unstaged.
