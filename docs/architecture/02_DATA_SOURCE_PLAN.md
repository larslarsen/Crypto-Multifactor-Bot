# 02 — Free/Low-Cost Data Source Plan

## 1. Policy

Prefer data sources in this order:

1. official downloadable exchange archives;
2. official public REST/WebSocket APIs;
3. official/open community datasets;
4. third-party aggregators only for discovery, cross-checks, or variables unavailable elsewhere.

Every source must have a provenance record, timestamp contract, rate-limit policy, and redistribution classification.

## 2. Phase 1 source stack

### Binance public archive — historical backfill and repair

Use official daily/monthly public files for spot and futures bars/trades where relevant. Preserve source checksums. Source schemas include quote volume and trade count, and Binance documents a spot timestamp-unit change to microseconds from 2025-01-01; the adapter must version this behavior.

Use cases:

- primary historical 5-minute/1-hour bars where available;
- selected futures bars and trades;
- cross-source reference, not automatic execution approval.

Risks:

- archive gaps and corrections exist;
- timestamp-unit transition;
- venue availability/jurisdiction is separate from data availability.

### Kraken downloadable OHLCVT — independent spot venue

Kraken provides complete and quarterly incremental OHLCVT downloads across several intervals. Missing intervals may mean no trade occurred, so the normalizer must represent no-trade intervals explicitly rather than assuming source failure.

Use cases:

- independent venue prices/volume;
- cross-source checks;
- historically reconstructable spot universe evidence.

Do not use the REST OHLC endpoint for historical backfill because it returns only the most recent 720 entries.

### OKX historical downloads and public API — derivatives and robustness

Official historical downloads include tick trades from 2021-09, candlesticks from 2023-07, funding from 2022-03, and high-resolution L2 from 2023-03.

Use cases:

- funding history and derivative robustness;
- candlestick/trade backfill;
- limited cost calibration samples.

Do **not** ingest the full L2 archive in Phase 1. It is storage/compute intensive and unnecessary for weekly factors. If cost calibration needs it, sample a bounded asset/date set.

### Bybit public API — incremental perps/funding and second-venue checks

The public kline API returns up to 1,000 rows per request; funding history up to 200. The collector must paginate backward/forward deterministically and store each response.

Use cases:

- funding and mark/index incremental history;
- true second-venue replication;
- prospective venue metadata snapshots.

### Existing local legacy observations

Treat local files as a source named `legacy_local`, not as canonical truth.

- Register exact bytes and hashes before conversion.
- Record the original path and inferred provenance.
- Do not modify or rename source files during audit.
- Compare against official archives where possible.
- Quarantine ambiguous symbol/timestamp files.

## 3. Market cap and size

Do not make historical market capitalization a Phase 1 dependency.

The free CoinGecko Demo historical endpoints currently restrict historical data to the previous 365 days. That is inadequate for a long point-in-time size-factor study and cannot reconstruct provider vintages. CoinGecko may still be used for:

- current ID/contract mapping assistance;
- prospective daily snapshots stored from the collection date onward;
- non-authoritative cross-checks.

The `SIZE-01` factor remains blocked until a historical point-in-time supply/market-cap source is audited or enough prospective history accumulates.

## 4. On-chain/network factors

Phase 2 candidates:

### Coin Metrics Community

Use only metrics confirmed available under the Community API/archive and record metric coverage, methodology, revision behavior, and license. Do not assume every desired metric/asset is free.

### DefiLlama free API

The free API exposes historical TVL and selected protocol/chain/fees/volume series without authentication. These are useful for protocol-level Phase 2 hypotheses, but mappings, methodology changes, publication lag, double counting, and historical revisions must be audited.

Neither source is part of U50 eligibility or the Phase 1 baseline.

## 5. Instrument/listing history

There is no assumption that a free provider offers a perfect historical security master.

Build it from evidence with confidence levels:

1. `OFFICIAL_EVENT`: dated exchange announcement or contract metadata.
2. `OFFICIAL_ARCHIVE`: first/last official observations plus active status.
3. `MULTI_SOURCE_CONFIRMED`: corroborated by multiple official sources.
4. `INFERRED`: first/last observed data without announcement.
5. `AMBIGUOUS`: unresolved mapping; excluded from primary universe.

Collect and version instrument metadata daily from now onward. This creates a clean prospective history even if older listing events require manual reconstruction.

## 6. Cost data

### Fees

- Snapshot public fee schedules and store effective/known times.
- When historical fees cannot be reconstructed, use a conservative fixed schedule and label it `ASSUMED_CONSERVATIVE`.

### Spreads

- Collect top-of-book snapshots prospectively at/around decision and rebalance times.
- For historical baseline, use robust bar-based spread estimators or conservative liquidity tiers, clearly labeled as estimates.

### Impact

- Use a simple participation/square-root sensitivity model calibrated only on approved observations.
- Report 0.5x/1x/2x cost scenarios.
- Do not download full-market L2 history until the baseline strategy demonstrates enough gross edge to justify refinement.

### Funding

Store each historical funding event and book the actual cash flow according to the venue interval/sign convention. A funding signal without funding cash-flow accounting is invalid.

## 7. Source roles

A source has one or more declared roles:

- `BACKFILL_PRIMARY`
- `INCREMENTAL_PRIMARY`
- `REFERENCE_METADATA`
- `CROSSCHECK`
- `ROBUSTNESS_ONLY`
- `COST_CALIBRATION`
- `EXPLORATORY_PHASE2`

Research code requests a role, not an arbitrary provider. This prevents silently substituting a lower-quality source.

## 8. Initial recommendation

### Long-only baseline

- Official Binance/Kraken/OKX spot bars where available.
- U50 based on vetted quote-volume observations.
- Deterministic point-in-time execution route.
- Daily bars derived from audited lower-frequency data or independently checked against native daily bars.

### Market-neutral baseline

Add only after:

- point-in-time perpetual availability;
- funding sign/interval normalization;
- mark/index data;
- short execution route;
- conservative fee/cost model.

### Deferred

- full L2/order-book history;
- all-exchange tick data;
- DEX tokens;
- market-cap factor;
- broad on-chain factor zoo;
- event/information bars outside their dedicated replication experiment.

## 9. Official references checked for this architecture

- Binance public data: https://github.com/binance/binance-public-data
- Kraken downloadable OHLCVT: https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data
- Kraken REST OHLC limit: https://docs.kraken.com/api-reference/market-data/get-ohlc-data
- OKX historical data: https://www.okx.com/historical-data
- Bybit klines: https://bybit-exchange.github.io/docs/v5/market/kline
- Bybit funding: https://bybit-exchange.github.io/docs/v5/market/history-fund-rate
- CoinGecko Demo historical limits: https://docs.coingecko.com/demo/reference/coins-id-market-chart-range
- Coin Metrics Community: https://docs.coinmetrics.io/api/v4/
- DefiLlama API: https://api-docs.defillama.com/

## 10. Evidence-backed acceptance conditions (Sprint 003)

Decisions below are recorded from the Sprint 003 source-feasibility audit
(`research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md`). They refine the roles in
Section 7 with provider-specific acceptance, deferral, and mandatory conditions.

### Per-provider decisions

- **Binance:** `ACCEPT — BACKFILL_PRIMARY`.
- **Bybit:** `CONDITIONAL — CROSSCHECK` and incremental derivatives/funding.
- **Coin Metrics Community:** `CONDITIONAL — EXPLORATORY_PHASE2`.
- **OKX:** `DEFER` historical approval pending audited historical files.
- **Kraken:** `DEFER` pending successful bulk-file acquisition.
- **DefiLlama:** `CONDITIONAL — EXPLORATORY_PHASE2`; emissions access not established as free.
- **Tokenomist / Messari:** `DEFER` pending authorized access or vendor trial.
- **CoinGecko / CoinMarketCap:** discovery and cross-check only; not point-in-time authorities.
- **DIL-01:** remains deferred.

### Mandatory Binance conditions

- Preserve provider checksums for every acquired object.
- Retain corrected and superseded objects rather than overwriting them.
- Infer and record timestamp units **per object** (not global to the provider).
- Support **both millisecond and microsecond** archives. The spot aggTrades
  unit change to microseconds from 2025-01-01 is real and must be versioned.
- Never infer timestamp units from filename dates alone; the unit must be
  observed from the data (see `source_audit.infer_timestamp_unit`).

### Mandatory Bybit conditions

- Deterministic cursor pagination (seed request + returned cursor drive the
  next fetch; unknown cursor terminates). Raw pages must be reproducible offline.
- Retain raw pages exactly (response bytes, not just normalized rows).
- Preserve fractional-second timestamps exactly (Bybit trades carry Unix seconds
  with microsecond fractional precision; do not truncate to integer seconds).
- Maintain source-specific schema/version records for each endpoint and revision.

