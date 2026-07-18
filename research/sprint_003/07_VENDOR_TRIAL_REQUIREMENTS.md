# 07 — Vendor Trial Requirements

**Sprint:** 003
**Research cutoff:** 2026-07-18

Documents what must be confirmed (licensing, rate limits, access) before each conditional
or deferred source can be promoted. No commercial purchase was made this audit.

## Binance (SRC-001 / SRC-002)

- **Bulk zip (SRC-002):** confirm reachability from the data-acquisition host; if 404
  persists, fall back to REST pagination (SRC-001). Obtain and verify the provider
  replacement-checksum register (github `binance/binance-public-data`) to validate any
  re-pulled historical file.
- **REST:** public, no key for market data; respect weight limits (IP-based). Terms: market
  data is provided "as is"; redistribution of raw data requires review of Binance terms.
- **Action:** trial a multi-day REST backfill of one pair; confirm checksum handling.

## Kraken (SRC-004)

- Public REST; no key for OHLC/Trades. Verify bulk-file layout and no-trade candle
  omission by reconstructing bars from trades and diffing against provider candles.
- Terms: public data usable for research; confirm redistribution clause.

## OKX (SRC-005)

- Public REST (market/instruments/public). Record dated funding-formula and interval
  changes from OKX docs; capture `formulaType` per history row.
- Terms: review OKX API terms for research use; no key for public market data.

## Bybit (SRC-006)

- Public v5 market endpoints. Cursor pagination on funding history must be fully walked.
- Confirm linear vs inverse volume/turnover unit normalization before any cross-venue
  aggregation.
- Terms: review Bybit API terms.

## Coin Metrics (SRC-007)

- Community API v4 usable without a key for catalog + many timeseries (param-format
  sensitive: no `page_size`/`limit` on catalog; use defaults). For broad historical
  coverage or higher rate limits, a **Pro/Atlas** subscription is likely required — separate
  procurement decision (SRC-012 class).
- Critical: `SplyIssued` is issued supply, **not** circulating float. For `DIL-01`,
  circulating/float and unlock series need Pro or a complementary source.
- Terms: Community API has usage limits; confirm non-redistribution of derived datasets.

## DefiLlama (SRC-008 / SRC-009)

- Public APIs (api.llama.fi, stablecoins.llama.fi) and open-source SDK (MIT). Pin the SDK
  commit; verify adapter registry for token/chain mappings and recomputation behavior.
- Emissions adapters are the bridge to unlock/emission data; trial a few protocols and
  confirm the unlocked-amount methodology and revision cadence.

## Tokenomist (SRC-010 — DEFERRED)

- **Blocker:** TLS to `api.tokenomist.com` failed in this environment
  (`TLSV1_UNRECOGNIZED_NAME`). Before any promotion: (a) confirm reachability from the data
  host; (b) review terms (some unlock data is licensed); (c) determine whether historical
  schedule vintages are preserved (current charts may not retain old information sets);
  (d) cross-check against on-chain vesting contracts and project/governance docs.

## Messari (SRC-011 — CONDITIONAL)

- Public endpoints returned 404/429 without a key. A trial/key is required for market data
  and volume. Use only as Phase-2 crosscheck; terms restrict redistribution.

## On-chain (SRC-012 — CONDITIONAL)

- Not queried this audit. Required for `NET-01` (active/new addresses, fees, TVL) and
  `DIL-01` (on-chain vesting, supply). Needs API keys (Etherscan/Dune/Glassnode) and rate
  planning. Separate procurement decision; pin provider versions.

## Cross-cutting

- No credentials were stored. Any future key must live in `~/cryptofactors_data` or a
  secrets manager, never in the repo (`.gitignore` already excludes `.env`/`*.key`).
- Redistribution of raw exchange data must not be committed without confirming applicable
  terms; registries, hashes, and audit notes are publishable.
