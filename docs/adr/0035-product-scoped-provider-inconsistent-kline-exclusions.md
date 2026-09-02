# ADR 0035 - Product-Scoped Provider-Inconsistent Kline Exclusions

- **Status:** Accepted
- **Date:** 2026-09-02
- **Amends:** ADR-0024 section 2 and CEX-002 Review 446
- **Evidence:** `research/sprint_004/451_CEX002_RECORD450_REVIEW_AND_KLINE_QUALITY_CORRECTION.md`

## Context

Review 446 reported all 16,033,509 accepted hourly kline rows as economically clean. That
conclusion was wrong. Record 450's real conversion stopped on one authenticated Binance row whose
taker-buy base volume exceeds its total base volume. A new read-only scan of all 35,642 selected
kline ZIPs found that the stopping row is part of a small, fully bounded provider-data defect:

- 40 rows have total base/quote volumes whose implied average price lies outside the row's own
  low/high range;
- 29 rows have the corresponding taker-buy inconsistency;
- two rows are in both sets, so the union is 67 rows;
- one of the 67 also has taker-buy base volume greater than total base volume; and
- the 67 rows affect 43 symbols, 57 symbol/month partitions, and five exact UTC hours in September
  and November 2023.

All objects and provider checksums remain authentic. Authentication proves which bytes Binance
published; it does not make an internally impossible economic row valid. For the first stopping
row, Binance's separately checksummed daily ZIP contains the same values as its selected monthly
ZIP, so swapping archive packaging would preserve the defect rather than repair it.

The final bar and trade-flow schemas currently require non-null volume fields. Making those fields
nullable would change the accepted product schemas and burden every consumer with partial-row
semantics. Publishing the impossible values would knowingly contaminate research. Dropping every
affected source row from both products would instead discard 27 price-bar rows whose complete bar
field set remains internally valid because only fields used by trade flow are defective.

## Decision

### 1. Validate volume pairs by an exact within-row identity

Let `low`, `high`, `volume`, and `quote_volume` be exact accepted decimals. A total-volume pair is
valid exactly when:

```text
(volume == 0 and quote_volume == 0)
or
(volume > 0 and low * volume <= quote_volume <= high * volume)
```

The taker-buy pair uses the same rule with `taker_buy_volume` and
`taker_buy_quote_volume`. This follows directly from the source definitions: quote volume divided
by base volume is a volume-weighted trade price, and every trade contributing to the candle must
lie within that candle's low/high range. Comparisons and products use the accepted exact scaled
decimal implementation; binary floats, tolerance bands, rounding, and inferred repairs are
forbidden.

The trade-flow row additionally requires taker-buy base volume no greater than total base volume
and taker-buy quote volume no greater than total quote volume. Existing timestamp, period, OHLC,
nonnegative, count, ZIP, authority, duplicate, and overlap rules remain unchanged. Violations of
those other rules still fail the run; this ADR creates no generic skip-on-error path.

### 2. Exclusion is product scoped

An authenticated raw row is projected independently into each required product:

- `binance_usdm_bar_1h` excludes the row only when its total-volume pair is inconsistent, because
  both total-volume fields are required and non-null in that product. Exactly 40 rows are excluded.
- `binance_usdm_trade_flow_1h` excludes the row when either volume pair is inconsistent or either
  taker-buy value exceeds its corresponding total. Exactly 67 rows are excluded.

The 27 rows with a valid total-volume pair and an invalid taker-buy pair remain valid bar rows.
No excluded product row is partially populated, changed, imputed, clamped, divided, or replaced.
The immutable raw ZIP and all original tokens remain unchanged and addressable through lineage.

### 3. Every exclusion is a typed product gap

Each excluded product hour produces one quality-gap row using the accepted quality schema:

- `missing_run_start_ms == missing_run_end_ms == open_time`;
- `expected_grid_count == 1`;
- `gap_kind == provider_invalid_required_fields`; and
- a fixed reason distinguishing total-volume inconsistency from trade-flow required-volume
  inconsistency.

The quality-gap lineage must bind every exclusion to product, native symbol, UTC month, source
key, source SHA-256, zero-based source data-row ordinal, open time, and the exact failed invariant
flags. It must not copy a corrected value because none is authoritative.

The original source-absence gaps remain unchanged. The exact full-corpus outcomes are therefore:

| product | physical rows | excluded rows | product rows | gap rows | unavailable hours |
|---|---:|---:|---:|---:|---:|
| `binance_usdm_bar_1h` | 16,033,509 | 40 | 16,033,469 | 154 | 8,043 |
| `binance_usdm_trade_flow_1h` | 16,033,509 | 67 | 16,033,442 | 181 | 8,070 |

Both products retain 35,642 authenticated sources, 661,676,054 compressed source bytes, and
22,633 symbol/month partitions. The prior 114 source-absence gap rows and 8,003 absent hours are
included in the table. No affected row adjoins a prior gap or another affected row for the same
symbol, so each exclusion adds exactly one gap row and one unavailable hour.

### 4. Completion and resume remain immutable and no-clobber

Completion descriptors advance to a new schema version and record the product-specific physical,
excluded, and product-row equation. Gap-lineage documents record the exclusion count and canonical
exclusion identity. A completion descriptor may reference only partitions produced or re-proved
under this corrected normalizer identity.

Previously published hidden content-addressed artifacts remain untouched. A corrected resume may
reuse byte-identical unaffected Parquets, publish corrected affected Parquets and new lineage
documents beside old unreferenced artifacts, and expose only the ordered set named by the new
completion descriptor. No cleanup or output-root deletion is required or authorized.

### 5. No acquisition or alternate-source substitution

Gate 2 and generation 0 remain accepted. This correction downloads nothing, changes no raw
authority, and does not substitute overlapping daily/monthly packaging. The provider-inconsistent
rows remain honest source-quality gaps. A future separately reviewed authoritative source could
supersede such gaps, but no value may be manufactured from adjacent candles, quote/base division,
or another market-data vendor in this ticket.

### 6. Existing capacity bounds remain conservative

Neither product schema nor partition count grows, and both product row counts decrease slightly.
The accepted pre-run storage bound therefore remains conservative. Record 450's capacity values
were default `df` 1-KiB block counts mislabeled as bytes: 41,509,740 KiB is 42,505,973,760 bytes,
and 37,658,760 KiB is 38,562,570,240 bytes. The corrected values were above the protected
33,566,545,257-byte floor; there was no 38-megabyte capacity emergency.

## Consequences

- Review 446's zero-corrupt-row statement and its product-row/gap totals are superseded.
- The accepted raw corpus, product schemas, publisher, and Gate-2 decision remain unchanged.
- Research receives every product-valid observation while impossible required values never enter
  a product.
- Consumers see explicit one-hour gaps rather than silent row loss, invented values, or nullable
  partial rows.
- A bounded normalizer/test correction and one reviewed resume are still required before either
  hourly product can be accepted.
