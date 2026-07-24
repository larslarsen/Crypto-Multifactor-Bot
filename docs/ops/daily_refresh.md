# INFRA-001 Daily Bar Refresh Operations

## Purpose

Automated, deterministic, idempotent daily refresh of Binance spot 1d klines into the catalog via BAR-001 (transform v6, native 1d eligible → PASS quality). The runner is local-first: no cloud daemon, no systemd, no always-on service.

## Components

- `scripts/ops/daily_refresh.py` — main runner.
- `scripts/ops/run_daily.sh` — shell wrapper for cron or manual execution.
- `research/sprint_004/30_DAILY_OPS_REPORT.json` — daily machine-readable report.

## Modes

### Dry-run (default)

No network fetch, no paper loop. Reports on the latest canonical `market_bars` dataset. Useful for cron smoke tests and days when the exchange has not yet delivered new bars.

```bash
./scripts/ops/run_daily.sh --dry-run
```

### Real incremental refresh

Fetches new bars from the day after the latest source dataset `event_end` through the current UTC day, publishes source-normalized datasets, then publishes a new canonical `market_bars` dataset.

```bash
./scripts/ops/run_daily.sh --no-dry-run
```

## Paper loop

The paper step is **disabled by default** (`--run-paper` to enable). Even when enabled, the runner:

- Never runs the archived `tsmom_14_3` / `mod_tsmom_14_3_v1` (REJECTED).
- Only runs a pre-registered active factor.
- Currently no pre-registered factor exists, so the paper step skips with `paper_skipped: true`.

## Scheduling

Use local cron. Example entry (07:00 UTC daily):

```cron
0 7 * * * cd /home/lars/Crypto_Multifactor_Bot && ./scripts/ops/run_daily.sh >> logs/daily_refresh.log 2>&1
```

No systemd, Kubernetes, or other cloud scheduler is required.

## Holdout policy

- Holdout starts: `2026-07-24T00:00:00+00:00`.
- All bars through `2026-07-23` are contaminated by prior grid search, selection, and paper validation.
- The refresh runner may accumulate fresh holdout bars, but it does **not** perform any factor exploration or selection on them.
- Any future factor test must be pre-registered using `tickets/templates/PRE_REGISTERED_TEST.md` before touching holdout data.

## Idempotency

- Re-running the same calendar day is safe.
- If no new bars are available, the runner reuses the existing canonical dataset and emits a report.
- Content-addressed datasets collapse duplicates.

## LIVE policy

No LIVE authorization. `live_eligible` is always `false` in the ops report.
