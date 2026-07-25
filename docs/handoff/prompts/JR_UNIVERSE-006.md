# Jr Dev prompt — UNIVERSE-006

Model: DeepSeek V4 Flash (Jr). Owner relays this once. No chat with reviewer.

## Goal

Publish `data/survivorship/cmc_dead_universe_full.csv` as a catalog universe dataset and prove `universe_at(t)` works. One-shot file only — **do not** call CoinMarketCap.

## Do

1. Read `tickets/UNIVERSE-006.md` and `src/cryptofactors/universe/cmc_survivorship.py`.
2. Load the CSV; build registry via existing helpers (`normalize_coin_record` / `build_cmc_survivorship_table` / provider publish path if present).
3. Publish to `exp003.db` + store under dataset id suitable for type universe (follow existing catalog publish patterns in repo).
4. Every row must keep `death_date_is_proxy=true` and `source=cmc_data_api_unofficial`.
5. Write `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json` with:
   - `row_count` (expect ≥1500)
   - `dataset_id`
   - `universe_at_2020_01_01_count`
   - `universe_at_2026_07_01_count`
   - `live_eligible`: false
6. Tests for provenance labels + as-of membership (extend `tests/universe/test_cmc_survivorship.py`).
7. Run:
   - `.venv/bin/python -m pytest tests/universe/ -q --tb=short`
   - `python3 scripts/check_repo_control.py`
8. Set ticket + CURRENT_TASK to **AWAITING_REVIEW**. Next ticket authorized: **NONE**.
9. Commit + push.

## Do not

- ACCEPTED
- Live CMC HTTP
- Factor/paper experiments
- DATA-010 / DEX work
- New architecture modules unless publish is impossible without a 20-line helper

## Stop

When AWAITING_REVIEW and evidence JSON exists. Owner notifies reviewer.
