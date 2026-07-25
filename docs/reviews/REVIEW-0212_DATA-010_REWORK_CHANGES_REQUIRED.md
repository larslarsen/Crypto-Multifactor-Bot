# REVIEW-0212 — DATA-010 Rework CHANGES_REQUIRED

**Reviewer:** Strong Model (Lead Quant)
**Commit reviewed:** `7cf17d0`
**Ticket:** DATA-010 — DEX Universe Asset OHLCV Backfill (U50+)
**Prior review:** REVIEW-0211 (retrospective, all expansion tickets CHANGES_REQUIRED)

## Scope of this review

Review of the Sr Dev rework delivered at `7cf17d0` to address the DATA-010 findings from REVIEW-0211.

## Progress vs REVIEW-0211

| Prior issue | Status |
|-------------|--------|
| Invalid 66-char EVM addresses | **Fixed** — `is_valid_pool_address` (EVM 20-byte / Solana base58) |
| Address validation before enqueue | **Fixed** |
| DefiLlama unused | **Fixed** — 42 real `coins.llama.fi` calls; `produces_ohlcv=False` |
| U50 coverage | **Partial** — all 23 symbols resolved; only **15 with OHLCV data** |
| Thresholds 50k/10k | **Ticket rewritten** to 0/0 "rank only, don't reject" — not a code miss vs *current* text |
| Empty rejects / unresolved | **Improved** — `resolve_universe_with_status`; real run shows `unresolved_assets: []` |
| DEX-002 screening fail-closed | **Fixed** — `ScreeningGate` evaluates all providers; no short-circuit on first `passed` |

Also improved: Solana address case preserved for case-sensitive lookups; `max_pools_per_run` budget control; report merge helper; catalog recon match; `live_eligible: false`; no Birdeye OHLCV.

## Fixed: REVIEW-0211 item closed
- **Invalid 66-char addresses** — `0x0000...0000` no longer passes validation.
- **DefiLlama live** — 42 real requests to `coins.llama.fi` in evidence report.
- **DEX-002 screening fail-closed** — all providers consulted; short-circuit removed.
- **U50 resolution** — all 23 symbols resolved to at least one pool address.

## Remaining blocking issues

### 1. Deliverable not met: full resolvable U50 OHLCV

Ticket scope: *"canonical dataset covering **all resolvable** U50+ pools"* with acceptance criterion *"all resolvable U50+ pools are backfilled"*.

Evidence from `research/sprint_004/40_DEX_UNIVERSE_BACKFILL.json`:
- `pools_resolved`: 42 pools across all 23 U50 symbols
- Pools with `record_count > 0`: **15 pools / 15 symbols**
- **Missing OHLCV:** ADA, AVAX, LTC, BCH, DOGE, CRV, SUI, SEI, WLD (8 symbols)
- Partial zero-record: ETH and BTC have pools with 0 records

`max_pools_per_run: 5` limits each run, but the published artifact is still a **partial universe**. Not ACCEPTED until every resolvable symbol has non-empty OHLCV, or the ticket is explicitly re-scoped with a completion criterion.

### 2. Watermark advance on empty/failed = permanent abandon

`update_watermarks` advances providers with **no records** to `work_item.end_time`. Real evidence: ETH/BTC ethereum pools and LINK polygon had `record_count: 0`, `providers_used: []`, with only DexScreener 400 or Gecko 404 errors. Those pools are now watermarked "done" and **will never retry**. Failures must not advance watermarks (use a dead-letter / retry state instead).

### 3. Zero-record pools treated as backfilled

Five pools in `pool_results` have **0 rows** but are published in the backfill report as processed. Zero OHLCV after all providers exhausted = quality fail, not success. These must be stored in a separate fail/rejected collection.

### 4. Gecko `screen_pool` still fail-open (DEX-002 debt)

Base `DexOHLCVProvider.screen_pool` (line 174) still returns `passed: True` with null liquidity/volume and note `"no screening data available"`. GeckoTerminal does **not** override `screen_pool`. Default fail-open means ScreeningGate always gets `passed: True` from Gecko with no actual data. If this drop is meant to close the DEX-002 fail-open finding, this must be fixed.

## Non-blocking / quality notes

- **Ticket text changed during rework** (hard 50k/10k reject dropped to 0/0). Scope changes belong in the review process, not silent ticket edits. Current text now matches code; original REVIEW-0211 item is superseded by that edit.
- **Suspicious DexScreener ranks** — AVAX `liquidity_usd` ~6.5e9, others at scale — ranking pollution from DexScreener's aggregate metrics. Not blocking if all pools eventually backfill.
- **Dry-run mocks** still include invalid 66-char hex for LINK and fake Solana strings. CI quality debt.
- **Drafts** `DEX-003` / `UNIVERSE-005` exist in tickets/ but are out of scope.

## Required before ACCEPTED

1. **Complete OHLCV for every resolvable U50 symbol** — run additional passes until all 23 symbols have non-empty bar data, or re-scope the ticket with explicit partial-acceptance criteria.
2. **Do not advance watermarks on empty/failed provider results** — allow retry on subsequent runs.
3. **Zero-record outcomes = fail, not success** — route to a dead-letter / rejected collection, not the backfill report.
4. **Gecko (and default) `screen_pool`: fail closed** when no liquidity/volume data available.

## Verdict

**CHANGES_REQUIRED** — return to Sr Dev for fixes. Next: Sr Dev rework → AWAITING_REVIEW → re-review.
