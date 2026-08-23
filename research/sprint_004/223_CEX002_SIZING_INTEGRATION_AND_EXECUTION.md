# CEX-002 Sizing Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/222_CEX002_SIZING_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** failed sizing execution published for reviewer inspection
**Gate 1:** accepted
**Gate 2:** not accepted

## Scope

Hermes executed review 222's authorized integration and first local sizing invocation.
The first invocation exited nonzero, so authorization ended immediately. Hermes did not
retry, run the second idempotence invocation, repair, substitute an artifact, run pytest,
run Ruff, acquire data, normalize, publish a catalog, or perform any Harmonic Trader /
payoff / PAPER / LIVE / next-ticket work.

## Pre-execution proof

`HEAD == origin/main` at the review-222 publication commit:

```text
656512b38bcf17b0cbe0343b675f99729cd2c7a4
656512b38bcf17b0cbe0343b675f99729cd2c7a4
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `7e370adddcf03c531834e503654fc41946fd75f8ee662605b92b5cd16a4d7fb9` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `10d13532c754ec1c98c2db634c5c53402cee9f67f28f8aa5b60b26a1d5f90b63` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

Only the accepted sizing production and test paths differed among the three sizing paths:

```text
src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

The sizing test source contained 63 `def test_` functions. Per review 222, Hermes did not
rerun pytest or Ruff.

Required authority identities before execution:

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

Report-retained and selected-plus-cost facts from report 62:

| Fact | Value |
|---|---:|
| manifest consumable rows | 56 |
| retained valid requirement keys | 73 |
| retained verified credit objects | 73 |
| retained verified credit bytes | 5,225,416 |
| rejected retained rows | 176 |
| selected objects | 733,203 |
| selected bytes | 7,833,966,625 |
| cost objects | 3,144 |
| cost bytes | 12,522,974,218 |

The intended sizing outputs were absent:

```text
report180_exists=1
envelope_tree_exists=1
0
```

In the shell proof above, `1` is the `test -e` exit status for absent. There were zero
files under `data/cex002_qualify/evidence/sizing`.

No sizing or qualification process was running:

```text
pgrep -af '[s]ize_binance_usdm_harmonic_release|[b]inance_usdm_harmonic_sizing|[q]ualify_binance_usdm_harmonic_sources|[b]inance_usdm_harmonic_qualification'
exit status: 1
stdout: empty
```

Complete store pre-snapshot:

| Measurement | Value |
|---|---:|
| full `data/cex002_qualify` file count | 41,372 |
| full store manifest SHA-256 | `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead` |
| full store manifest line count | 41,372 |
| available bytes on destination filesystem | 158,696,816,640 |

## First sizing invocation

Hermes ran the exact first local invocation from review 222. No `.env` was loaded and no
network permission was requested.

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

Transcript:

```text
start_utc=2026-08-23T00:05:56Z
ERROR: a Coinalyze provenance record carries a credential field
end_utc=2026-08-23T00:08:31Z
elapsed_seconds=155
sizing_status=1
```

The first invocation exited status 1. Per review 222, this ended authorization. Hermes did
not run the second identical invocation.

## Post-failure proof

No valid sizing receipt was produced:

```text
report180_exists=1
envelope_tree_exists=1
0
```

Again, `1` is the `test -e` exit status for absent. There were zero sizing-envelope files.

The complete store was unchanged by the failed first invocation:

| Measurement | Value |
|---|---:|
| post file count | 41,372 |
| post full store manifest SHA-256 | `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead` |
| post full store manifest line count | 41,372 |
| manifest comparison status | 0 |
| post available bytes on destination filesystem | 159,537,266,688 |

Authority identities after the failed invocation remained:

| Artifact | SHA-256 |
|---|---|
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

Because the measurement failed with no valid receipt, Hermes will omit
`research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/223_CEX002_SIZING_INTEGRATION_AND_EXECUTION.md`;
4. `docs/handoff/CURRENT_TASK.md`; and
5. `tickets/CEX-002.md`.

Sizing envelopes, data/evidence files, database sidecars, DEX, BitMEX, catalog, ingest,
fixtures, and unrelated dirty paths are not staged.
