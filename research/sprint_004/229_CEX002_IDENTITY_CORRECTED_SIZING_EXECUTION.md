# CEX-002 Identity-Corrected Sizing Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/228_CEX002_IDENTITY_SOURCE_ACCEPTANCE_AND_SIZING_RETRY.md`
**Decision status:** sizing measurement published; reviewer inspection pending
**Gate 1:** accepted
**Gate 2:** not accepted by Hermes

## Scope

Hermes executed review 228's bounded sequence in the shared dirty workspace. Hermes did
not pull, reset, checkout, restore, stash, delete, or rewrite the workspace or existing
sizing envelopes. Hermes did not repair source, load `.env`, request network, accept Gate
2, acquire data, normalize, publish a catalog, or perform NautilusTrader / Harmonic
Trader / payoff / PAPER / LIVE / next-ticket work.

## Preproof

`HEAD == origin/main` at the review-228 publication commit:

```text
84824e4f23c3cc444c988f7c4d637dbd02eb3c78
84824e4f23c3cc444c988f7c4d637dbd02eb3c78
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `aafdf65733e2865f92d89d75ce4a4ba934ce240d3d816e37a9fbe0072749ca82` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `343d422ce86d217d39459b49d40308125065b6a7873459c7d27ca37a6eda12c8` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

The corrected test file contained 85 `def test_` functions.

Record-226 authority identities matched:

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

Receipt 180 was absent before execution:

```text
report180_exists=1
```

The existing ignored sizing evidence was preserved:

| Measurement | Value |
|---|---:|
| existing envelope files | 96 |
| existing envelope bytes | 1,890,921 |
| full evidence-store file count | 41,468 |
| full evidence-store manifest SHA-256 | `361095f2be95d9efab91046b910f76cc514e8e2fc1a79e1d359ead2f13ddedb6` |
| destination available bytes | 158,614,986,752 |

No sizing or qualification process was running.

Real-authority identity facts reproduced from the pinned report:

| Fact | Value |
|---|---:|
| future-market provider identities | 759 |
| future-market native identities | 759 |
| report `binance_perpetual_market_count` | 759 |
| report `native_identity_validated_markets` | 759 |
| supported native identities | 569 |
| unique supported native identities | 569 |
| unmapped native identities | 202 |
| unique unmapped native identities | 202 |
| supported/unmapped disjoint | true |
| supported ∪ unmapped | 771 |
| accepted membership identities | 771 |
| union equals accepted membership | true |
| inventory identities outside supported projection | 190 |

Retained provider/native anchors:

| Provider identity | Native identity |
|---|---|
| `BTCUSDT_PERP.A` | `BTCUSDT` |
| `ETHUSDT_PERP.A` | `ETHUSDT` |

## Focused validation

Focused pytest:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
focused_status=$?
```

Transcript:

```text
start_utc=2026-08-23T01:15:54Z
........................................................................ [ 39%]
........................................................................ [ 79%]
.....................................                                    [100%]
end_utc=2026-08-23T01:15:58Z
elapsed_seconds=4
focused_status=0
```

The focused suite exited 0 and displayed 181 passing case dots.

Exact-path Ruff:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
ruff_status=$?
```

Transcript:

```text
start_utc=2026-08-23T01:16:05Z
All checks passed!
end_utc=2026-08-23T01:16:05Z
elapsed_seconds=0
ruff_status=0
```

After validation, all three sizing path hashes still matched review 228.

## First sizing invocation

Hermes ran the exact local sizing command. No `.env` was loaded and no network permission
was requested.

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

Transcript:

```text
start_utc=2026-08-23T01:16:20Z
sizing receipt written at research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json
envelopes_published=2 envelopes_reused=96
receipt_sha256=f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c receipt_bytes=141595
storage_preflight_state=blocked total_future_storage_bytes=432141608507 post_publication_available_bytes=158559266533
blockers: available_capacity_insufficient
end_utc=2026-08-23T01:18:53Z
elapsed_seconds=152
sizing_status=0
```

After the first successful invocation:

- receipt 180 SHA-256: `f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c`;
- receipt bytes: 141,595;
- envelope files: 98;
- envelope bytes: 1,908,201;
- evidence-store manifest SHA-256:
  `2a6fe68854bb30e3b8e4e2a80e06481b92cde07c5ef39f32d4655d705a3e4857`;
- evidence-store file count: 41,470.

## Second idempotence invocation

Because the first sizing invocation exited 0, Hermes ran the identical command exactly
once more.

Transcript:

```text
start_utc=2026-08-23T01:19:35Z
sizing receipt re-proved at research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json
envelopes_published=0 envelopes_reused=98
receipt_sha256=f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c receipt_bytes=141595
storage_preflight_state=blocked total_future_storage_bytes=432141608507 post_publication_available_bytes=158559266533
blockers: available_capacity_insufficient
end_utc=2026-08-23T01:22:10Z
elapsed_seconds=155
sizing_status=0
```

Second-run idempotence proof:

| Measurement | Value |
|---|---:|
| receipt SHA-256 | `f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c` |
| receipt bytes | 141,595 |
| envelopes published | 0 |
| envelopes reused | 98 |
| full evidence-store manifest SHA-256 | `2a6fe68854bb30e3b8e4e2a80e06481b92cde07c5ef39f32d4655d705a3e4857` |
| full evidence-store file count | 41,470 |
| first/second manifest comparison | identical |
| final destination available bytes | 158,558,867,456 |

## Receipt facts

Receipt path: `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`

| Field | Value |
|---|---|
| schema | `cex002_gate2_storage_sizing_v1` |
| ticket | `CEX-002` |
| storage preflight state | `blocked` |
| blocker | `available_capacity_insufficient` |
| authorization text | sufficient storage preflight is measurement only; it accepts no gate, authorizes no acquisition, and changes no ticket state |

Retained decomposition and raw inputs:

| Fact | Value |
|---|---:|
| manifest consumable rows | 56 |
| selected retained keys | 68 |
| cost retained keys | 5 |
| valid requirement keys | 73 |
| retained credit objects | 73 |
| retained credit bytes | 5,225,416 |
| selected objects | 733,203 |
| selected bytes | 7,833,966,625 |
| cost objects | 3,144 |
| cost bytes | 12,522,974,218 |
| combined objects | 736,347 |
| combined bytes | 20,356,940,843 |
| projected new Binance raw bytes | 20,351,715,427 |

Coinalyze facts:

| Fact | Value |
|---|---:|
| inventory mappings | 759 |
| supported native mappings | 569 |
| typed gap native symbols | 202 |
| retained provider symbols | `BTCUSDT_PERP.A`, `ETHUSDT_PERP.A` |
| retained native symbols | `BTCUSDT`, `ETHUSDT` |
| projected acquisition receipts | 570 |
| projected new raw bytes | 29,072,901 |
| projected normalized bytes | 12,621,439 |
| projected points | 486,056 |
| partition count | 16,419 |
| largest partition bytes | 805 |
| retained receipts | 2 |
| retained points | 686 |
| retained raw bytes | 1,490,459 |

Coinalyze retained liquidation envelopes:

| Provider | Native | Points | Raw point bytes | Parquet bytes | Parquet SHA-256 |
|---|---|---:|---:|---:|---|
| `BTCUSDT_PERP.A` | `BTCUSDT` | 343 | 20,535 | 8,692 | `238c7ef3792adfa831750a57ad6e9dedbe0b644a0b1b3fd862e95f5320d5bb99` |
| `ETHUSDT_PERP.A` | `ETHUSDT` | 343 | 19,524 | 8,588 | `d9194306faa536b157982e16db7f772e5966166c180b351a30644771326f8e29` |

Capacity:

| Component | Bytes |
|---|---:|
| new Binance raw | 20,351,715,427 |
| new Coinalyze raw | 29,072,901 |
| normalized catalog | 188,932,621,323 |
| temporary high water | 191,116,312,315 |
| operating reserve | 31,711,886,541 |
| total future storage | 432,141,608,507 |
| post-publication available | 158,559,266,533 |

Total future storage is 432.141608507 decimal GB, or 402.463235433 binary GiB. The
preflight is blocked for insufficient available capacity.

Family projections:

| Family | Objects | Input bytes | Projected bytes | Partitions | Multiplicity | Ratio | Largest partition |
|---|---:|---:|---:|---:|---:|---|---:|
| `daily/klines` | 13,710 | 16,175,845 | 240,695,244 | 1,402 | 2 | 4769/641 | 230,594 |
| `daily/metrics` | 573,786 | 6,112,309,876 | 60,465,126,261 | 19,744 | 1 | 3492/353 | 4,543,053 |
| `daily/premiumIndexKlines` | 11,439 | 8,452,758 | 242,509,304 | 1,150 | 2 | 4117/287 | 258,496 |
| `daily/markPriceKlines` | 14,096 | 10,458,575 | 143,996,231 | 713 | 1 | 4158/302 | 296,485 |
| `daily/indexPriceKlines` | 12,266 | 10,088,018 | 120,296,280 | 653 | 1 | 4114/345 | 282,078 |
| `monthly/klines` | 21,932 | 645,500,209 | 2,102,089,104 | 43,864 | 2 | 11033/6776 | 68,271 |
| `monthly/fundingRate` | 21,035 | 21,351,804 | 120,773,954 | 21,035 | 1 | 2449/433 | 33,336 |
| `monthly/premiumIndexKlines` | 20,932 | 290,695,727 | 1,993,727,574 | 41,864 | 2 | 6248/1822 | 66,037 |
| `monthly/markPriceKlines` | 22,286 | 346,831,322 | 1,089,928,542 | 22,286 | 1 | 6285/2000 | 85,574 |
| `monthly/indexPriceKlines` | 21,721 | 372,102,491 | 881,928,325 | 21,721 | 1 | 7909/3337 | 67,809 |
| `daily/bookTicker` | 909 | 11,692,468,351 | 112,793,591,029 | 866 | 1 | 3058/317 | 2,183,690,992 |
| `daily/bookDepth` | 2,235 | 830,505,867 | 4,882,541,321 | 2,226 | 1 | 2575/438 | 6,597,539 |

## Publication plan

Because sizing succeeded and produced a valid receipt, Hermes will stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`;
4. `research/sprint_004/229_CEX002_IDENTITY_CORRECTED_SIZING_EXECUTION.md`;
5. `docs/handoff/CURRENT_TASK.md`; and
6. `tickets/CEX-002.md`.

Sizing envelopes are ignored evidence and are not staged. Unrelated dirty, database, DEX,
BitMEX, catalog, ingest, fixture, and other data paths are not staged.
