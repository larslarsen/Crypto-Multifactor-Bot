# REVIEW-0186 — DATA-003 CHANGES_REQUIRED

**Ticket:** DATA-003 — Real As-Of Path Correctness  
**Decision:** CHANGES_REQUIRED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  

## Verdict

Fail-closed guards and symbol *string* map are a step forward, but the **real as-of path still cannot resolve market bars correctly**. Do not claim DATA-003 complete.

## What works

- `--store-root` + fail closed if missing (`scripts/run_paper_momts.py`)
- Fail closed if control DB missing
- Fail closed if default/explicit dataset id missing from catalog
- `symbols.py` paper↔Binance string map; unit tests
- Bare `except Exception: pass` removed; `AsOfAccessError` re-raised as `PaperExecutionError`
- Artifact `12_REAL_ASOF_CORRECTNESS.json` with `live_eligible: false`
- Jr gates green after fix of nonexistent `list_datasets()`

## Blockers (must fix)

### B1 — Market bar keys are **integer** `instrument_id`, not venue symbols

`CatalogAsOfStore._latest_market_bars` does:

```python
key_set = {int(k) for k in keys}
```

Canonical bars from DATA-002 backfill use numeric ids (`1`, `2`, …) in partitions / columns.

`get_real_prices` still does:

```python
binance_sym = to_binance_symbol(sym)  # e.g. "BTCUSDT"
as_of_store.latest_available(dataset_id, [binance_sym], ["close"], dt)
```

`int("BTCUSDT")` → `ValueError` (not `AsOfAccessError`). Factor path via `make_tsmom_30_7` uses paper symbols / `_asof_key` string fallback — same mismatch against int bar keys.

**Required:** stable map paper/Binance symbol → **int instrument_id** consistent with how bars were published (or publish bars keyed the way as-of expects and document it). Wire both `get_real_prices` and factor evaluation to that map. Fail closed if unmapped.

### B2 — Default `--market-dataset-id ds_market_bars` vs content-addressed ids

Backfill publishes `ds_<sha256…>`. Real mode requires the operator to pass the real id every time; no discovery by `dataset_type == market_bars` (and `list_datasets` does not exist). Acceptable only if documented **and** fail message points at report field `canonical_dataset_id`; better: resolve latest `market_bars` via catalog query helper (small, tested).

### B3 — Missing required test: mocked E2E to `market_bars`

Ticket required: fetch → RAW → normalize → MAN source → canonical → catalog assert. Still only partial coverage in `tests/acquisition` (source path) + script dry-run. Add a **pytest** E2E (mock HTTP) asserting `dataset_type == "market_bars"`.

### B4 — No proof real price path returns rows

No test that `latest_available` with correct int keys returns `close` after a mini publish into temp store+DB. Without this, B1 can regress silently.

## Non-blocking

- Watermark is last **decision** time, not max bar `period_end` / event end — rename or fix in follow-up.
- Artifact from dry-run embeds `/tmp/...` paths — fine for synthetic; real run should rewrite.
- Unused imports in test file (`PAPER_TO_BINANCE_MAP`, `PaperExecutionError`, `datetime`).
- Partial universe: some symbols missing prices → omitted until all empty; prefer fail closed if coverage &lt; threshold for paper.

## Policy

LIVE still blocked. Synthetic dry-run PnL is not real-data paper.

## Required for re-review

1. Int instrument_id map end-to-end (prices + factor).  
2. Dataset id resolution or crystal-clear CLI contract + test.  
3. Pytest mocked E2E → `market_bars`.  
4. Pytest mini real-asof price hit (temp catalog+store).  
5. Jr gates green; stop AWAITING_REVIEW, Next NONE.
