# FX-002 — Stablecoin FX Source Feasibility Audit

**Ticket:** FX-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Lead Quantitative Finance Researcher/Engineer (reviewer)
**Date:** 2026-07-21

## Summary Decision

No candidate source passes all mandatory gates for a primary point-in-time USD-per-stablecoin historical source.

**Recommendation: NONE**

## Evidence Register

See `research/fx_002/EVIDENCE_REGISTER.csv`

All raw in /tmp/fx_002_raw (not committed). Malformed no-/data/ archive rows deleted.

## Mechanical Preflight (literal, exact as required)

Command: (exact bad-string preflight per task)

Output:
(no matches)
1

## Per Provider (corrected)

### Kraken, Coin Metrics, DefiLlama
Unchanged from prior (no /data/ issues). All REJECTED.

### Binance (corrected /data/ paths only)

- Direct symbols: USDTUSD (quote=USD), USDCUSD (quote=USD). rate_direction = USD per USDT / USDC.
- 2022-05-01 archives (correct path): 404 for both. Proves no object for depeg window.
- 2026-07-20 archives (correct path): 200 for both. 1-row CSV (no header): open_time, o,h,l,c,volume,... close 0.9992 (USDT), 0.99981 (USDC). Confirms USD per stable.
- CHECKSUMs for 2026: 200, match exactly local shas.
- Last-Modified present on 200 responses.
- Historical: recent/partial (2026 succeeds, 2022 depeg absent).
- Depeg: failed (404 on 2022-05-01).
- Fiat semantics, PIT, revisions, licensing: UNKNOWN.
- Recommend: NONE

## Decision Matrix

See `research/fx_002/decision_matrix.csv` (schema from REVIEW-0085)

## Source Notes

See `research/fx_002/sources/`

## Acceptance Commands (literal)

1. `python3 scripts/check_repo_control.py`
   Repo control check: PASS

2. `PYTHONPATH=src uv run pytest -q --tb=short`
   ........................................................................ [ 16%]
   ........................................................................ [ 32%]
   ........................................................................ [ 48%]
   ........................................................................ [ 64%]
   ........................................................................ [ 80%]
   ........................................................................ [ 96%]
   .................                                                        [100%]
   ================================ warnings summary ================================
   tests/test_archives.py::test_duplicate_member_names
     /home/lars/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/zipfile/__init__.py:1661: UserWarning: Duplicate name: 'a.csv'
       return self._open_to_write(zinfo, force_zip64=force_zip64)

   -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

   100 passed in 0.20s (1 warning)

## Records

- FX-002_JR_BINANCE_DIRECT_USD_AUDIT_TASK.md marked FAILED - REVIEW-0086.
- This task marked COMPLETED.
- FX-002 set to AWAITING_REVIEW.
- FX-001 remains ACCEPTED.
- Malformed archive rows/claims removed; N/A replaced with NOT_APPLICABLE/UNKNOWN; report/matrix/register/source agree on corrected evidence.
- All other records reconciled.

No implementation.
