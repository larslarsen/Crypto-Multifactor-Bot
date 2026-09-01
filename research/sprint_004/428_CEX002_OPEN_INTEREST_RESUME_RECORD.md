# CEX-002 Open-Interest Resume Record 428

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Runner directory:** `/tmp/cex002_oi_427_yZ3DpH`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m`
- **Source commit:** `683b5b7e16185e58ab79f351cdb47d28f66692fb`
- **Start UTC:** 2026-09-01T19:31:01Z
- **End UTC:** 2026-09-01T19:35:40Z
- **Duration:** ~4 min 39 sec
- **Shell PID:** 1030387 (start tick 9689740; now exited)
- **Python PID:** 1030470 (start tick 9689757; now exited)
- **Final exit code:** 1
- **Terminal error:** `cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: metrics row lies outside its source contract-day` raised at `src/cryptofactors/ingest/binance_usdm_open_interest.py:831` inside `_row_values`, called from `_normalize_open_interest_tree` at line 1209.

## Preflight verification

| Check | Result |
|---|---|
| `HEAD == origin/main == 683b5b7e16185e58ab79f351cdb47d28f66692fb` | verified |
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` 1,448 lines / SHA `b1ae591e…` | verified |
| `scripts/research/normalize_binance_usdm_open_interest.py` 53 lines / SHA `33585315…` | verified |
| `tests/ingest/test_binance_usdm_open_interest.py` 491 lines / SHA `b597b69e…` | verified |
| runner.json shell_pid 1030387 / shell_start_tick 9689740 | verified |
| runner.json child_pid 1030470 / child_start_tick 9689757 | verified |

## Captured runner logs (read-only)

stdout.log (43 bytes) records the final `Exit code: 1` / `End UTC: 2026-09-01T19:35:40Z`. stderr.log (1,605 bytes) captures the exact traceback:

```
Traceback (most recent call last):
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 53, in <module>
    raise SystemExit(main())
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 25, in main
    result = normalize_from_authorities(...)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 1441, in normalize_from_authorities
    return _normalize_open_interest_tree(...)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 1209, in _normalize_open_interest_tree
    _row_values(source, raw_ref, ordinal, raw_row)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 831, in _row_values
    _require(row_date == economic_date, "metrics row lies outside its source contract-day")
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 194, in _require
    raise OpenInterestNormalizationError(message)
cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: metrics row lies outside its source contract-day
```

## Hidden-output facts (read-only, no reconciliation)

`data/.cex002_open_interest_5m` **exists** and contains partial, unreferenced output (16 files):

- `.partitions/0GUSDT/` — 8 Parquet files, one symbol (0GUSDT), months 2025-09 through 2026-04:
  - 2025-09: 365,680 bytes (`53998ec1…`)
  - 2025-10: 847,071 bytes (`2b7d06d6…`)
  - 2025-11: 832,841 bytes (`9dca8704…`)
  - 2025-12: 852,312 bytes (`db8342f9…`)
  - 2026-01: 851,153 bytes (`e3604b90…`)
  - 2026-02: 763,270 bytes (`ac35aade…`)
  - 2026-03: 834,721 bytes (`95ff7a3a…`)
  - 2026-04: 807,026 bytes (`31c92234…`) ← **new in this run**
- `.lineage/0GUSDT/` — 8 matching JSON lineage files (2025-09 through 2026-04).
- `.staging/` — empty (0 files).
- No completion descriptor, no accepted completion artifact, no other symbol.

The normalizer published eight 0GUSDT months (one more than record 425's seven) and then failed the contract-day bounds assertion on a subsequent row inside `_row_values`. The output remains partial: one symbol of an eleven-product contract, with no durable completion descriptor and no authority/lineage reconciliation. It is evidence, not an accepted product.

## Distinct terminal error from record 425

Record 425 failed on `metrics timestamps are not strictly increasing` at the post-sort continuity check (line 1216). Record 427 fails earlier, inside `_row_values` at line 831, on `metrics row lies outside its source contract-day`. The daily-order correction is therefore not the proximate cause of this halt; the failure is a per-row contract-day bounds assertion that the existing parser does not satisfy on real data.

## No patch, cleanup, retry, or product claim

Per Review 427 this record states the exact terminal error, the distinct failure site from record 425, and the partial unreferenced output facts. No source/test/CLI patch, data cleanup, re-run, reproduction, catalog mutation, NautilusTrader check, or next-ticket work is authorized. Both `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` have their next-required-actor fields returned to the reviewer. Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`; next ticket remains `NONE`.
