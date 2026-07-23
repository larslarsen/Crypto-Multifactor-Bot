# MOMTS-001 — MOM-TS-01 Factor + Confirmatory Run Path (EXP-2026-019 / EXP-2026-020)

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** EXP-001, BASE-001, LABEL-001, SPLIT-001, PORT-001, SERV-001, HOLDOUT-001, EXEC-001, UNIVERSE-003 (CMC proxy accepted for Aware-level)
**Layer:** factors / experiments / research execution
**Architecture:** Implements registered confirmatory experiments; no new ADR required. Survivorship posture locked by reviewer (see below).

## Reviewer posture (do not re-litigate)

- **DF-08 / survivorship:** CMC dead-coin proxy backfill (ADR-0012 / UNIVERSE-003) is **sufficient for Aware-level research** on EXP-2026-019/020. Final tradable price and failure-cause gaps remain documented residuals only; they do **not** re-block these experiments.
- **BLOCKED_DATA lift:** Substrate (as-of, splits, labels, bundles/fingerprints, portfolio sim, paper broker, serving parity, holdout) is accepted complete enough to leave `BLOCKED_DATA` for these two IDs.
- **Scope discipline:** First runnable path is **spot long/cash + raw exposure**. Perpetual long/short, funding-event cashflows, margin/liquidation absorbing exits, and vol-managed cells remain **mandatory later cells** but are **out of scope for MOMTS-001** (do not invent funding authority; FUND-* remains separate).

## Objective

Unblock and implement the minimum honest path to **execute** registered experiments:

| ID | Signal | Horizon |
|----|--------|---------|
| EXP-2026-019 | `tsmom_30_7 = log(P[t-7d] / P[t-30d])` | 7d |
| EXP-2026-020 | `tsmom_90_7 = log(P[t-7d] / P[t-90d])` | 7d |

Per `research/sprint_004/factor_cards/MOM-TS-01_time_series_momentum.md` and `01_MOMENTUM_OPERATIONALIZATION.md`.

## Required contract

### Factor (`MOM-TS-01`)

- New production factor(s), **not** a silent rename of cross-sectional `MomentumFactor` / MOM-01.
- Exact skip-window log returns: 30→7 and 90→7 calendar-day (or bar-equivalent documented) lookbacks ending **7d before** decision (skip last 7d of price path in the signal).
- Missing history → missing (omit instrument); exact zero → flat score (cash), not imputed.
- Deterministic; as-of only; fail-closed on non-UTC / malformed store responses.

### Experiment runner (confirmatory)

- Build `ExperimentBundle` (EXP-001) fingerprints for EXP-2026-019 and EXP-2026-020 separately (no combined verdict).
- Universe: audited U50 or best available PIT membership from accepted universe providers; document membership source in bundle metadata.
- Labels: 7d forward return via LABEL-001 / event intervals.
- Splits: purged chronological folds via SPLIT-001.
- Portfolio cell **in scope:** spot long/cash, equal notional (or rank-weight long-only of positive TS signal), costed via PORT-001 `CostConfig`.
- Emit structured run artifacts (metrics table + bundle ids) under a deterministic research path; no promotion events.

### Registry hygiene

- Update `research/sprint_004/05_EXPERIMENT_REGISTRATIONS.csv` status for EXP-2026-019/020 from `BLOCKED_DATA` → `READY_TO_RUN` when factor+runner land, then → `EXECUTED` only after a successful gated dry-run with fixtures (not live network).

## Deliverables

- `src/cryptofactors/factors/tsmom.py` (or equivalent) — TimeSeriesMomentumFactor 30-7 / 90-7
- Public exports from `cryptofactors.factors` as needed
- `src/cryptofactors/experiments/momts_runner.py` (or under `validation/`) — confirmatory runner
- Tests with synthetic as-of price panels (no live network)
- Optional: script entrypoint under `scripts/research/` for offline dry-run
- Registry CSV status update
- Ticket + governance records

## Out of scope

- Reopening DF-08 authority debates
- Perpetual / funding / liquidation wealth paths (follow-on ticket)
- Vol-managed exposure cells (follow-on)
- LIVE routing or paper promotion of results
- Joint momentum/carry
- Retuning lookbacks after seeing results

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/factors/ tests/experiments/ -q --tb=short` (or paths used)
2. `.venv/bin/python -m ruff check src/cryptofactors/factors src/cryptofactors/experiments tests`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/factors src/cryptofactors/experiments tests`
4. `python3 scripts/check_repo_control.py`
5. Tests assert 30-7 and 90-7 formulas match the factor card on a fixed synthetic series
6. Tests assert missing history does not become zero; zero signal is flat
7. Runner produces distinct EXP-001 fingerprints for 019 vs 020

## Phased ownership

- Sr Dev (Strong Model): production source only. Stop for reviewer.
- Jr Engineer (Weak Model): tests polish if needed, gates, records, Git, commit, push after approval.

## Stop condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
