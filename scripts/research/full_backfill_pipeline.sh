#!/usr/bin/env bash
# DATA-006 — Full historical backfill orchestration.
#
# Chains the three backfill scripts and the canonical bar rebuild:
#   1. Binance spot klines (U50+ universe, daily)
#   2. BitMEX funding rates
#   3. DEX USDC/USDT stablecoin OHLCV
#   4. Canonical market_bars rebuild via backfill_binance_klines.py
#
# Default: dry-run. Pass --no-dry-run for real network fetches.
#
# Examples:
#   ./scripts/research/full_backfill_pipeline.sh
#   ./scripts/research/full_backfill_pipeline.sh --no-dry-run
#   ./scripts/research/full_backfill_pipeline.sh --symbols BTCUSDT,ETHUSDT

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs

DRY_RUN="--dry-run"
SYMBOLS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-dry-run)
      DRY_RUN="--no-dry-run"
      shift
      ;;
    --symbols)
      SYMBOLS="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--no-dry-run] [--symbols BTCUSDT,ETHUSDT]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

RUN=".venv/bin/python"
LOG="logs/full_backfill_$(date -u +%Y%m%d_%H%M%S).log"

{
  echo "=== DATA-006 full backfill pipeline ==="
  echo "mode: ${DRY_RUN}"
  echo "symbols: ${SYMBOLS:-U50+ default}"
  echo "log: ${LOG}"
  echo

  echo "[1/4] Binance spot klines backfill"
  if [[ -n "$SYMBOLS" ]]; then
    $RUN scripts/research/backfill_binance_klines.py --symbols "$SYMBOLS" $DRY_RUN
  else
    $RUN scripts/research/backfill_binance_klines.py $DRY_RUN
  fi

  echo "[2/4] BitMEX funding backfill"
  $RUN scripts/research/backfill_bitmex_funding.py $DRY_RUN

  echo "[3/4] DEX stablecoin OHLCV backfill"
  $RUN scripts/research/backfill_dex_stablecoin_prices.py $DRY_RUN

  echo "[4/4] Pipeline complete"
  echo "Review reports in research/sprint_004/"
} 2>&1 | tee -a "$LOG"

exit "${PIPESTATUS[0]}"
