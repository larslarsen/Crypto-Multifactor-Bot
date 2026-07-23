# CURRENT_TASK

Ticket: DATA-001
State: READY
Next required actor: Sr Dev (Strong Model) — Binance klines through RAW-001/MAN-001
Next ticket authorized: DATA-001

**Reviewer Decision (Architecture & Ticket Selection):**

HARDEN-001 ACCEPTED (REVIEW-0183). Hardening, paper path, and funding resolution are complete. The system runs end-to-end on **synthetic** data only.

Authorizing **DATA-001**:
1. Binance spot klines fetcher → RAW-001 content-addressed store
2. Wire existing `ingest/binance.py` normalizer + MAN-001 publish
3. Canonical bars via existing market/bars path
4. Backfill U50 history (target from ~2020 or earliest available)
5. Incremental watermark updates

**Policy:** No LIVE promotion. Paper on real data comes after DATA-001 lands non-empty published datasets. LIVE still blocked until paper is profitable on real data.

## Governing documents

- tickets/DATA-001.md (READY)
- tickets/HARDEN-001.md (ACCEPTED)
- docs/reviews/REVIEW-0183_HARDEN-001_ACCEPTED.md
- tickets/RAW-001.md, tickets/MAN-001.md, tickets/UNIVERSE-001.md (accepted)

## Acceptance (Jr)

1. python3 -m pytest tests/acquisition/ -q --tb=short
2. python3 -m ruff check src/cryptofactors/acquisition/
3. python3 -m mypy --no-error-summary src/cryptofactors/acquisition/
4. Backfill script fetches ≥1 asset daily klines; published dataset in catalog
5. python3 scripts/check_repo_control.py
