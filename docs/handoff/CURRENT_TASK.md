# CURRENT_TASK

Ticket: DATA-006
State: READY
Next required actor: Sr Dev (Strong Model) — full historical backfill (Binance + BitMEX funding + DEX)
Next ticket authorized: DATA-006

**Reviewer Decision (Architecture & Ticket Selection):**

INFRA-001 ACCEPTED (REVIEW-0206). Owner direction: current 10-asset × ~2.5y slice is too small. Authorize full historical backfill.

**Policy update (overrides ARCH-001 contamination lock for data acquisition):**
- DATA-006 may backfill **all available history** (Binance pairs from earliest, BitMEX funding from 2016, DEX stablecoin pools).
- The ARCH-001 lock remains for **TSMOM_14_3 / archived false-discovery selection** — do not un-archive or re-tune that candidate.
- New research on full history still requires honest multi-testing discipline for **selection**; data itself is not restricted to post-2026-07-24.
- No LIVE.

Implement `tickets/DATA-006.md` as written: full-universe Binance klines, BitMEX funding, DEX USDC/USDT, BAR-001 rebuild, ops/report evidence.

## Governing documents

- tickets/DATA-006.md
- tickets/INFRA-001.md
- docs/reviews/REVIEW-0206_INFRA-001_ACCEPTED.md
- tickets/BIN-001.md
- tickets/FUND-005.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/ingest/ -q --tb=short
2. Dry-run backfill scripts produce valid plans
3. Full backfill evidence: BTC/ETH ≥2020 where source allows; DEX dataset published
4. Ops/report reflects expanded bar counts
5. python3 scripts/check_repo_control.py
