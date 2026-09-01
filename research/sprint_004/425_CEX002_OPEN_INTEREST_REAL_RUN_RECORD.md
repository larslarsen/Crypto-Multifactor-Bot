# CEX-002 Open-Interest Real-Run Record 425

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Runner directory:** `/tmp/cex002_oi_424_bWtKo4`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m`
- **Source commit:** `75de0967016c98cadecee4378927abd3670328ae`
- **Start UTC:** 2026-09-01T18:59:16Z
- **End UTC:** 2026-09-01T19:03:56Z
- **Duration:** ~4 min 40 sec
- **Shell PID:** 1010533 (start tick 9499261; now exited)
- **Python PID:** 1010614 (start tick 9499273; now exited)
- **Final exit code:** 1
- **Terminal error:** `cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: metrics timestamps are not strictly increasing` raised at `src/cryptofactors/ingest/binance_usdm_open_interest.py:1216` inside `_normalize_open_interest_tree`.

## Prior status poll raced terminal completion

The immediately preceding Hermes continuation (session `20260901_120304_ff3146`) polled this exact runner at **19:03:58Z** and reported it **live**: both PIDs were present in `/proc` (bash sleeping, python in disk-sleep), the cmdline/cwd/commit identities matched, and `runner.json` contained only the launch metadata with no `exit_code`/`end_utc` tail. The runner's recorded `end_utc` is **19:03:56Z**, two seconds earlier. The poll read the runner in the narrow window between the child's exception propagation and the parent shell's `wait` return plus tail append. The poll correctly reported what it saw; it did not trigger the terminal-evidence workflow because the runner had not yet visibly terminated. This continuation re-inspected the same runner after the exit tail and PID teardown were complete, so the terminal workflow now executes.

## Preflight verification

| Check | Result |
|---|---|
| `HEAD == origin/main == 75de0967016c98cadecee4378927abd3670328ae` | verified |
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` 1,441 lines / SHA `898c0a1a…` | verified |
| `scripts/research/normalize_binance_usdm_open_interest.py` 53 lines / SHA `33585315…` | verified |
| `tests/ingest/test_binance_usdm_open_interest.py` 455 lines / SHA `b36aa9e8…` | verified |
| runner.json shell_pid 1010533 / shell_start_tick 9499261 | verified |
| runner.json child_pid 1010614 / child_start_tick 9499273 | verified |
| git diff --check | clean (exit 0) |

## Captured runner logs (read-only)

stdout.log (150 bytes) records the shell header and the final `Exit code: 1` / `End UTC: 2026-09-01T19:03:56Z`. stderr.log (1,417 bytes) captures the exact traceback:

```
Traceback (most recent call last):
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 53, in <module>
    raise SystemExit(main())
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 25, in main
    result = normalize_from_authorities(...)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 1434, in normalize_from_authorities
    return _normalize_open_interest_tree(...)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 1216, in _normalize_open_interest_tree
    _require(previous_time is None or moment > previous_time, "metrics timestamps are not strictly increasing")
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 194, in _require
    raise OpenInterestNormalizationError(message)
cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: metrics timestamps are not strictly increasing
```

## Hidden-output facts (read-only, no reconciliation)

`data/.cex002_open_interest_5m` **exists** and contains partial, unreferenced output (5,425,125 bytes, 14 files):

- `.partitions/0GUSDT/` — 7 Parquet files, one symbol (0GUSDT), months 2025-09 through 2026-03, total 5,347,048 bytes:
  - 2025-09: 365,680 bytes (`53998ec1…`)
  - 2025-10: 847,071 bytes (`2b7d06d6…`)
  - 2025-11: 832,841 bytes (`9dca8704…`)
  - 2025-12: 852,312 bytes (`db8342f9…`)
  - 2026-01: 851,153 bytes (`e3604b90…`)
  - 2026-02: 763,270 bytes (`ac35aade…`)
  - 2026-03: 834,721 bytes (`95ff7a3a…`)
- `.lineage/0GUSDT/` — 7 matching JSON lineage files, total 78,077 bytes.
- `.staging/` — empty (0 files).
- No completion descriptor, no accepted completion artifact, no other symbol.

The normalizer published the seven 0GUSDT months and then failed the strictly-increasing timestamp assertion on a subsequent row. The output is therefore partial: one symbol of an eleven-product contract, with no durable completion descriptor and no authority/lineage reconciliation. It is evidence, not an accepted product.

## No patch, cleanup, retry, or product claim

Per Review 424 this record states the exact terminal error, the prior poll race, and the partial unreferenced output facts. No source/test/CLI patch, data cleanup, re-run, reproduction, catalog mutation, NautilusTrader check, or next-ticket work is authorized. Both `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` have their next-required-actor fields returned to the reviewer. Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`; next ticket remains `NONE`.
