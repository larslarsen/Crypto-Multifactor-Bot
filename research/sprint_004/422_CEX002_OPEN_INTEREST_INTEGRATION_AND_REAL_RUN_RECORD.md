# CEX-002 Open-Interest Integration and Real-Run Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Runner directory:** `/tmp/cex002_oi_421_I7Ov28`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m`
- **Start UTC:** 2026-09-01T18:39:30Z
- **End UTC:** 2026-09-01T18:41:24Z
- **Duration:** ~114 seconds
- **Shell PID:** 998815 (launcher, now exited)
- **Shell start tick:** 9380595
- **Python PID:** 998897 (recorded in runner; now exited)
- **Python start tick:** 9380609
- **Final exit code:** 1
- **stdout/stderr:** empty (process output was not captured through the detached pipe)
- **data/.cex002_open_interest_5m:** absent (no output directory created)

## Preflight verification

| Check | Result |
|---|---|
| `HEAD == origin/main == 99b4729` | verified |
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` 1432 lines / SHA `c2b88354…` | verified |
| `scripts/research/normalize_binance_usdm_open_interest.py` 53 lines / SHA `33585315…` | verified |
| `tests/ingest/test_binance_usdm_open_interest.py` 439 lines / SHA `4c6d796e…` | verified |
| `data/.cex002_open_interest_5m` absent | verified |
| `df -BG /` available | 103 G (≥100 GiB pass) |
| `state.sqlite` present | yes |
| `v3 manifest` present | yes |

## Ordered integration checks (all pass before real run)

1. `.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short`
   - Result: `................................... [100%]` — **PASS** (35/35)
2. `.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py`
   - Result: `All checks passed!` — **PASS**
3. `python3 scripts/check_repo_control.py`
   - Result: **PASS** (not recorded above — see runner records)

## Real-run failure

Foreground reproduction of the exact command fails identically:

```
Traceback (most recent call last):
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 53, in <module>
    raise SystemExit(main())
  File "scripts/research/normalize_binance_usdm_open_interest.py", line 25, in main
    result = normalize_from_authorities(...)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 1420, in normalize_from_authorities
    sources = load_generation0_sources(generation0_state, generation0_content_root)
  File "src/cryptofactors/ingest/binance_usdm_open_interest.py", line 609, in load_generation0_sources
    _require(str(state) == "checksum_verified", "generation-0 metrics completion is not checksum verified")
cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: generation-0 metrics completion is not checksum verified
```

This is a precondition failure in the normalizer: the persisted generation-0 metrics state is not `checksum_verified`. It is not a source-network, capacity, or authority defect — the state store disagrees with its own checksum invariant. No output was written; no mutation occurred. The hidden output root was never created.

## No patch, cleanup, retry, or product claim

Per Review 421 this record states the exact terminal error and the absence of output. No source/test patch, data cleanup, re-run, catalog mutation, NautilusTrader check, or next-ticket work is authorized. Both `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` have their next-required-actor fields returned to the reviewer.
