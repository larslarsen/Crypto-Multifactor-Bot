# 09 — Open Questions (CORRECTION PASS)

**Sprint:** 003 (correction)
**Research cutoff:** 2026-07-18

## Resolved in this correction
1. ~~Binance bulk path 404~~ → RESOLVED: wrong host (`data-api` vs `data.binance.vision`).
   Real archive objects acquired; provider CHECKSUM verified; replacement register audited.
2. ~~Coin Metrics SplyIssued issued supply~~ → RESOLVED: metric is `SplyCur`; timeseries is
   a flat `data` array; `SplyCur` ≠ circulating float (excluded supply = `SplyExNtv`).
3. ~~Bybit pagination / delivered contract~~ → RESOLVED: instruments-info cursor returns
   distinct pages; `BTCUSDU26` InverseFutures has `deliveryTime`>0 (real delivery exemplar).
4. ~~DefiLlama adapter path~~ → RESOLVED (changed): old SDK `emissions/adapters` 404;
   emissions API now **HTTP 402** (paid). Free unlock bridge gone.

## Remaining open questions
1. **Kraken bulk host** — `data.kraken.com` does not resolve from this environment. Is it a
   host/network restriction or a renamed endpoint? Acquire from a resolvable host and verify
   ZIP/CSV layout, no-trade OHLCVT omission, reconstructed-vs-provider bars. (SRC-003)
2. **OKX historical host** — `bulk-data-download.okx.com` does not resolve. Locate the
   current historical-file host; verify layout/compression/schema/coverage. (SRC-004)
3. **Tokenomist reachability + vintage preservation** — TLS fails here; even if reachable,
   can it reproduce historical unlock-schedule vintages? Binding gap for DIL-01. (SRC-008)
4. **DefiLlama paid emissions** — is a paid plan the only free-bridge replacement, or does a
   public adapter repo remain? Pin exact commit + inspect ≥5 adapters. (SRC-007b)
5. **On-chain vesting (DIL-01/NET-01)** — not queried (needs keys). Publication-time vs
   block-time lag and revision/backfill behavior unbounded. (SRC-010)
6. **Bybit funding history cap** — capped at most-recent ≤100 events; true multi-page
   historical funding requires another route (or exchange data request). Cursor pagination
   demonstrated only on instruments-info.
7. **Micro-cap coverage** — `bonk`/`pepe` absent from Coin Metrics Community catalog; limited
   coverage likely Pro-only. Affects U100 representativeness for tiny assets.
8. **Kraken no-trade intervals** — omission vs zero-fill unverified (blocked by Q1).
9. **OKX/Bybit funding formula changes** — exact effective dates of past `formulaType`/
   interval changes not pulled; capture per-timestamp.
10. **Commercial procurement** — Coin Metrics Pro/Atlas, Kaiko, Amberdata, Messari Pro,
    DefiLlama paid: point-in-time / revision guarantees vs free tiers. (SRC-006b/SRC-007b/
    SRC-009/SRC-010)
