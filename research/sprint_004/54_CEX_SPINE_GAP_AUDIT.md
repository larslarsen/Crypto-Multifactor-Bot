# 54 — CEX Research Spine Gap Audit

**Date:** 2026-08-17
**Role:** Lead Quantitative Finance Researcher/Engineer review
**Purpose:** establish what is implemented before authorizing CEX-001

## Finding

The repository has a daily spot-bar panel, isolated source normalizers, and source-audit
evidence. It does not have an aligned, production CEX derivatives or microstructure
bundle. No retained product combines historical contract membership, trades/order-book
state, OI, funding, liquidations, basis, and costs on one venue clock.

DATA-011 accepted a 23-instrument Binance spot daily-bar panel. Its ticket explicitly did
not require full venue breadth. The Bybit implementation normalizes explicitly registered
local trade archives; the Sprint-003 audit inspected two real archive samples. Neither is
a complete historical production trade or order-book dataset. Repository source search
found no production OI, liquidation, basis, BBO/depth, or aligned-bundle publisher.

## Invalid BitMEX funding products

Direct PyArrow inspection of every retained `data/exp003_store/**/bitmex/**/funding.parquet`
file produced:

| Dataset ID | Type | Rows | Symbols | Nonzero rates | Empty intervals | Catalog state |
|---|---:|---:|---:|---:|---:|---|
| `ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933` | `bitmex_funding` | 14,376 | 2 | 0 | 14,376 | PASS / REGISTERED |
| `ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb` | `bitmex_funding` | 32,768 | 5 | 0 | 32,768 | PASS / REGISTERED |
| `ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea` | `bitmex_funding` | 32,768 | 5 | 0 | 32,768 | PASS / REGISTERED |
| `ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512` | `bitmex_funding` | 38,256 | 5 | 0 | 38,256 | PASS / REGISTERED |
| `ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8` | `bitmex_funding_full` | 189,570 | 45 | 0 | 189,570 | PASS / REGISTERED |

Total: **307,738 rows, zero nonzero funding rates, and 307,738 empty intervals**.
There are no null rates because the normalizer silently converts a missing source rate to
`0.0`.

Catalog inspection used `exp003.db` in SQLite read-only URI mode. The latest narrow and
full products resolve to `ds_ab70...` and `ds_ee8e...`; both are invalid. Artifacts and
manifests must be preserved but excluded from research resolution.

DATA-009 remained marked `AWAITING_REVIEW` despite producing `ds_ee8e...`. The reviewer
rejects and supersedes DATA-009 in the CEX-001 pivot; it is not an accepted predecessor.

## Source cause

`src/cryptofactors/ingest/bitmex_funding.py` currently:

- maps an absent `fundingRate` / `funding_rate` to `0.0`;
- derives missing `fundingRateDaily` as three times that value;
- accepts an empty funding interval; and
- loses the distinction between source event time and actual publication/availability
  when the latter is absent.

`scripts/research/backfill_bitmex_funding.py` publishes any non-empty merged table with
`QualityStatus.PASS`, including all-zero rates, empty intervals, empty symbols, and fetch
errors. Its unit tests use synthetic rows containing the expected old field names and do
not exercise a real source-field drift response.

## Why the capability appeared complete

The requirements were documented accurately, and the source audit produced deterministic
reports from real sample objects. But later records used words such as `EXECUTED`,
`realistic mechanics`, and `PASS` without proving that the experiment consumed accepted
microstructure products. This allowed requirements, parsers, sample audits, row-count
publication, and a working consumer stack to be conflated.

## Reviewer decision

ADR-0016 and CEX-001 replace that progression with one end-to-end acceptance boundary.
DEX-003 is superseded without acceptance. CEX-001 cannot pass until the historically
complete venue family, all required products, real non-empty economic fields, typed gaps,
provenance, reconciliation, resumability, clean release, and consumer harness all exist.
