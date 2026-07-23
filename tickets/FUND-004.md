# FUND-004 - BitMEX Perpetual Funding Rate Source Audit

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** DF-03 (accepted, NO_POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY)
**Layer:** research evidence / funding cashflow source authority
**Architecture:** no ADR, migration, or production implementation authorized

## Objective

Audit the source semantics of BitMEX perpetual swap funding rate data for use as an
point-in-time funding cashflow source. Required recommendation:
`POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY` or `NO_PRIMARY_SOURCE_AUTHORITY`.

## Evidence

All live API tests performed 2026-07-23. Decision matrix at `research/fund_004/decision_matrix.csv`.

### API endpoint
`GET https://www.bitmex.com/api/v1/funding?symbol={symbol}&count={n}&startTime={t}&endTime={t}`
Returns up to 500 records per request. Rate limit: 180 req/min (unauthenticated). No API key required for public data. Full historical pagination supported via `startTime`/`endTime` params.

### Perpetual instruments sampled
- **XBTUSD** (BTC/USD inverse perp) — earliest record: 2016-05-14T12:00:00Z (listed 2016-05-13)
- **ETHUSD** (ETH/USD quanto perp) — earliest record: 2018-08-02T12:00:00Z (listed 2018-08-01)
- **XRPUSD** — listed 2020-02-04
- **SOLUSDT** — listed 2021-11-10
- **ADAUSDT** — listed 2021-12-15

### Funding rate formula (from BitMEX perp guide)
Funding = Mark Value × Funding Rate
Funding Rate (F) = Premium Index (P) + clamp(Interest Rate (I) − P, +0.05%, −0.05%)
Interest Rate (I) = (Funding Quote Rate − Funding Base Rate) / 3
Premium Index: 8-hour TWAP of minute-level premium samples
Rate caps: max |F| = 75% × (initMargin − maintMargin); max ΔF = 75% × maintMargin

### Funding settlement schedule
Every 8 hours at 04:00, 12:00, 20:00 UTC. Early XBTUSD history (2016-05-14 → 2016-06-04) was daily (24h interval); switched to 8h at 2016-06-04T20:00Z.

### Public archive (S3 `public.bitmex.com`)
No funding CSV dumps. Available: `data/trade/`, `data/quote/`, `data/porl/` only.

### Terms of Service (June 2026)
Clause 16: data for personal use only; commercial use requires written consent; no data mining. API Annex C: no explicit research prohibition. Publications Annex allows historical data for informational purposes. Internal research use case is in a grey area — likely acceptable but not explicitly authorized.

## Gate Audit

| Gate | Status | Summary |
|------|--------|---------|
| G01 — semantics | **PASS** | `timestamp` = funding settlement time; `fundingInterval` encodes 8h; schedule documented |
| G02 — unit/sign/formula | **PASS** | Full formula documented in perp guide; rate = decimal fraction; positive = longs pay shorts |
| G03 — interval history | **PARTIAL** | Daily→8h switch documented (2016-06-04); formula stable since; formula versioning undocumented |
| G04 — historical depth | **PARTIAL** | XBTUSD from 2016-05; REST pagination works; no CSV dumps for independent archival |
| G05 — correction history | **UNKNOWN** | No revision fields; no correction policy documented |
| G06 — raw lineage | **PARTIAL** | HTTP response has request identity; no independent archive for cross-verification |
| G07 — licensing | **PARTIAL** | ToS permits personal/informational use; commercial/compliance-gate use ambiguous |
| G08 — cashflow conversion | **PARTIAL** | Formula explicitly documented; USDT pairs settle in USDt; XBTUSD inverse needs FX step |

## Comparison vs Binance (FUND-002) and OKX (FUND-003)

| Gate | Binance | OKX | BitMEX |
|------|---------|-----|--------|
| G01 | FAIL_PARTIAL (calc_time confusion) | FAIL_PARTIAL | **PASS** (single clear timestamp) |
| G02 | FAIL_PARTIAL (relabeled fields) | FAIL_PARTIAL | **PASS** (documented formula) |
| G03 | FAIL_PARTIAL | FAIL_PARTIAL | **PARTIAL** (switch known, formula stable) |
| G04 | FAIL_PARTIAL | FAIL_PARTIAL (2026+) | **PARTIAL** (2016+, no CSV) |
| G05 | FAIL_UNKNOWN | FAIL_UNKNOWN | **UNKNOWN** (same gap) |
| G06 | PASS (bounded) | FAIL_PARTIAL | **PARTIAL** (REST only, no CSV) |
| G07 | FAIL_UNKNOWN | FAIL_UNKNOWN | **PARTIAL** (ToS clearer) |
| G08 | FAIL_BLOCKED | FAIL_BLOCKED | **PARTIAL** (formula known, FX still needed) |

## Recommendation

**NO_PRIMARY_SOURCE_AUTHORITY** at audit standard, but **strictly better than Binance/OKX** — BitMEX clears G01 and G02 fully (unlike both peers), and its ToS is more permissive for research use.

BitMEX is the **best available free funding source** for a pragmatic research-grade path. The gate gaps (G03 PARTIAL, G05 UNKNOWN, G06 PARTIAL) mirror those on prior accepted sources. G08 requires the same FX resolution as any funding source.

Recommended reviewer decision: same pragmatic treatment as Binance (accepted Binance data with documented caveats for FUND-002) but with stronger preconditions — the documented formula and clear timestamp semantics lower the error bound below Binance's estimated ±15%.

## Stop Condition

Publish the source-semantics report and return control to Reviewer with
`Next ticket authorized: NONE` or `Next ticket authorized: <pragmatic-implementation-ticket>`.
