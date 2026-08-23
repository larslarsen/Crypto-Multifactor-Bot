# CEX-002 V3 Corrected Sizing Execution

- **Date:** 2026-08-23
- **Ticket:** CEX-002
- **Authorized actor:** Jr Dev — Hermes
- **Reviewer authorization:** `research/sprint_004/271_CEX002_V3_TEST_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
- **Outcome:** BLOCKED before Ruff and sizing; focused pytest failed
- **Gate 2:** not accepted

## Preproof and integration

| Check | Result |
|---|---|
| `HEAD` | `0ce5e9a221aed6fec5cc7d905c0baa8992a8aa5a` |
| `origin/main` | `0ce5e9a221aed6fec5cc7d905c0baa8992a8aa5a` |
| production SHA-256 | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` |
| accepted test SHA-256 | `f67851a952bc5fdacf5a951344f119e0efd721d47974af0f6f1424449299777c` |
| CLI SHA-256 | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |
| test function count | `161` |
| receipt 258 | absent |
| v3 Parquet evidence | absent |
| accepted manifest detail | present |

Only the accepted test path was staged. Unrelated dirty work was left untouched.

## Corrected validation command

The exact command authorized by review 271 was run once. The command wrapper reported
17.1 seconds elapsed and exit status `1`; it did not emit start/end timestamps. The
end-of-record UTC observation was `2026-08-23T23:29:57Z`.

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Observed output:

```text
........................................................................ [ 23%]
........................................................................ [ 47%]
........................................................................ [ 70%]
..........................................................F............. [ 94%]
..................                                                       [100%]
=================================== FAILURES ===================================
_________________ test_the_v3_capacity_terms_reconcile_exactly _________________
tests/acquisition/test_binance_usdm_harmonic_sizing.py:6272: in test_the_v3_capacity_terms_reconcile_exactly
    domain = liquidation["identity_domain"]
             ^^^^^^^^^^^
E   UnboundLocalError: cannot access local variable 'liquidation' where it is not associated with a value
=========================== short test summary info ============================
FAILED tests/acquisition/test_binance_usdm_harmonic_sizing.py::test_the_v3_capacity_terms_reconcile_exactly
```

The command collected 161 test functions and had one failure. Because focused pytest
exited nonzero, review 271 requires stopping immediately. Ruff, both real v3 sizing
invocations, receipt 258, v3 envelope publication, and idempotence were not run.
No sizing, acquisition, normalization, catalog, NautilusTrader, Harmonic Trader,
PAPER, LIVE, or next-ticket work occurred.

## Evidence and authority

No receipt SHA-256, receipt byte length, envelope count, capacity equation, or v3
evidence manifest exists from this attempt. Receipt 258 remains absent. Gate 2 remains
not accepted and the next ticket remains `NONE`.
