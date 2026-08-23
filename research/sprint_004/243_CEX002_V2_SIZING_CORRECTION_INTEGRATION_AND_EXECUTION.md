# CEX-002 V2 Sizing Correction Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/242_CEX002_V2_SIZING_CORRECTION_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** focused validation failed; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 242 through exact-byte preproof, staged only the two accepted
modified sizing paths, and ran the authorized focused pytest validation once. The focused
pytest command exited nonzero. Per review 242, Hermes stopped before Ruff and before any
real v2 sizing invocation. Hermes did not request network access, load `.env`, acquire
data, normalize a release, publish a catalog, perform NautilusTrader or Harmonic Trader
work, or start later work.

## Preproof

`HEAD == origin/main` before execution:

```text
9ba9a07cde578f2450b17557d4de72a62da062bb
9ba9a07cde578f2450b17557d4de72a62da062bb
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `7ca6082f9c52f4d6b5a770647ecd452cea8c279faa41811ad31d7fc70f44b4c9` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `1867f9d271a1d4e04eab931209a08451a948938e5df42ad8619c1c1d062cc0a4` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The sizing test source contained 138 `def test_` functions.

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

Hermes ran the exact focused validation command from review 242:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Result:

```text
exit status: 1
tool-reported wall time: 7.7909 seconds
publication_utc_after_failure=2026-08-23T06:40:22Z
```

The command was not wrapped with shell-level start/end timestamp capture before execution;
the exact shell timestamps are therefore unavailable.

Pytest reported four failing tests:

```text
test_end_to_end_receipt_is_complete_and_durably_identical
test_v2_envelopes_are_content_addressed_and_reused_not_rewritten
test_rerun_returns_the_identical_receipt_under_changed_observations
test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt
```

The first failure was a capacity-equation assertion:

```text
tests/acquisition/test_binance_usdm_harmonic_sizing.py:2958:
assert 200457493 < (10822789 + 1094722)
```

The three rerun/idempotence failures were receipt target collisions:

```text
cryptofactors.acquisition.binance_usdm_harmonic_sizing.SizingError:
a different sizing receipt already occupies its target |
context={'name': '231_receipt.json'}
```

## Commands Not Run

Because focused pytest exited 1, review 242 prohibited further execution. Hermes did not
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
