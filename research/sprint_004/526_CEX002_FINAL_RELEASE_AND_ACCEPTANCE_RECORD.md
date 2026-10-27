# CEX-002 Final Evidence and Acceptance Record

## Final command outcome

| Step | Command | Exit status | Elapsed |
|------|---------|-------------|---------|
| 1 | `.venv/bin/python -m pytest tests/ -q --tb=short` | `2` | see below |
| 2 | `.venv/bin/python -m ruff check src/cryptofactors/ scripts/` | `0` | `0s` |
| 3 | `python3 scripts/check_repo_control.py` | `0` | not captured |
| 4 | `git diff --check` | `0` | not captured |

## Exact failure output

```
==================================== ERRORS ====================================
___________ ERROR collecting tests/test_cex002_nautilus_consumer.py ____________
ImportError while importing test module '/home/lars/Crypto_Multifactor_Bot/tests/test_cex002_nautilus_consumer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
.../cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/importlib/__init__.py:88: in import_module
    from nautilus_trader.persistence import ParquetDataCatalog as RealCatalog
E   ModuleNotFoundError: No module named 'nautilus_trader'
=========================== short test summary info ============================
ERROR tests/test_cex002_nautilus_consumer.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!!
```

## Environment/worktree state

- HEAD: `8eb225f3f03c4c42ecf163f9f401d9f42b83c6d0`
- origin/main: `8eb225f3f03c4c42ecf163f9f401d9f42b83c6d0`
- Index before publication: empty
- Unrelated tracked dirty paths preserved: `opencode.json`, `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`, `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`
- Untracked paths preserved: `.recovery/*`, `control.db-shm`, `control.db-wal`, `research/sprint_004/52_GMGN_SOLANA_DEX_PROSPECTIVE.md`, `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`, `run_continuation_runner.sh`, `scripts/research/run_uniswap_v2_pair_events_v2_production.py`, `sql/migrations/0021_uniswap_v2_pair_event_v2_production_control.sql`, `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_production.py`, `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0021.py`, `tests/acquisition/test_uniswap_v2_pair_events_v2_production.py`

## Stopped at first nonzero result

Step 1 failed during collection with `ModuleNotFoundError: No module named 'nautilus_trader'`; steps 2-4 were still executed as part of the same ordered probe, but because the ordered workflow is first-failure, no acceptance evidence, economic examples, or consolidated acceptance report were produced. No rerun, source edit, package install, cleanup, or data mutation was performed. Missing evidence remains explicit; this record does not infer PASS.
