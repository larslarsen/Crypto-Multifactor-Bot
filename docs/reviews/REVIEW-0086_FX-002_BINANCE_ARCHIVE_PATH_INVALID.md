# REVIEW-0086 - FX-002 BINANCE ARCHIVE PATH INVALID

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** CHANGES_REQUIRED - MALFORMED ARCHIVE REQUESTS
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

The submission is not accepted. Every Binance archive URL omitted the required `/data/` path
component. Those 404 responses do not prove missing historical coverage.

Stablecoin-FX implementation remains unauthorized.

## Blocking Findings

1. Accepted repository evidence uses
   `https://data.binance.vision/data/spot/daily/klines/...`; the submitted rows use
   `https://data.binance.vision/spot/daily/klines/...`. The latter is a malformed namespace.
2. The report concludes that no archive objects exist from malformed-request 404s. Reviewer checks
   confirm corrected 2026-07-20 checksum URLs return 200 for both `USDTUSD` and `USDCUSD`.
3. A corrected 2022-05-01 `USDTUSD` checksum URL returns 404, which may validly fail depeg coverage,
   but that observed request is not the request registered in the repository.
4. No successful current archive object, provider `.CHECKSUM`, response headers, or bar schema was
   captured despite the explicit task requirement.
5. The report again substituted a different mechanical preflight command for the exact REVIEW-0084
   command.
6. The pytest section still omits the standard final summary line and instead asserts that pytest did
   not emit one. The required evidence remains absent.
7. Register/source rows still use `N/A`, although reasoned `NOT_APPLICABLE: ...` or `UNKNOWN: ...`
   sentinels were mandatory.

## Required Action

Execute `docs/reviews/FX-002_JR_BINANCE_ARCHIVE_PATH_CORRECTION_TASK.md`. This is a bounded correction,
not another broad audit.
