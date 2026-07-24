# DATA-008 — Free CEX Universe Expansion (Binance-first)

**Priority:** P1  
**Status:** ACCEPTED  
**Dependencies:** DATA-006 (ACCEPTED), DATA-007 (ACCEPTED)  
**Layer:** acquisition / bars  
**Architecture:** free Binance REST + watermarks. **No LIVE.**

## Objective

Expand spot bar universe/history under **free** Binance rate limits using DATA-007 capacity estimates (20k symbols/day headroom). Prioritize symbols by screening criteria (liquidity/volume), not "all listings at once." Pin the expanded dataset under a new canonical dataset id in the catalog.

## Scope

1. **Symbol priority list** from liquidity/volume screen (top N by 30d volume on Binance, configurable). Implement as a sort + take, not a manual list.
2. **Incremental backfill** with watermarks per symbol. Resume-safe. Multi-day safe at the estimated 20k symbols/day rate.
3. **Extend history** where DATA-006 stopped (23 symbols). Add additional symbols from the priority list up to a reasonable free-tier boundary. Optionally deepen major symbols back to 2017 if time and rate limit allow.
4. **Report** `research/sprint_004/36_BINANCE_UNIVERSE_EXPANSION.json` with:
   - symbols added and their span
   - rate-limit incidents (429s, backoffs)
   - total rows added
   - pinned canonical dataset id for consumers
5. **Tests:** unit tests for prioritization logic, watermark management, and rate-limit resilience. No network in CI.

## Out of scope

- Deribit, Bybit, or other CEXes (future ticket)
- DEX expansion (DEX-002)
- LIVE
- Paid Binance plans

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
3. `36_BINANCE_UNIVERSE_EXPANSION.json` present with symbols, span, dataset id
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next NONE.
