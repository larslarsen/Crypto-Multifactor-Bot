# UNIVERSE-005 — Full CEX Universe Expansion (Binance + MEXC + Kraken + Blofin)

**Priority:** P1
**Status:** DRAFT
**Dependencies:** DATA-008 (ACCEPTED), UNIVERSE-003 (ACCEPTED), CMC survivorship backfill (running)
**Layer:** universe / acquisition
**Architecture:** add exchange connectors + backfill + paper mapping. **No LIVE.**

## Objective

Expand the CEX universe from the current 23 symbols to ALL tradeable USDT pairs on Binance, MEXC, Kraken, and Blofin with full survivorship (birth + death dates). This replaces the U50+ CMC survivorship screen with exhaustive exchange-level coverage.

## Current State

- 23 Binance USDT pairs mapped to paper universe (`symbols.py` instruments 1–23)
- 52 Binance symbols backfilled (DATA-008) but only 23 mapped
- 470 Binance, 1,741 MEXC, 56 Kraken, 479 Blofin USDT pairs exist on the exchanges (~2,746 total)
- No connectors exist for MEXC, Kraken, or Blofin
- CMC dead-universe graveyard being collected (1,756 dead coins, not exchange-specific)

## Scope

### In scope

1. **Exchange connectors** — Implement MEXC, Kraken, and Blofin kline fetchers (mirroring `BinanceKlineFetcher` pattern). Each fetcher supports symbol discovery (via `exchangeInfo` or equivalent) and `klines` (historical + incremental OHLCV). Rate-limit discovery: probe each exchange's tier.

2. **Full symbol discovery** — For each exchange:
   - Binance: all `TRADING` USDT pairs from `exchangeInfo` (~470)
   - MEXC: all pairs from `ticker/price` (~1,741)
   - Kraken: all USDT pairs from `AssetPairs` (~56)
   - Blofin: all USDT pairs from `market/tickers` (~479) — note `instId` uses `-` separator (e.g. `BTC-USDT`)

3. **Birth date via earliest bar** — For each symbol, the earliest available kline record is its proxy birth date. This is the exchange-specific listing date, which is more precise than CMC global data.

4. **Death detection** — For symbols that delist during the backfill window: detect via `exchangeInfo` status change (`BREAK`/`POST_DELISTING`). Death date = last traded bar timestamp. Cross-check against CMC graveyard.

5. **Full historical backfill** — Backfill all discovered pairs from exchange inception (or as far back as free API allows) to present. Reuse the `backfill_binance_klines.py` pattern for each new exchange.

6. **Paper universe mapping** — Extend `symbols.py` with `PAPER_TO_BINANCE_MAP`, `PAPER_TO_INSTRUMENT_ID`, etc. for all ~2,267 symbols. Each exchange gets its own paper prefix convention (e.g. `XBTUSD` = Binance BTC/USDT, `MXBTUSD` = MEXC BTC/USDT, `KXBTUSD` = Kraken BTC/USDT) or a unified symbol space.

7. **Universe survivorship table** — Publish `ref_instrument` and `ref_listing_event` tables in the catalog with birth/death dates per exchange per symbol.

8. **Report** `research/sprint_004/50_CEX_UNIVERSE_EXPANSION.json` with:
   - symbols discovered per exchange
   - backfill coverage (rows, date range) per symbol
   - birth dates resolved per symbol
   - delisted/dead symbols detected
   - rate-limit incidents per exchange

### Out of scope

- DEX universe (separate ticket)
- Factor computation on new symbols
- Portfolio allocation changes
- LIVE trading
- Paid data sources

## Deliverables

1. MEXC kline fetcher (`src/cryptofactors/acquisition/mexc_fetcher.py`)
2. Kraken kline fetcher (`src/cryptofactors/acquisition/kraken_fetcher.py`)
3. Blofin kline fetcher (`src/cryptofactors/acquisition/blofin_fetcher.py`)
4. Full backfill script (`scripts/research/backfill_all_cex.py`)
5. Updated `symbols.py` with all ~2,746 paper symbols
6. Published `ref_instrument` + `ref_listing_event` tables in catalog
7. Report `50_CEX_UNIVERSE_EXPANSION.json`

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
3. Each exchange fetcher returns valid OHLCV for at least one test symbol in dry-run mode
4. Published universe dataset contains ≥2,000 instruments with birth dates
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
