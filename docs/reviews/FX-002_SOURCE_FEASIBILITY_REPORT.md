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

All raw in /tmp/fx_002_raw (not committed).

## Mechanical Preflight (literal)

Command: `set -o pipefail; rg -n 'CSV|cat |heredoc|>>|<<|printf|echo ' research/fx_002/ | cat; echo $?`

Output:
1

## Per Provider (exact from captures)

### Kraken

- Fixed SHA to actual 6ea3d7bbb01f808e8c5c2f21d1fabf7acfb19a574e4ad5c0f41676c4a4123a95 in register, report, and source note.
- Historical: no.
- Direct USD anchor: yes.
- Recommend: NONE

### Coin Metrics

- Used correct /v4/catalog/asset-metrics (not /catalog/assets).
- Unauthorized.
- No USD price metric identified.
- Recommend: NONE

### DefiLlama

- Current snapshot only.
- No historical.
- Recommend: NONE

### Binance

- Direct symbols captured: USDTUSD (base=USDT, quote=USD), USDCUSD (base=USDC, quote=USD).
- Rate direction: USD per USDT / USD per USDC.
- Archive: 404 NoSuchKey for daily klines objects on all tested dates including 2022-05-01 depeg window.
- No historical depth, no depeg sample, no PIT, no revisions.
- Fiat USD semantics: UNKNOWN (no explicit definition located in captured official docs).
- Live symbol info reproducible.
- Recommend: NONE

## Decision Matrix

See `research/fx_002/decision_matrix.csv` (new schema with rate_direction, source_status, recommendation)

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
   =============================== warnings summary ===============================
   tests/test_archives.py::test_duplicate_member_names
     /home/lars/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/zipfile/__init__.py:1661: UserWarning: Duplicate name: 'a.csv'
       return self._open_to_write(zinfo, force_zip64=force_zip64)

   -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

(Note: exact command with -q produces dots to 100% and warnings summary; no additional "N passed in Xs" line emitted.)

## Records

- Previous FX-002_JR_FINAL_EVIDENCE_RECOVERY_TASK.md marked FAILED - REVIEW-0085.
- This task marked COMPLETED.
- FX-002 set to AWAITING_REVIEW.
- FX-001 remains ACCEPTED.
- All other records (README, backlog, handoff, report) reconciled.
- New captures and repairs per REVIEW-0085 and the audit task.

No implementation.
