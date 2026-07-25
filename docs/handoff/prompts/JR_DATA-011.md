# Jr Dev prompt — DATA-011

Model: DeepSeek V4 Flash (Jr). Owner relays once. No chat with reviewer.

## Goal

Produce a PASS-quality daily bar dataset for Binance USDT symbols that are **not** dead per the CMC graveyard. Follow the quality-cleared bars pattern from DATA-005.

## Context

- UNIVERSE-006 published the CMC graveyard as catalog dataset `ds_22d2100a575a9764cceec9cc75f45867047969d1b348fd630771bfb083f5b3d8` (ACCEPTED)
- Graveyard has 1,756 dead coins with `universe_at(t)` that excludes inactive coins
- We don't have an ARCH-002 binding yet — so for this ticket the approach is:
  1. Read the graveyard provider
  2. For each paper symbol, look up its coin name/symbol in CMC
  3. If found and dead at time → exclude from bar dataset
  4. Quality-clear bars for survivors

## Do

1. Read `src/cryptofactors/universe/cmc_survivorship.py` — understand `CMCSurvivorshipProvider.from_csv()`, `universe_at(t)`, `records()`.

2. Read `src/cryptofactors/execution/symbols.py` — understand `PAPER_TO_INSTRUMENT_ID`, `PAPER_TO_BINANCE_MAP`.

3. Study the existing quality-cleared bars script `scripts/research/quality_cleared_bars.py` — replicate the pattern.

4. Write `scripts/research/build_bound_bars.py` that:
   - Loads CMC graveyard from CSV (`data/survivorship/cmc_dead_universe_full.csv`)
   - For each paper symbol, checks CMC by symbol match
   - Skips any symbol whose coin is inactive **and** dead before the bar date range
   - Backfills Binance klines for survivors (reuse existing backfill helpers)
   - Quality-clears the bars (reuse BAR-001 daily path)
   - Publishes as PASS dataset
   - Emits `research/sprint_004/43_BOUND_BARS.json` with:
     - `symbols_requested`, `symbols_excluded` (with reason), `symbols_backfilled`
     - `dataset_id`, rows per symbol, date range per symbol
     - `exclusion_reasons`: list of (symbol, cmc_id, death_date)

5. Tests (extend `tests/universe/`):
   - Symbol known to CMC dead → excluded
   - Symbol not in CMC → included
   - Empty graveyard → all symbols included

6. Run:
   - `.venv/bin/python -m pytest tests/ -q --tb=short`
   - `python3 scripts/check_repo_control.py`

7. Set ticket + CURRENT_TASK to **AWAITING_REVIEW**. Next ticket: **NONE**.
8. Commit + push.

## Do not

- ACCEPTED
- Call CMC HTTP (CSV only)
- Add MEXC/Kraken/Blofin
- Factor experiments
- ARCH-002 binding contract (that's separate)
- Change the graveyard data

## Hint

The CMC `records()` return rows with `symbol` field matching crypto tickers (e.g. "BTC", "ETH"). Match against the non-USD suffix of Binance pairs (e.g. BTCUSDT → "BTC"). A simple exclusion rule:

```python
cmc_symbols_dead_by_2020 = {
    r["symbol"] for r in provider.records()
    if not r["is_active"] and provider.universe_at(t_2020) does NOT include r["instrument_id"]
}
```

Or simpler: just check if the coin is in the `universe_at(t)` set at all — alive coins are in it, dead ones are not.

## Stop

When AWAITING_REVIEW and evidence JSON exists. Owner notifies reviewer.
