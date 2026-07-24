#!/usr/bin/env bash
# INFRA-001 local daily wrapper for cron or manual execution.
#
# Example crontab (runs at 07:00 UTC after Binance 1d close):
#   0 7 * * * cd /home/lars/Crypto_Multifactor_Bot && ./scripts/ops/run_daily.sh >> logs/daily_refresh.log 2>&1
#
# For a dry-run smoke test (no network fetch, no paper loop):
#   ./scripts/ops/run_daily.sh --dry-run
#
# For a real incremental refresh (when new bars are available):
#   ./scripts/ops/run_daily.sh --no-dry-run

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs

# Default: dry-run. Pass --no-dry-run to fetch and publish real bars.
exec .venv/bin/python scripts/ops/daily_refresh.py "$@"
