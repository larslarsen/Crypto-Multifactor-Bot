# CURRENT_TASK

Ticket: DEX-002
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DEX-002 — Screened Free DEX OHLCV Acquisition.

REVIEW-0235 rework complete. Provider capabilities are separated; DexScreener
synthetic candles removed; screening is fail-closed; canonical full-snapshot
publication with raw lineage. 84 tests pass, Ruff clean, repo control PASS.

## Evidence

- `tickets/DEX-002.md`
- `docs/reviews/REVIEW-0235_DEX-002_REWORK_AUTHORIZED.md`
- `src/cryptofactors/ingest/dex_fanout.py`
- `src/cryptofactors/ingest/dex_providers.py`
- `src/cryptofactors/ingest/dex_snapshot.py`
- `scripts/research/dex002_snapshot.py`
- `tests/ingest/test_dex_snapshot.py`
- `research/sprint_004/37_DEX_MULTI_PROVIDER_FANOUT.json`
