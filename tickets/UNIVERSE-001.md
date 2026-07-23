# UNIVERSE-001 — CoinGecko Survivorship-Free Universe Provider

**Priority:** P0
**Status:** ACCEPTED
**Decision:** Option C — Bounded non-survivorship-free universe with current BAR-001 instruments
**Rationale:** CoinGecko doesn't provide listing/delisting dates (even on paid plans). $35/mo Basic gives 2yr price history but not historical membership. CoinMarketCap needed for true survivorship-free.
**Dependencies:** ASOF-001 (accepted), BAR-001 (accepted), EXP-001 (accepted)
**Layer:** universe
**Architecture:** implements research substrate gate item #11 (historical universe snapshots); no ADR required

## Objective

Provide a point-in-time universe of crypto instruments. **Revised:** Use current BAR-001 instruments without survivorship-free guarantee. Accept survivorship bias for initial experiments (#18, #19). Upgrade to CoinMarketCap ($79-299/mo) when proper survivorship-free research is needed.

## Required Contract

- `universe_at(decision_time)` returns instruments from current BAR-001 data
- **Note:** This is NOT survivorship-free. Delisted coins are missing.
- Future upgrade: CoinMarketCap historical snapshots for proper survivorship-free universe
- Deterministic: same inputs → same universe
- Fail-closed on missing data

## Data Source

- Current BAR-001 instruments (Binance/Bybit bars)
- **No historical membership reconstruction** (requires CoinMarketCap or similar)
- Future: CoinMarketCap ($79/mo for 3yr, $299/mo for all-time)

## Deliverables

- `src/cryptofactors/universe/bar001.py` (or similar)
- Public exports from `cryptofactors.universe`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Full historical OHLCV (requires paid plan, future upgrade)
- Factor computation
- Portfolio simulation
- New data sources beyond BAR-001 instruments
- Historical membership reconstruction (requires CoinMarketCap)

## Upgrade Path

When proper survivorship-free research is needed:
1. Subscribe to CoinMarketCap ($79-299/mo)
2. Implement historical universe snapshots
3. Upgrade UNIVERSE-001 to use CoinMarketCap data
4. Re-run experiments with survivorship-free universe

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
