# CEX-002 Review 446 — Hourly Kline Architecture and Source Authorization

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** authorize one bounded Sol High source/test drop for the two hourly kline products
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol, High
- **Next ticket:** `NONE`

## Plain-language decision

The hourly price data does not need another download. All 35,642 selected hourly kline ZIPs are
already present in the accepted generation-0 store, authenticated by their Binance checksum
sidecars, and terminal in the accepted acquisition database. A complete read-only scan found a
clean 16,033,509-row corpus. The next job is one local conversion: read those ZIPs once and publish
two separate immutable tables, one containing prices and one containing buy/sell volume.

The existing generic BIN-001 parser is useful evidence but is not the CEX-002 publication adapter.
It publishes one generic file per raw object, uses a different schema, and does not authenticate the
accepted generation-0 authority or publish CEX-002 product/symbol/month completion descriptors.
Changing the raw data or running another acquisition would not solve that mismatch. This review
therefore authorizes one dedicated, bounded CEX-002 normalizer rather than another download or a
new framework.

This implements the already accepted ADR-0024 partition-atomic publication architecture. It does
not change a layer boundary and requires no ADR amendment.

## Read-only authority and corpus proof

The reviewer inspected `data/cex002_qualify/gate2/state.sqlite` in read-only mode and the exact
content-addressed objects beneath `data/cex002_qualify/gate2/content`. No repository data or source
was changed by this inspection.

The accepted generation-0 authority contains:

| family | completions | compressed bytes | symbols |
|---|---:|---:|---:|
| `daily/klines` | 13,710 | 16,175,845 | 698 |
| `monthly/klines` | 21,932 | 645,500,209 | 766 |
| total | 35,642 | 661,676,054 | 767 union |

Of the 35,642 completions, 35,633 have `checksum_verified` validation state and nine have the
accepted `retained_credit` state. Every selected completion has a matching sidecar fact, and every
provider checksum equals the content SHA-256. The accepted generation-0 seal head remains
`8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab` and the total accepted
Binance completion count remains 685,072. The V3 recovery manifest is not an input to these two
products because every selected kline object is already a completed generation-0 object.

The full read-only ZIP/CSV scan found:

- 35,642 safe one-member ZIPs and 16,033,509 physical/economic rows;
- 329,025 daily rows and 15,704,484 monthly rows;
- 767 native symbols and 22,633 distinct native-symbol/UTC-month partitions;
- coverage from `2019-12-31T00:00:00Z` through `2026-08-20T23:00:00Z`;
- 33,614 headed objects and 2,028 headerless objects;
- all timestamps in integer milliseconds, exactly hour aligned, with close time equal to open time
  plus 3,599,999 milliseconds;
- zero corrupt archives, unsafe members, checksum/size mismatches, malformed widths, timestamp
  failures, filename-period violations, OHLC violations, negative volume/count values, duplicate
  timestamps, conflicting duplicates, daily/monthly overlap, or decimal conversion failures;
- a maximum of 744 rows in an object, a maximum 41,725-byte compressed CSV member, and a maximum
  104,421-byte uncompressed CSV member; and
- no excluded or collapsed row and no repeated economic interval.

The exact product-row equation for each hourly product is therefore:

`16,033,509 physical rows - 0 duplicates - 0 overlaps - 0 exclusions = 16,033,509 product rows`.

The scan also found 114 real missing-hour runs totaling 8,003 missing hours across 61 symbols:

- 12 within-object runs totaling 223 hours;
- 102 between-object runs totaling 7,780 hours; and
- run-length distribution `7×1, 8×1, 10×1, 11×4, 17×2, 24×2, 48×50, 72×50, 518×1,
  626×1, 708×1`.

Those are source coverage facts, not bad rows. They must become typed gap records for both products
and must never be filled, interpolated, silently dropped, or presented as continuous history. The
normalizer recomputes them from authenticated rows; it does not hard-code the review totals.

The accepted V3 sizing receipt conservatively projects 17,799,707 rows and 22,633 partitions per
product. Its byte bounds are 1,398,403,824 for `binance_usdm_bar_1h` and 2,477,294,735 for
`binance_usdm_trade_flow_1h`. Current available space is 47,402,745,856 bytes. Before a future real
run Hermes must reprove that available space is at least the frozen 29,690,701,415-byte operating
reserve plus both product bounds and the greatest 145,283-byte projected partition temporary:
33,566,545,257 bytes. No data run is authorized by this review.

## Frozen economic contract

One authenticated source row has exactly the accepted 12-field kline shape:

`open_time, open, high, low, close, volume, close_time, quote_volume, count,
taker_buy_volume, taker_buy_quote_volume, ignore`.

Both headed and headerless files are supported. Only the exact accepted kline header may be skipped;
an arbitrary nonnumeric first row fails. Every ZIP must remain a safe, unencrypted, single root CSV
whose member name and every row agree with its authenticated source identity, symbol, interval, and
daily or monthly economic period. Parser safety bounds must exceed the proved complete corpus while
remaining finite; the rejected acquisition ZIP-expansion ceiling is not reused as a semantic filter.

All source timestamps, prices, quantities, volumes, counts, and the reserved trailing integer are
preserved without binary-float conversion or silent rounding. Decimal values use the accepted exact
`decimal128(38,18)` conversion. Prices must be positive; volumes and trade counts must be
non-negative; `high` must be no lower than open, close, and low; `low` must be no higher than open,
close, and high; and taker-buy base/quote volume must lie between zero and the corresponding total.
Any violation fails the run without publishing a completion descriptor.

The two required products remain separate:

1. `binance_usdm_bar_1h` publishes the accepted final schema directly from OHLCV, quote volume,
   count, the reserved source integer, partition-local lineage reference, row ordinal, and native
   identity.
2. `binance_usdm_trade_flow_1h` publishes total and taker-buy base/quote volume plus exact derived
   fields:
   - `taker_sell_volume = volume - taker_buy_volume`;
   - `taker_sell_quote_volume = quote_volume - taker_buy_quote_volume`;
   - `volume_imbalance = taker_buy_volume - taker_sell_volume`; and
   - `quote_volume_imbalance = taker_buy_quote_volume - taker_sell_quote_volume`.

The derivations use scaled-integer arithmetic or an equivalently context-independent exact method.
They are not floats. Volume is Binance-published base-asset volume; quote volume is
Binance-published quote-asset volume. Positive imbalance means more taker-buy than taker-sell
volume in the named unit. The source files are read once to produce the two separate products.

Every row uses native venue identity `BINANCE_USDM`. The venue symbol and native symbol remain the
published Binance symbol. The not-yet-created REF-001 canonical instrument/version identifiers stay
null with the accepted named reference-identity state; ticker-derived identifiers are forbidden.

Any repeated open timestamp fails, even if byte-identical, because the complete accepted corpus
contains no observed duplicate domain. Any daily/monthly economic overlap fails. Gaps produce typed
quality rows with inclusive missing-run start/end in epoch milliseconds, exact expected-grid count,
and a reason distinguishing within-object from between-object absence. A gap never creates a market
row.

## Frozen publication contract

The normalizer accepts only the generation-0 SQLite state, its content-addressed root, and two
caller-selected hidden output roots. It authenticates the database, accepted seal, exact completion
counts, accepted validation states, plan identity/family/symbol/period, sidecar checksum, content
path, byte size, and content SHA-256 before consuming a row. It performs no network access and
writes nothing to an authority input.

The two products have independent hidden roots and independent completion descriptors. Each root
uses ADR-0024 product/native-symbol/UTC-month content-addressed Parquet partitions plus one matching
content-addressed lineage document per partition. Lineage maps each partition-local raw-object
reference exactly once to source key, SHA-256, checksum authority, byte size, retrieval time, and
availability semantics. Each product also has its own 114-row content-addressed quality-gap Parquet,
gap lineage document, and completion descriptor.

The accepted schemas come only from
`cryptofactors.acquisition.binance_usdm_harmonic_sizing.final_product_schema`; writer settings and
schema identities use the accepted sizing authorities. Output is bounded, staged on the destination
filesystem, flushed, verified, content addressed, and published with atomic no-clobber. A matching
winner is rehashed and reused; a differing winner fails. A completion descriptor is the only
product-complete marker and pins the ordered partitions, lineages, quality artifact, source digest,
schema/writer/normalizer identities, and exact row equations. An interruption may leave hidden
verified artifacts but no visible dataset; replay must reprove and reuse them byte-identically.

Completion succeeds only if each product independently proves all of these exact full-corpus totals:

- 35,642 authenticated sources and 661,676,054 compressed source bytes;
- 22,633 Parquet partitions and 22,633 matching lineage documents;
- 16,033,509 physical rows and 16,033,509 product rows;
- zero duplicate, overlap, collapsed, or excluded rows; and
- 114 quality-gap rows representing exactly 8,003 missing hourly grid points.

## Sol High source authorization

Sr Dev — Codex Sol using High reasoning is authorized to author exactly these three paths:

- `src/cryptofactors/ingest/binance_usdm_klines.py`;
- `scripts/research/normalize_binance_usdm_klines.py`; and
- `tests/ingest/test_binance_usdm_klines.py`.

The source may import accepted public sizing and acquisition authorities but may not modify the
accepted open-interest normalizer, the generic BIN-001 parser, any acquisition source, any existing
test, or any package export unless a later review expressly authorizes it. The CLI takes explicit
`--generation0-state`, `--generation0-content-root`, `--bar-output-root`, and
`--trade-flow-output-root` arguments and prints only a deterministic concise result; it never
infers Git identity or accesses the network.

Sol authors production and test source. Tests must cover authority fail-closed behavior,
headed/headerless parsing, exact decimal/timestamp/economic rules, the four flow derivations,
daily/monthly identity and overlap, duplicate/conflict handling, within/cross-object gaps, typed
schemas and lineage, dual-product separation, content-addressed no-clobber publication, interruption
and byte-identical resume, completion reconciliation, unsafe ZIP/path rejection, and bounded
parser limits.

Under the targeted senior test exception, Sol may run exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact command/output. It performs no real-data
run, data mutation, integration, repository-record edit, Git operation, commit, push, acquisition,
network access, cleanup, catalog transaction, NautilusTrader work, experiment, backtest, model,
Harmonic Trader repository work, PAPER, LIVE, or next-ticket work. Hermes remains unauthorized
until the reviewer accepts the exact source/test drop.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/446_CEX002_HOURLY_KLINE_ARCHITECTURE_AND_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All implementation, data, runner, wrapper, and unrelated dirty paths remain unstaged and untouched.
