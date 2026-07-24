# REVIEW-0207 — DATA-006 CHANGES_REQUIRED

**Ticket:** DATA-006 — Full Historical Backfill  
**Decision:** CHANGES_REQUIRED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  

## What is good

| Deliverable | Evidence |
|-------------|----------|
| Binance → BAR-001 | `ds_890b365e…` **PASS**, 90,276 bars, 23 symbols, 2020-01-01 → 2026-07-24 |
| BTC/ETH ≥2020 | Met (ticket acceptance #3) |
| BitMEX funding | `ds_f61c6934…` PASS, 32,768 rows, 5 symbols |
| DEX stablecoin | published PASS dataset(s); GeckoTerminal ingest module present |
| Scripts | `backfill_binance_klines.py`, `backfill_bitmex_funding.py`, `backfill_dex_stablecoin_prices.py`, `full_backfill_pipeline.sh` |
| BIN-001 | listing-day partial bar → WARNING (reasonable) |
| Symbol maps | extended through PEPE |
| `live_eligible` | false on reports |
| `pytest tests/acquisition/ tests/ingest/` | PASS |
| ruff | PASS |

## Blocking issues

### 1. Ops regression (must fix)

```
tests/ops/test_daily_refresh.py::test_dry_run_emits_ops_report
assert data["bars"]["bars_in_holdout_count"] == 0
# actual: 23  (one bar per symbol on 2026-07-24 = holdout start)
```

DATA-006 correctly extends bars through **2026-07-24**. Holdout count of 23 is economically right; the INFRA-001 test is stale. **Fix the test** (and any docs that claim zero holdout bars) so dry-run remains green after full backfill.

### 2. Ticket claims vs delivery (must document or extend)

| Claim | Delivered |
|-------|-----------|
| Earliest available **2017+** | **2020-01-01** only |
| BitMEX funding from **2016-05** | **2020-01-01** only |
| **All** U50+ / full exchange depth | **23** listed symbols only |
| Hourly + daily | Evidence is daily-scale (~2397 rows/BTC ≈ daily) |

Either:
- **A)** Extend backfill to true earliest API history + broader universe, **or**
- **B)** Amend ticket acceptance text + reports with an explicit **scope reduction** and `why_not_2017` / `why_not_full_listing` fields (API limits, watermark, intentional U23 freeze).

Silence is not acceptable — the objective said “no more limited slice.”

### 3. Catalog / report hygiene (should fix)

- DEX report `dataset_id` (`ds_214c4d…`, 356 rows) ≠ `resolve_latest_by_type("dex_stablecoin_ohlcv")` (`ds_7f87fac…`, 180 rows). Explain dual publish or pin the report id.
- `experiment_registry.csv` has **CRLF** and mixed rows; DictWriter path previously threw `fields not in fieldnames: None` under some states — harden `_append_registry_row` against empty/None keys.

## Non-blocking

- BitMEX default start in CLI is 2016-05-14 but published coverage is 2020 — same as (2).
- No LIVE (correct).
- Do not un-archive tsmom_14_3 (correct).

## Required rework (Sr)

1. Fix `tests/ops/test_daily_refresh.py` for holdout bars ≥ holdout_start.
2. Choose **A or B** on history/universe; update reports 31–33 with explicit fields.
3. Reconcile DEX dataset ids in report vs catalog.
4. Re-run:  
   `.venv/bin/python -m pytest tests/ops/ tests/acquisition/ tests/ingest/ -q --tb=short`  
   must be green.
5. Stop AWAITING_REVIEW, Next NONE.

## Verdict

**CHANGES_REQUIRED** — solid spine, not yet ticket-complete on “full history / all assets,” and one broken ops test.
