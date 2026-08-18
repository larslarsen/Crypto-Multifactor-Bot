# DATA-009 — BitMEX Full Backfill: All Perps + 2016 History

**Priority:** P1  
**Status:** SUPERSEDED
**Next:** NONE — rejected and subsumed by CEX-001
**Dependencies:** DATA-006 (ACCEPTED), DATA-007 (ACCEPTED), FUND-005 (ACCEPTED)  
**Layer:** acquisition / funding  
**Architecture:** extend existing `backfill_bitmex_funding.py`; publish new canonical dataset. **No LIVE.**

## Objective

Backfill BitMEX perpetual funding rates for **all available perp symbols** from **2016-05-13** (earliest funding data) to present, replacing the DATA-006 scope-reduced slice (5 symbols, 2020 onward).

## Scope

1. **Symbol universe:** discover all perp symbols from BitMEX exchange info or instrument endpoint; backfill funding for every symbol that has funding history.
2. **Full history:** from 2016-05-13 (or symbol inception) to present, 8-hour interval.
3. **Incremental:** watermark-based resume; safe to re-run daily.
4. **Rate-limit safe:** 120 req/min polite budget; single request fetches 500 records.
5. **Dataset:** publish new canonical dataset id (separate from DATA-006 BitMEX dataset).
6. **Report** `research/sprint_004/39_BITMEX_FULL_BACKFILL.json` with:
   - symbols added
   - record count per symbol
   - date span
   - rate-limit incidents
   - pinned dataset id
   - `catalog_reconciliation` match

## Out of scope

- Price/trade data for BitMEX (funding only)
- Other CEXes (DATA-008 covered Binance)
- LIVE

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
3. `39_BITMEX_FULL_BACKFILL.json` present with full perp universe + 2016 start
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next NONE.

## Reviewer disposition — rejected and superseded (2026-08-17)

DATA-009 is not accepted. Its reported dataset
`ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8`
contains 189,570 rows across 45 symbols, but direct inspection found zero nonzero
`funding_rate` values and an empty `funding_interval` in all 189,570 rows. The catalog and
report incorrectly label it `PASS`.

The artifact and report are preserved as rejection evidence. CEX-001 Gate 0 owns atomic
catalog quarantine of this dataset and the four related BitMEX predecessors; CEX-001 owns
all replacement CEX source qualification and data work. DATA-009 authorizes no further
source edit, execution, publication, experiment, PAPER, or LIVE action.
