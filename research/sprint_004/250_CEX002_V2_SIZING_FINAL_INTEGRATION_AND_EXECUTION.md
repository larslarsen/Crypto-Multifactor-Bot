# CEX-002 V2 Sizing Final Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/249_CEX002_V2_RECEIPT_BOUNDARY_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** first real sizing invocation failed; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 249 through exact-byte preproof, focused validation, exact-path
Ruff, and the first real v2 sizing invocation. The focused pytest and Ruff checks passed.
The first real sizing invocation exited nonzero, so Hermes stopped immediately as required.
Hermes did not run the second idempotence invocation, did not request network access, did
not load `.env`, did not acquire data, did not normalize a release, did not publish a
catalog, did not perform NautilusTrader or Harmonic Trader work, and did not start later
work.

## Preproof

`HEAD == origin/main` before execution:

```text
7f68217b00e7bdc3d1b336f85dc562295dce78bc
7f68217b00e7bdc3d1b336f85dc562295dce78bc
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `32153fe509929eedd64731f57046eb0cc838cb3296ea681e195481358af694bc` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `6a9fdb3103f9259545864d5341a1d61739df15e9669b2a325fa8a615cae327a3` |
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
sha256: 64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113
```

Hermes did not delete or rewrite any v1 receipt or v1 envelope.

## Focused Pytest

Hermes ran the exact focused validation command from review 249:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Result:

```text
exit status: 0
```

## Exact-Path Ruff

Hermes ran the exact Ruff command from review 249:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
```

Result:

```text
All checks passed!
exit status: 0
```

## First Real V2 Sizing Invocation

After both validation commands passed, Hermes ran the first real v2 sizing invocation
without `.env` and without requesting network access:

```bash
date -u +start_utc=%Y-%m-%dT%H:%M:%SZ
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
date -u +end_utc=%Y-%m-%dT%H:%M:%SZ
printf 'sizing_status=%s\n' "$sizing_status"
exit "$sizing_status"
```

Result:

```text
start_utc=2026-08-23T07:50:17Z
ERROR: a typed integer column is not a strict integer
end_utc=2026-08-23T07:52:53Z
sizing_status=1
elapsed_seconds=156
```

The first invocation exited status 1. Per review 249, Hermes stopped immediately and did
not run the second identical idempotence invocation.

## Post-Failure Evidence

No valid receipt was produced:

```text
test -e research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json
exit status: 1
```

No v2 sizing Parquet evidence directory existed after the failed invocation:

```text
find data/cex002_qualify/evidence/sizing/v2 -type f -printf '%p %s\n'
exit status: 1
stderr: find: 'data/cex002_qualify/evidence/sizing/v2': No such file or directory
```

Accepted source/test/CLI and manifest identities after the failed invocation:

| Artifact | SHA-256 |
|---|---|
| sizing production | `32153fe509929eedd64731f57046eb0cc838cb3296ea681e195481358af694bc` |
| sizing test | `6a9fdb3103f9259545864d5341a1d61739df15e9669b2a325fa8a615cae327a3` |
| sizing CLI | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |
| manifest detail gzip | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |

Post-failure destination filesystem availability:

```text
/dev/mapper/ubuntu--vg-ubuntu--lv 980105256960 775537864704 154705297408  84% /home/lars/Crypto_Multifactor_Bot
```

Because the sizing command exited nonzero before producing a receipt, there are no valid
receipt identity/size facts, envelope published/reused counts, storage state, blockers,
six-component capacity equation, total required bytes, post-publication available bytes,
or idempotence facts to report. Gate 2 remains not accepted.

## Publication

Hermes stages only the two accepted modified sizing paths, this record, and the two
control-plane files. Receipt 231 is omitted because it was not produced. The unchanged
CLI, unrelated dirty files, database sidecars, data evidence, v1 receipts, and v1
envelopes remain untouched and unstaged.
