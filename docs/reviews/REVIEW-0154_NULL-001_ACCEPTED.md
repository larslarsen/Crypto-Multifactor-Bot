# REVIEW-0154 — NULL-001 ACCEPTED

**Ticket:** NULL-001 — Null Factor Test (Experiment #18)
**Status:** ACCEPTED
**Date:** 2026-07-22
**Reviewer:** GPT-5.6 sol
**Next required actor:** None
**Next ticket authorized:** NONE

## Corrections completed

- P1: test parameters restored to ticket spec (100 assets, 365 days, ±0.5 Sharpe)
- P1: CatalogAsOfStore integration verified with real store + synthetic Parquet
- P2: factor contracts moved to neutral module (contract.py)
- P2: string/bytes universe rejection verified
- P2: per-instrument seeding for universe-stable scores verified
- P2: unused type: ignore removed
- P2: misleading IR check removed

## Evidence

- pytest: 11/11 pass (4m30s)
- ruff: clean
- mypy: clean
- check_repo_control: PASS

## Files

- `src/cryptofactors/factors/contract.py` (39 lines)
- `src/cryptofactors/factors/null.py` (129 lines)
- `tests/test_null_factor.py` (662 lines)

## State

NULL-001 ACCEPTED. No further work on this ticket. No next ticket authorized.
