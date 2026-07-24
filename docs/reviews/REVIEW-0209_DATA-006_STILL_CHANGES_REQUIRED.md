# REVIEW-0209 — DATA-006 still CHANGES_REQUIRED

**Ticket:** DATA-006  
**Decision:** CHANGES_REQUIRED (unchanged from REVIEW-0207)  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  
**HEAD under review:** `6e1a93c` (post-revert of improper self-rework)

## Process note

An intermediate commit (`2089345`) attempted option-B rework outside the Sr Dev role and was correctly reverted (`6e1a93c`). This review judges **only** the remaining tree after that revert.

## Evidence check (blocking items from 0207)

| # | Requirement | Status at `6e1a93c` |
|---|-------------|---------------------|
| 1 | Ops test holdout count after DATA-006 bars | **FAIL** — `test_dry_run_emits_ops_report` still asserts `bars_in_holdout_count == 0`; also `DictWriter` / `None` fieldnames error on registry append |
| 2 | Scope reduction **or** true 2017 / full U50+ / BitMEX 2016 | **FAIL** — reports 31–33 have **no** `scope_reduction`; scripts have **no** `why_not_*` fields; delivery remains 2020 start, 23 symbols, BitMEX from 2020, DEX ~180d |
| 3 | DEX / catalog pin vs `resolve_latest` | **FAIL** — no `catalog_reconciliation`; report dex `ds_214c4d…` ≠ `resolve_latest` `ds_1fed0ae…`; market_bars report `ds_890b365e…` ≠ resolve `ds_5578bfc1…` |
| 4 | pytest ops+acquisition+ingest green | **FAIL** — ops test red |

## What remains good (unchanged)

- Canonical bars PASS path exists (~90k rows, 23 symbols, ≥2020 BTC/ETH).
- BitMEX funding + DEX modules/scripts present; PASS datasets in catalog.
- `live_eligible: false` on reports.
- acquisition/ingest suites previously green (ops is the red gate).

## Verdict

**CHANGES_REQUIRED.** Do not accept. Sr Dev must complete REVIEW-0207 items 1–3 on a proper Sr path; Jr integrates and stops for review. No LIVE.

## Required rework (Sr only)

Same as REVIEW-0207:

1. Fix ops test + registry writer so dry-run is green with holdout-boundary bars.
2. Option A (extend history/universe) **or** B (explicit `scope_reduction` / `why_not_*` on reports 31–33 and ticket).
3. Pin report dataset ids vs `resolve_latest` (`catalog_reconciliation` or equivalent).
4. Green: `pytest tests/ops/ tests/acquisition/ tests/ingest/ -q --tb=short`
5. Stop AWAITING_REVIEW, Next NONE.
