# PAPER-008 — Formal Paper Package for tsmom_14_3 (Freeze Candidate)

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** EXP-007 (ACCEPTED), DATA-004, ALLOC-001  
**Layer:** paper / promotion evidence / research  
**Architecture:** same path as PAPER-007. **No LIVE.**

## Objective

EXP-007 found **`tsmom_14_3` +16.70%** full-window under risk (gate true). Produce a **dedicated** paper evidence package (single config, clean artifact) and **freeze** the candidate identity for any future forward observation. Still **not** LIVE.

## Scope

1. **Config:** lookback=14, skip=3; factor_id `tsmom_14_3`; model id **`mod_tsmom_14_3_v1`** (or successor if re-registration required).
2. **Session:** Same window/protocol as PAPER-007/EXP-007 (weekly, 2024-04-01 → 2026-07-23, DATA-004 pin, ALLOC-001). Re-run or pin hashes from EXP-007 if bit-identical; prefer explicit re-run for a standalone artifact.
3. **Artifact** `research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json`:
   - Full session metrics (return, risk, complete, gate)
   - `live_eligible: false`
   - `candidate_frozen: true` with freeze note (no further lookback/skip search on this path without new ticket)
   - Cross-ref EXP-006/007, PAPER-007
4. **Registry:** Append experiment row if `experiment_registry.csv` pattern exists for sprint_004.
5. **Do not mutate** 08–23.
6. **Tests:** suite green.

## Out of Scope

- LIVE orders / LIVE promotion ticket  
- Re-optimizing parameters  
- Changing risk limits  
- BAR-001 quality fix (document only)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `24_TSMOM_14_3_PAPER_SESSION.json` present; `live_eligible: false`; `candidate_frozen: true`
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
