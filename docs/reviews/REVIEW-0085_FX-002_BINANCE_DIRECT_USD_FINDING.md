# REVIEW-0085 - FX-002 BINANCE DIRECT-USD FINDING

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** CHANGES_REQUIRED - DIRECT-USD CANDIDATE NOT AUDITED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

The recovered submission is not accepted. Its own Binance capture reports live `USDTUSD` and
`USDCUSD` spot instruments, but the report incorrectly classifies them as non-direct and secondary.
These symbols require a bounded historical/PIT audit before FX-002 can recommend `NONE`.

Stablecoin-FX implementation remains unauthorized.

## Blocking Findings

1. `USDTUSD` has base asset `USDT` and quote asset `USD`; `USDCUSD` has base asset `USDC` and quote
   asset `USD`. They are direct USD-per-stablecoin instruments, not stablecoin/stablecoin crosses.
   Reviewer spot checks of the submitted endpoint on 2026-07-21 returned both symbols as `TRADING`.
2. The report acknowledges those symbols but sets `rate_direction: N/A` and `Direct USD anchor: no`.
   The correct observed direction is USD per USDT/USDC. The ticket's secondary-only rule applies to
   stablecoin cross-pairs, not a pair whose actual quote asset is fiat `USD`.
3. No Binance bar/trade archive, listing history, 2022 depeg coverage, availability semantics,
   revision behavior, or archive licensing was tested. Therefore neither PRIMARY nor NONE is proven.
4. The required matrix schema was not used. `rate_direction`, `source_status`, and `recommendation`
   remain absent.
5. The prescribed mechanical preflight was replaced by a different command.
6. The pytest output omits its literal final summary line with pass count, warning count, and duration.
7. Kraken lineage is internally inconsistent: the report/register use SHA-256 `6ea3d7...`, while
   `research/fx_002/sources/kraken.md` records `1eed62...` for the same path, size, and retrieval time.
8. The Binance source note marks its supposedly exact retrieval timestamp `(approx)`, and several
   register fields use `N/A` instead of the required reasoned sentinel.
9. Coin Metrics queried `/catalog/assets`, not the required asset-metric catalog, so its metric
   availability conclusion remains unsupported.

## Required Action

Execute `docs/reviews/FX-002_JR_BINANCE_DIRECT_USD_AUDIT_TASK.md`. Do not begin implementation or
another ticket.
