# HARDEN-001 — Paper Path Hardening (Real As-Of + Venue Stubs)

**Priority:** P1
**Status:** AWAITING_REVIEW
**Dependencies:** PAPER-004 (ACCEPTED), EXEC-002 (ACCEPTED), ASOF / catalog stack
**Layer:** execution / catalog / ops
**Architecture:** Hardens paper trading toward production readiness. **No LIVE promotion. No real order submission.**

## Policy

LIVE remains blocked until paper trading is profitable on **real** (non-synthetic) as-of data. This ticket only builds the path to measure that.

## Objective

1. Run the MOM-TS-01 paper loop against `CatalogAsOfStore` (or documented fallback) when a control DB + market dataset exist.
2. Add a non-funded venue connectivity stub / smoke probe using the existing `VenueAdapter` protocol (read-only: ping, list symbols, or fetch last price — no orders).
3. Emit a hardening report artifact with gate status, data mode (synthetic vs real), equity metrics, and venue probe results.

## Scope

1. **Real as-of paper path**
   - Extend `scripts/run_paper_momts.py` (or add `scripts/run_paper_momts_real.py`) so non-`--dry-run` mode:
     - Opens `CatalogAsOfStore` from `--db-path`
     - Uses published `--market-dataset-id`
     - Builds decision times from available bar coverage (or explicit `--start` / `--end`)
     - Supplies `get_prices_at` from as-of store closes
     - Fails closed with a clear error if DB/dataset missing or empty (no silent synthetic fallback)
   - Keep `--dry-run` synthetic path for CI.

2. **Venue stub (read-only)**
   - Implement a minimal stub adapter (e.g. `NullVenueAdapter` or `HttpPingVenueAdapter`) under `src/cryptofactors/execution/` that satisfies `VenueAdapter` for connectivity checks only.
   - Script flag `--venue-probe` runs the probe and records success/latency/error — **never** places orders.

3. **Hardening report**
   - Write `research/sprint_004/10_PAPER_HARDEN_REPORT.json` including:
     - `data_mode`: `synthetic` | `real_asof`
     - paper equity / net return / observation ref
     - ops gate status
     - venue probe result
     - `live_eligible`: always `false` in this ticket (explicit)

4. **Tests**
   - Real path fails closed without DB.
   - Dry-run still works.
   - Venue probe does not call order methods.
   - Report schema fields present.

## Out of Scope

- `LIVE_APPROVED` promotion or owner authority flows.
- Funded trading, API keys in repo, or live order routing.
- New factor families.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution`
4. `.venv/bin/python scripts/run_paper_momts.py --dry-run` (or equivalent) produces harden report in synthetic mode
5. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, Git after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
