# UNIVERSE-001 — CoinGecko Survivorship-Free Universe Provider

**Priority:** P0
**Status:** BLOCKED
**Dependencies:** ASOF-001 (accepted), BAR-001 (accepted), EXP-001 (accepted)
**Layer:** universe
**Architecture:** implements research substrate gate item #11 (historical universe snapshots); no ADR required

## Objective

Provide a point-in-time universe of crypto instruments using CoinGecko's free tier. Include both active and delisted coins to avoid survivorship bias. Use existing BAR-001 price data for market bars; CoinGecko provides only the universe membership (which instruments existed at each point in time).

## Required Contract

- `CoinGeckoUniverseProvider` fetches full coin list (active + delisted) from CoinGecko `/coins/list?status=inactive`
- `universe_at(decision_time)` returns all instruments that were listed at `decision_time` (listing_date <= decision_time)
- Delisted instruments included up to their last known active date
- Store universe snapshots in the control catalog (MAN-001 compatible)
- Deterministic: same inputs → same universe
- Fail-closed on API errors or missing data

## Data Source

- CoinGecko free tier: `/coins/list?include_platform=false&status=active,inactive`
- Returns: id, symbol, name, (active/inactive status)
- Limitation: 365 days of OHLCV history only (close/volume/market_cap)
- Price data comes from existing BAR-001 (Binance/Bybit bars)

## Deliverables

- `src/cryptofactors/universe/coingecko.py` (or similar)
- Public exports from `cryptofactors.universe`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Full historical OHLCV (requires paid plan, future upgrade)
- Factor computation
- Portfolio simulation
- New data sources beyond CoinGecko universe list

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/universe/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/universe tests/universe`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/universe tests/universe`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE.
