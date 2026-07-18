# 11 — Evidence Collection Log (primary-source staging)

**Sprint:** 003 (evidence collection pass)
**Date:** 2026-07-18
**Cutoff:** 2026-07-18

## Purpose

Mechanical collection of primary-source evidence into an external staging area so the
senior audit tooling and research review have clean inputs. No parsing, pagination,
bar-reconstruction, checksum, or storage-estimation code was written for this pass. No
source decisions were changed; existing decisions in `01_SOURCE_DECISION_REGISTER.csv`
stand. Interpretation awaits senior tooling and the research lead's decisions.

## Staging area (outside the repository — not committed)

`/tmp/crypto_source_audit/` organized by provider:
`binance/ kraken/ okx/ bybit/ coin_metrics/ defillama/ token_unlocks/ reference_events/`

Manifest: `/tmp/crypto_source_audit/evidence_manifest.csv` (43 records, 16 columns).

## Evidence collected (by provider)

- **binance (12):** BTCUSDT spot aggTrades 2024-12-31 and 2025-01-01, spot klines 1m
  2025-01-01, USD-M perp aggTrades + perp trades 2025-01-01, funding monthly 2025-01, all
  four provider `.CHECKSUM` sidecars, the official replacement-checksum register
  (`updates/2022-10-04_aggregate_trade_updates.csv`), and the data-source README.
- **bybit (8):** BTCUSD inverse perp archive 2019-10-01, BTCUSDT linear perp archive
  2020-03-25, linear + inverse instrument metadata, funding history page 1 (raw cursor
  `[]` preserved), instruments-info pages 1 and 2 (cursor pagination), and a delivered
  forward contract `BTCUSDU26` (deliveryTime > 0).
- **coin_metrics (7):** full catalog (5991 assets), btc `SplyCur` (issued supply) +
  `AdrActCnt` (activity) timeseries, bonk `SplyCur` (error — limited/unsupported),
  `SplyIssued` (error — unsupported metric), catalog rate-limit response headers, docs.
- **defillama (6):** emissions API response (HTTP 402 — paid), current adapters repo
  `DefiLlama/defillama-adapters` at commit `79df37a51d8f26bf4903b04504980e647307c2fc`, and
  four representative adapters (unlockd, unlockd-v2, optimism, helper addresses).
- **okx (4):** historical L2 order-book docs, live funding-history sample, live trades
  sample (live kept separate from historical), historical-host record.
- **kraken (3):** three documentation URLs, all returned HTTP 404 from this environment
  (Kraken docs/site restructured).
- **token_unlocks (3):** Tokenomist ARB (TLS-unreachable), Messari ARB (requires account),
  unlocks.app documentation page.

## Sources blocked / requiring credentials or payment

- **Kraken historical bulk files** — `data.kraken.com` / `download.kraken.com` do not
  resolve (DNS) from this environment; Kraken docs URLs 404. `ACCESS_BLOCKED` / `NOT_FOUND`.
- **OKX historical files** — `bulk-data-download.okx.com` does not resolve (DNS).
  `ACCESS_BLOCKED`.
- **Tokenomist** — TLS `TLSV1_UNRECOGNIZED_NAME` from this environment. `ACCESS_BLOCKED`.
- **Messari** — API requires a key (404/429 without). `REQUIRES_ACCOUNT`.
- **DefiLlama emissions API** — now returns HTTP 402 (paid plan); free unlock bridge gone.
  `REQUIRES_PAYMENT`.

## Notes

- No market-data files were committed to the repository. Only this documentation-only log
  is added under `research/sprint_003/`.
- The Binance historical files, Bybit archives, Coin Metrics responses, and DefiLlama
  adapter files remain in the external staging area for senior tooling and research review.
- Interpretation (timestamp precision, point-in-time classification, source decisions) is
  deferred to senior tooling and the research lead. Existing Sprint 003 decisions are
  unchanged by this log.
