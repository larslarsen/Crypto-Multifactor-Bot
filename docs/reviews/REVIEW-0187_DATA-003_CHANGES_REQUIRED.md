# REVIEW-0187 — DATA-003 CHANGES_REQUIRED (rework incomplete)

**Ticket:** DATA-003  
**Decision:** CHANGES_REQUIRED  
**Prior:** REVIEW-0186  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit reviewed:** `e6fabac`

## Verdict

REVIEW-0186 items B2–B4 are largely addressed. **B1 is only half-fixed:** int keys work for the price helper path that requests `["close"]` only. The **factor path still breaks** when the adapter rewrites the `instrument_id` column.

## Cleared vs REVIEW-0186

| ID | Status |
|----|--------|
| B2 resolve_latest_by_type | **OK** — catalog helper + script fallback + test |
| B3 mocked E2E → market_bars | **OK** — `test_e2e_mocked_canonical_market_bars_in_catalog` |
| B4 as-of price hit int keys | **OK** for raw store + adapter with `["close"]` only |
| Fail-closed guards | **OK** |
| instrument_id_map in artifact | **OK** |
| manifest_uri path join in as_of load | **OK** (needed for real store layout) |

## Blocker

### B5 — `PaperSymbolAsOfAdapter._maybe_translate_instrument_id` uses nonexistent API

```python
return table.replace_column("instrument_id", [pa.array(new_vals, type=pa.string())])
```

PyArrow `Table` has **no** `replace_column`. Correct pattern is `set_column` / `drop`+`append_column` by field index.

`TimeSeriesMomentumFactor._price_at` requests:

```python
fields = ["instrument_id", field, "availability_time", "period_start"]
```

So real mode with `make_tsmom_30_7(PaperSymbolAsOfAdapter(...))` will hit the translate path and raise `AttributeError`, wrapped as `TSMOMError` / empty signals — **factor does not work on real as-of**.

B4 test only queries `["close"]`, so translation is skipped — **false green**.

**Required:**
1. Fix column rewrite with valid PyArrow API (or stop rewriting and leave int ids; factor only needs close).
2. Add test: adapter `latest_available(..., ["XBTUSD"], ["instrument_id", "close"], ...)` returns rows and finite close (proves factor field list).
3. Prefer optional: end-to-end factor `compute` smoke on temp published bars (one as_of).

## Non-blocking

- Backfill assigns `instrument_int_id = idx + 1` by symbol list order; must stay aligned with `PAPER_TO_INSTRUMENT_ID` (BTC=1, ETH=2). Document or assert in backfill.
- `to_binance_symbol` still soft-passthrough for unknown; `to_instrument_id` is correctly fail-closed.
- Watermark still decision-time, not bar `period_end`.
- Dry-run artifact still has `/tmp` paths and default `ds_market_bars` before resolve (synthetic path).

## Policy

LIVE blocked. No acceptance until factor-compatible as-of adapter is proven.

## Re-review checklist

1. Fix B5 + test with factor field list  
2. Jr gates green  
3. AWAITING_REVIEW, Next NONE  
