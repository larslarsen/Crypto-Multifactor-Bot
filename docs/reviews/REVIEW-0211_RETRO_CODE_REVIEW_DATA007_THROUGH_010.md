# REVIEW-0211 — Retrospective Code Review (DATA-007 → DATA-010 chain)

**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  
**Context:** Jr had been accepting tickets without code review. Reviewer inspected each ticket **backwards** from DATA-010 until a clean acceptance.

---

## DATA-010 — DEX Universe OHLCV Backfill

**Verdict: CHANGES_REQUIRED** (already filed)

| # | Issue |
|---|--------|
| 1 | Incomplete U50: 9/23 symbols; multi-pool on few assets |
| 2 | Invalid 66-char “addresses” (not 20-byte EVM); DexScreener 400s |
| 3 | Thresholds 5k/1k vs ticket 50k/10k |
| 4 | `rejected_pools: []` — unresolved assets not recorded |
| 5 | DefiLlama 0 requests |

---

## DATA-009 — BitMEX Full Backfill

**Verdict: CHANGES_REQUIRED**

### What works
- 45 active perps, 189,570 rows, XBTUSD from 2016-05-14, catalog recon match
- Discovery via `/instrument/active`, FFWCSX filter, 120 req/min, watermarks, tests
- `live_eligible: false`, new dataset type `bitmex_funding_full`

### Blocking / material issues

1. **Active-only universe ≠ “all symbols with funding history”**  
   Ticket: backfill every symbol with funding history.  
   Impl: `fetch_perp_symbols(state="Open")` on `/instrument/active` only.  
   Delisted/settled perps with historical funding are omitted (survivorship gap on funding).

2. **Incremental re-run publishes delta-only dataset**  
   Watermark resume fetches only new rows, then **publishes a new canonical dataset containing only that delta**, not a merge with prior full history. First real run is full (OK). Daily re-run would replace “latest” with a thin slice — broken incremental publish contract.

3. **Watermark save can drop keys**  
   `save_watermarks` writes only `new_watermarks` from the current run. Symbols that error mid-run or return empty lose prior watermarks on overwrite.

### Non-blocking
- Coverage starts 2016-05-14 (first XBTUSD print) vs ticket 2016-05-13 — fine
- Dummy `config_sha256="a"*64` — pattern debt

---

## UNIVERSE-004 — Birdeye Listings → Screen → Queue

**Verdict: ACCEPTED (with caveats)**

### What works
- Birdeye **listings only** (`/defi/v2/tokens/new_listing`); no OHLCV endpoints
- ScreeningConfig versioned; 60 listed → 14 screened → 46 rejected with reasons
- `ohlcv_request_queue` + as-of membership; death rule documented (7d liq+vol)
- `live_eligible: false`

### Caveats (not blocking for this ticket)
- Death rule not exercised in real run (no DEX-002 stats on new listings) — expected first pass
- Queue holds **token** addresses; DEX-002 wants **pool** addresses — consumer must resolve (DATA-010 path)
- Many queue reasons show `volume_24h=n/a` (liquidity-only screen in practice)

---

## DEX-002 — Multi-Provider DEX OHLCV Fan-Out

**Verdict: CHANGES_REQUIRED**

### What works
- Provider interface, token buckets, sharded watermarks, merge with provenance
- Catalog pin match; 357 records on 2 Arbitrum pools; no Birdeye; no LIVE
- Gecko primary path works for controlled window

### Blocking

1. **Fail-open screening (violates “fail closed”)**  
   Base `DexOHLCVProvider.screen_pool` returns `passed: True` with  
   `note: "no screening data available"`.  
   Real report: both pools screened with `liquidity_usd: null`, `volume_24h_usd: null`, `passed: True`.  
   Ticket hard rule: *Fail closed on quality; no silent gap fill.*

2. **ScreeningGate short-circuits on first `passed`**  
   Gecko (default fail-open) runs first → always enqueues without real liq/vol check.

### Non-blocking
- Only Gecko filled OHLCV; DexScreener/DefiLlama unused in that run (acceptable if documented)
- Demo used 2 stablecoin pools only (ticket allowed controlled first window)

---

## DATA-008 — Binance Universe Expansion

**Verdict: CHANGES_REQUIRED**

### What works
- 23→52 symbols, 70,325 bars, catalog recon, watermarks, 0 rate-limit incidents
- Volume prioritization scaffolding, instrument allocator, expand script

### Blocking / material

1. **Weak / wrong symbol screen for research universe**  
   Added set includes stable-like and non-core pairs: `EURUSDT`, `USD1USDT`, `RLUSDUSDT`, `UUSDT`, gold `PAXGUSDT`/`XAUTUSDT`, microcaps with **&lt;50 days** history (`AEROUSDT` 8d, `REUSDT` 37d, etc.).  
   Ticket intent: screen-prioritized **trading** expansion, not any high-24h-volume ticker.

2. **Leveraged-token filter is substring-broken**  
   `any(suffix in symbol for suffix in ("UP","DOWN","BEAR","BULL"))` matches interior substrings (e.g. `"UP" in "TRUMPUSDT"`). Either over-excludes or was ineffective depending on path — not a correct `endswith`/tokenized check.

3. **Stablecoin base allowlist incomplete**  
   Only USDC/BUSD/TUSD/FDUSD/DAI excluded; EUR/USD1/RLUSD/etc. pass.

### Non-blocking
- Majors deepen to 2017 optional — not clearly done; 2020 floor retained

---

## DATA-007 — Free Source Rate-Limit Probe

**Verdict: ACCEPTED**

### Meets ticket
- 6 sources probed with roles, rate limits, history depth, screening fields
- `birdeye_ohlcv_forbidden: true` on Birdeye row; listings-only endpoint
- `recommended_fanout` + `estimated_daily_capacity` + `live_eligible: false`
- Mocked CI tests; dry-run default; live matrix artifact present

### Notes
- Birdeye live row `fail` without env key in artifact — acceptable for probe matrix
- Capacity numbers are estimates (documented), not measured load tests

**First ticket in reverse walk that needs no code changes.**

---

## Summary table

| Ticket | Prior status | Review verdict |
|--------|--------------|----------------|
| DATA-010 | AWAITING / READY rework | **CHANGES_REQUIRED** |
| DATA-009 | ACCEPTED (improper) | **CHANGES_REQUIRED** |
| UNIVERSE-004 | ACCEPTED (improper) | **ACCEPTED** (caveats) |
| DEX-002 | ACCEPTED (improper) | **CHANGES_REQUIRED** |
| DATA-008 | ACCEPTED (improper) | **CHANGES_REQUIRED** |
| DATA-007 | ACCEPTED (improper) | **ACCEPTED** (clean) |

## Process rule restated

Jr Dev must **not** set ACCEPTED. Sr delivers → **AWAITING_REVIEW** → Reviewer (strong model) accepts/rejects → Jr records decision + git only after review.
