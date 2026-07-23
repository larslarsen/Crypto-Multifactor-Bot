# DATA-005 — Quality-Cleared Bars for Frozen TSMOM Candidate Path

**Priority:** P0  
**Status:** READY  
**Dependencies:** PAPER-008 (ACCEPTED), DATA-004, BAR-001  
**Layer:** market bars / catalog quality / acquisition  
**Architecture:** fix or extend BAR-001 path so frozen-candidate research can cite **non-REJECTED** `market_bars`. **No LIVE. No lookback/skip changes.**

## Objective

PAPER-008 freezes `tsmom_14_3` with gate-true paper on DATA-004 bars that remain **`quality_status: REJECTED`** (`unsupported_daily_interval` for native 1d). LIVE policy cannot honestly proceed on REJECTED quality. Produce a **quality-cleared** (PASS or PASS_WITH_WARNINGS) canonical bar dataset covering the same universe and ≥ the PAPER-008 window.

## Scope

1. **Choose one approach (document which):**
   - **A.** Extend BAR-001 / publish path to accept **native daily** sources under an explicit policy and mark PASS when checks succeed; or
   - **B.** Re-backfill **sub-day** (e.g. 1h) klines and promote proper daily (and/or keep intraday) so quality is PASS without native-1d quarantine.
2. **Universe / span:** Same 10 paper names; span at least 2024-01-01 → 2026-07-23 (or prove venue max).
3. **Artifact** `research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json`:
   - approach A/B, old vs new `dataset_id`, `quality_status`, bar_start/end, per-symbol counts
   - `live_eligible: false`
   - note: does **not** re-authorize LIVE; frozen config unchanged
4. **Optional smoke:** one factor/as-of read on new dataset (no full paper re-tune).
5. **Do not mutate** 08–24; do not change `tsmom_14_3` parameters.
6. **Tests:** suite green; bar/quality tests if production code touched.

## Out of Scope

- LIVE promotion  
- Re-optimizing TSMOM  
- Changing 0.15 / 1.0 risk limits  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ tests/market/ -q --tb=short` (skip missing test dirs if absent)
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. `25_QUALITY_CLEARED_BARS_REPORT.json` present; new dataset `quality_status` in {PASS, PASS_WITH_WARNINGS}
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
