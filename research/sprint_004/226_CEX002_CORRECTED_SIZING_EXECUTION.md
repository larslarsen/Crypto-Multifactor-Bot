# CEX-002 Corrected Sizing Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/225_CEX002_COINALYZE_PROVENANCE_SOURCE_ACCEPTANCE.md`
**Decision status:** validation passed; corrected sizing execution failed before receipt
**Gate 1:** accepted
**Gate 2:** not accepted

## Scope

Hermes executed review 225's authorized sequence in the shared dirty workspace. Hermes did
not pull, reset, checkout, restore, or stash. Hermes did not edit source, repair the
failure, retry, run the second idempotence invocation, load `.env`, request network,
acquire data, normalize, publish a catalog, or perform Harmonic Trader / payoff / PAPER /
LIVE / next-ticket work.

## Preproof

`HEAD == origin/main` at the review-225 publication commit:

```text
a9b319898a0b162ff28dd0b5bbb55961fd9b9ac2
a9b319898a0b162ff28dd0b5bbb55961fd9b9ac2
```

Only the two accepted sizing paths differed from `HEAD` among sizing source/test/CLI:

```text
src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

Accepted sizing identities:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | 120,568 | `bcaca1b1907a89df5020cdbd33c44f49471ff67d0c97d1a303c8225c2cabb592` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | 102,711 | `0a9a3cf0978b596130323e36e495e4fa4d0bc018f21a6d44341e8b9e3bab8177` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | 5,602 | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

The corrected test file contained 71 `def test_` functions.

Required authority identities matched record 223 / review 225:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| report 62 | 13,745,360 | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` |
| manifest detail gzip | 11,292,635 | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| live lock | 428,097 | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| amendment ledger | 26,677 | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| qualification production | 512,435 | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| qualification CLI | 18,571 | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| progress checkpoint | 487,815 | `cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,774 | `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| legacy budget ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |

Sizing outputs were absent before validation and execution:

```text
report180_exists=1
envelope_tree_exists=1
0
```

In the shell proof above, `1` is the `test -e` exit status for absent. There were zero
sizing-envelope files.

No sizing or qualification process was running:

```text
pgrep -af '[s]ize_binance_usdm_harmonic_release|[b]inance_usdm_harmonic_sizing|[q]ualify_binance_usdm_harmonic_sources|[b]inance_usdm_harmonic_qualification'
exit status: 1
stdout: empty
```

Complete store pre-snapshot:

| Measurement | Value |
|---|---:|
| file count | 41,372 |
| full store manifest SHA-256 | `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead` |
| full store manifest line count | 41,372 |
| destination available bytes | 159,144,464,384 |

## Focused validation

Hermes ran the exact focused pytest command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
focused_status=$?
```

Transcript:

```text
start_utc=2026-08-23T00:39:23Z
........................................................................ [ 47%]
........................................................................ [ 94%]
.........                                                                [100%]
end_utc=2026-08-23T00:39:27Z
elapsed_seconds=4
focused_status=0
```

The focused suite exited 0 and displayed 153 passing case dots.

Hermes then ran the exact-path Ruff command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
ruff_status=$?
```

Transcript:

```text
start_utc=2026-08-23T00:39:35Z
All checks passed!
end_utc=2026-08-23T00:39:36Z
elapsed_seconds=1
ruff_status=0
```

After both validation commands, the three sizing path hashes still matched the accepted
review-225 identities.

## First corrected sizing invocation

Because both validations passed, Hermes ran the first exact corrected local sizing
invocation. Hermes did not load `.env` and did not request network.

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

Transcript:

```text
start_utc=2026-08-23T00:39:52Z
ERROR: the retained liquidation response covers an unsupported symbol
end_utc=2026-08-23T00:42:32Z
elapsed_seconds=160
sizing_status=1
```

The first corrected sizing invocation exited status 1. Per review 225, this ended
authorization. Hermes did not retry and did not run the second identical idempotence
invocation.

## Post-failure proof

No valid sizing receipt was produced:

```text
report180_exists=1
```

The sizing envelope tree was created before the failure:

| Measurement | Value |
|---|---:|
| envelope files | 96 |
| envelope total bytes | 1,890,921 |
| envelope hash-list SHA-256 | `b4d52ac991a64aabc36f116f3cf7cf4b3381f9bae72119226b4f0f5aad18bdc4` |

The complete store changed only by the failed sizing run's ignored data evidence:

| Measurement | Before | After |
|---|---:|---:|
| file count | 41,372 | 41,468 |
| full store manifest SHA-256 | `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead` | `361095f2be95d9efab91046b910f76cc514e8e2fc1a79e1d359ead2f13ddedb6` |
| destination available bytes | 159,144,464,384 | 158,958,542,848 |

Authority identities after the failed invocation remained:

| Artifact | SHA-256 |
|---|---|
| sizing production | `bcaca1b1907a89df5020cdbd33c44f49471ff67d0c97d1a303c8225c2cabb592` |
| sizing tests | `0a9a3cf0978b596130323e36e495e4fa4d0bc018f21a6d44341e8b9e3bab8177` |
| sizing CLI | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |
| report 62 | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` |
| manifest detail gzip | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| live lock | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| amendment ledger | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| progress checkpoint | `cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f` |
| listing checkpoint | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42` |
| sample plan | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| retry journal | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| legacy budget ledger | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |

## Publication plan

Because the corrected sizing invocation failed without a valid receipt, Hermes will omit
`research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/226_CEX002_CORRECTED_SIZING_EXECUTION.md`;
4. `docs/handoff/CURRENT_TASK.md`; and
5. `tickets/CEX-002.md`.

Sizing envelopes are ignored data evidence and are not staged. Unrelated dirty, database,
DEX, BitMEX, catalog, ingest, fixture, and other data paths are not staged.
