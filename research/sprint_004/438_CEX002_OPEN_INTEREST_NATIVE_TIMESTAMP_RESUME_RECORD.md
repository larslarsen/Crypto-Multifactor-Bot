# CEX-002 Record 438 — Review-437 preserved-root resume; unobserved terminal launch failure

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Review-437 resume produced an unobserved terminal launch failure with zero output mutation; record only, no retry
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Integration commit and checks

Hermes proved `HEAD == origin/main == 4a65179e6cd0938a86a556eb0c7f755ab3e283be` and re-ran Review 437's four ordered checks in sequence, stopping on the first nonzero result. All four passed:

| # | Command | Result |
|---|---:|---|
| 1 | `.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short` | 55 passed |
| 2 | `.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py` | All checks passed |
| 3 | `python3 scripts/check_repo_control.py` | PASS |
| 4 | `git diff --check -- src/cryptofactors/ingest/binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py` | clean |

The exact two source/test paths remain unstaged and untouched at the integration commit.

## Preserved hidden-root facts

`data/.cex002_open_interest_5m` before and after the launch attempt contains exactly 181 Parquets plus 181 matching lineage JSON files, an empty `.staging` directory, and no completion descriptor. The last published partition is `1000FLOKIUSDT/2024-03`. No mutation occurred.

## Accepted capacity equation

The unchanged complete-archive sizing proof:

```text
160,226,578 authenticated physical rows
-    75,255 byte-identical repeated physical rows
-     2,818 adjacent-next-midnight spillover rows
= 160,148,505 expected product rows
```

Available space is 99,645,513,728 bytes against the unchanged conservative 55,415,363,427-byte requirement. The equation remains sufficient.

## Sole runner identity

The single runner started at `2026-09-01T21:26:20Z` in `/tmp/cex002_oi_437_XAHLxl`. The shell PID was 1088968 with start tick 10381675. The Python PID was 1089049 with start tick 10381691. Hermes observed the live runner at about 25 seconds after launch.

The production command was:

```text
PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src
/home/lars/Crypto_Multifactor_Bot/.venv/bin/python
/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py
--generation0-state data/cex002_qualify/gate2/state.sqlite
--generation0-content-root data/cex002_qualify/gate2/content
--v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
--recovery-root data/cex002_recovery
--output-root data/.cex002_open_interest_5m
```

## Terminal outcome — unobserved launch failure

Immediately after the harness returned, both exact PIDs were independently absent: no matching process exists for shell PID 1088968 or Python PID 1089049. The `stdout.log` file is exactly 0 bytes with mtime frozen at launch (2026-09-01T21:26:20Z). No durable exit code or end timestamp exists. No terminal status was written.

This is an unobserved terminal launch failure with zero output mutation, not a normalizer or data diagnosis. The hidden output remains exactly 181 Parquets plus 181 lineages, empty staging, no completion descriptor.

## Supervisor deviations (factual)

1. **`metadata.json` omitted durable Python identity.** The JSON records `shell_pid` and `shell_start_tick` only; it does not record the Python PID or Python start tick despite `child_pid.txt` holding that value separately.
2. **stdout and stderr were merged.** `supervisor.sh` uses `> "$RUNNER/stdout.log" 2>&1`, combining both streams into one file.
3. **`supervisor.sh` ended with `wait` redirected and wrote no terminal status.** The final line `wait 2>/dev/null` blocks on the detached child but never writes an exit code, end timestamp, or terminal descriptor to the runner directory.
4. **The detached lifecycle did not survive.** Despite `nohup setsid` and closed stdin, neither the shell nor the Python process remained observable after the harness returned; the detached session did not persist as a durable background process.

## Result

Record 438 is published at the integration commit. Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. Next ticket remains `NONE`. Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`. No source/test/CLI patch, retry, reproduction, cleanup, or next ticket is authorized.
