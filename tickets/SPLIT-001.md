# SPLIT-001 — Purged Chronological Split Engine

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** CAT-001/CAT-001A, REF-001, BAR-001, ASOF-001 (accepted)
**Layer:** validation / splits
**Architecture:** implements architecture §6/11/12 requirements for purged event-time splits; no ADR required

## Objective

Provide a single reviewed implementation that generates deterministic, purged, chronological train/test (and validation) splits so that no future information leaks into model training or evaluation.

## Required contract

- Input: list of instruments, decision-time windows or horizons, embargo (optional), number of folds or train/test ratio.
- Output: ordered list of Split objects, each containing:
  - train_start, train_end, test_start, test_end (as UTC datetimes)
  - list of (instrument_id, decision_time) pairs eligible for that split segment
  - purge/embargo metadata
- All data access for eligibility and feature/label construction must go through the reviewed AsOfStore.
- Event-time rule: a decision at time t may only use observations whose availability_time <= t.
- Purging: no instrument may appear in both training and test with overlapping event windows.
- Embargo: if specified, test must start after train_end + embargo.
- Deterministic: same inputs + seed must produce identical splits.
- Empty / insufficient history must fail closed (no silent short windows).

## Dataset surface (via AsOfStore)

- Market bars (BAR-001)
- Instrument versions (REF-001)
- Fee schedules (FEE-001) if cost-aware splits are requested later

## Deliverables (this ticket)

- `src/cryptofactors/validation/split.py` (or equivalent location) — protocol + implementation
- Public export from the validation package
- Ticket file and governance updates
- Focused tests + gates (Jr)

## Out of scope (this ticket)

- Label or factor computation
- Portfolio simulation or costed backtests
- Experiment bundling
- New data sources or collectors

## Acceptance commands (to be run by Jr after Sr source)

1. `.venv/bin/python -m pytest tests/validation/ -q --tb=short` (or equivalent)
2. `.venv/bin/python -m ruff check src/cryptofactors/validation tests/validation`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/validation tests/validation`
4. `python3 scripts/check_repo_control.py`
5. Full relevant test suite pass where applicable

## Phased ownership

- Sr Dev - Grok Build: production source only, then stop for reviewer inspection.
- Jr Dev - Hermes: tests, gates, records, Git, commit, push after source approval.

## Stop condition

After Sr source + Jr integration + all gates pass, return to AWAITING_REVIEW. Reviewer next. Next ticket authorized: NONE. No factors, no portfolio, no live work.