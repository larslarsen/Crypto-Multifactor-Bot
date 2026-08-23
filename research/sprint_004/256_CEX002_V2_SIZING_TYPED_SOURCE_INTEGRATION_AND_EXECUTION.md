# CEX-002 V2 Sizing Typed Source Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/255_CEX002_REAL_TYPED_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** valid blocked sizing receipt produced; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 255 through exact-byte preproof, focused validation, exact-path
Ruff, one real v2 sizing invocation, and one identical idempotence invocation. Both
validation commands passed. Both real sizing invocations exited 0. The first invocation
published receipt 231 and 151 v2 sizing envelopes. The second invocation re-proved the
same receipt, published zero new envelopes, and reused all 151 envelopes.

The receipt is a valid blocked measurement: storage preflight state is `blocked` with
blocker `available_capacity_insufficient`. This record does not accept Gate 2 and does
not authorize acquisition, normalization, catalog publication, NautilusTrader, Harmonic
Trader, PAPER/LIVE, or later work.

## Preproof

`HEAD == origin/main` before execution:

```text
d38a5cee9d183615878ef38ce83b7ec05994e8e7
d38a5cee9d183615878ef38ce83b7ec05994e8e7
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `39eff6a986e114b1c07f5af976709179a8ec5c5ad5d113b6dc4ae743df60d468` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `96c9bb542c32d0e1b4161e3d2b0c247c1496dd926662096ffac3a03624bca165` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The sizing test source contained 144 `def test_` functions.

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

Hermes ran the exact focused validation command from review 255:

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

Hermes ran the exact Ruff command from review 255:

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
start_utc=2026-08-23T08:32:02Z
cex002_gate2_storage_sizing_v2 receipt written at research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json
envelopes_published=151 envelopes_reused=0
receipt_sha256=d3b2e81e46ecb17ea98dee160a98a551720b4bb27f5c29497839081acabaad29 receipt_bytes=39553673
storage_preflight_state=blocked total_future_storage_bytes=646431826972 post_publication_available_bytes=154464187767
typed_normalized_partition_bytes=584035445256 catalog_manifest_bundle_bytes=5556368003 bounded_temporary_work_bytes=5556368003
blockers: available_capacity_insufficient
end_utc=2026-08-23T08:34:37Z
sizing_status=0
elapsed_seconds=155
```

## Idempotence Invocation

Because the first invocation exited 0, Hermes ran the identical command exactly once more:

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
start_utc=2026-08-23T08:34:43Z
cex002_gate2_storage_sizing_v2 receipt re-proved at research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json
envelopes_published=0 envelopes_reused=151
receipt_sha256=d3b2e81e46ecb17ea98dee160a98a551720b4bb27f5c29497839081acabaad29 receipt_bytes=39553673
storage_preflight_state=blocked total_future_storage_bytes=646431826972 post_publication_available_bytes=154464187767
typed_normalized_partition_bytes=584035445256 catalog_manifest_bundle_bytes=5556368003 bounded_temporary_work_bytes=5556368003
blockers: available_capacity_insufficient
end_utc=2026-08-23T08:37:17Z
sizing_status=0
elapsed_seconds=154
```

The idempotence invocation returned the same receipt SHA-256 and byte length, published
zero new envelopes, reused all 151 envelopes, and preserved the same blocked storage
state, blocker, total, and reported component values.

## Receipt and Capacity Facts

Receipt 231:

| Fact | Value |
|---|---:|
| path | `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` |
| SHA-256 | `d3b2e81e46ecb17ea98dee160a98a551720b4bb27f5c29497839081acabaad29` |
| bytes | 39,553,673 |
| schema version | `cex002_gate2_storage_sizing_v2` |
| storage preflight state | `blocked` |
| blocker | `available_capacity_insufficient` |

Capacity equation:

```text
new Binance raw + new Coinalyze raw + typed normalized partitions + catalog/manifest/bundle + bounded temporary work + operating reserve, counted once and without overlap
```

Capacity components:

| Component | Bytes |
|---|---:|
| new Binance raw | 20,351,715,427 |
| new Coinalyze raw | 30,580,702 |
| typed normalized partitions | 584,035,445,256 |
| catalog/manifest/bundle | 5,556,368,003 |
| bounded temporary work | 5,556,368,003 |
| operating reserve | 30,901,349,581 |
| total future storage | 646,431,826,972 |
| post-publication available | 154,464,187,767 |

Receipt counts:

| Count | Value |
|---|---:|
| accepted membership identities | 771 |
| membership rows | 771 |
| physical raw objects | 736,347 |
| projected normalized files | 291,255 |
| projected acquisition receipts | 736,917 |
| projected Coinalyze receipts | 570 |
| required products | 11 |
| sizing envelopes | 151 |
| typed gap rows | 202 |

Receipt authority bindings include:

| Binding | SHA-256 |
|---|---|
| report | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` |
| manifest detail gzip | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| manifest detail uncompressed | `d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17` |
| live lock | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| amendment ledger | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| progress checkpoint | `cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f` |
| listing checkpoint | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| contract metadata | `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42` |
| qualification source | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| qualification CLI | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| plan digest | `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef` |
| code/config digest | `86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb` |

## V2 Evidence

V2 sizing envelopes are data evidence and are not staged.

| Fact | Value |
|---|---:|
| parquet envelope files | 151 |
| total retained sizing evidence bytes | 2,612,518 |
| sorted envelope manifest SHA-256 | `20d8c833cfb3f5264104b4059d5c03431635e3fa29fb2e2d6d98234861762c5a` |

Final identity checks after both invocations:

| Artifact | SHA-256 |
|---|---|
| receipt 231 | `d3b2e81e46ecb17ea98dee160a98a551720b4bb27f5c29497839081acabaad29` |
| sizing production | `39eff6a986e114b1c07f5af976709179a8ec5c5ad5d113b6dc4ae743df60d468` |
| sizing test | `96c9bb542c32d0e1b4161e3d2b0c247c1496dd926662096ffac3a03624bca165` |
| sizing CLI | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |
| manifest detail gzip | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |

## Publication

Hermes stages only the two accepted modified sizing paths, this record, receipt 231, and
the two control-plane files. V2 envelopes, unrelated dirty files, database sidecars, v1
receipts, and v1 envelopes remain untouched and unstaged.
