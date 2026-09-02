# CEX-002 Record 469 — Funding Integration Stopped at pytest

- **Date:** 2026-09-02
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Review:** 468
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` — four of eleven required products accepted
- **Next required actor:** reviewer disposition
- **Next ticket:** `NONE`

## Preproof

- `HEAD == origin/main == 93636067a7ab4aabcbc5d9708654c75cd4012718` (proved).
- Three accepted hashes and line counts reproved exactly:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_funding_realized.py` | 1,404 | `4e38658f89905e1f5b66b739eb8f58e2f66ce204b9c61cfbfa7cb0ed161acada` |
| `scripts/research/normalize_binance_usdm_funding_realized.py` | 50 | `05e30c8712608e4895749114375a9b38ea5cf868870d913ddef5d264f77d7b2b` |
| `tests/ingest/test_binance_usdm_funding_realized.py` | 905 | `f7cdb6c443f7bb334d947adb376819d27fd03a35202c9bdecd52bf365ce05559` |

## First nonzero result — pytest

Review 468 ordered commands:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_funding_realized.py scripts/research/normalize_binance_usdm_funding_realized.py tests/ingest/test_binance_usdm_funding_realized.py
python3 scripts/check_repo_control.py
```

The first command exited 1. Exact terminal evidence:

```
................................................................F.       [100%]
=================================== FAILURES ===================================
________________ test_missing_or_nonpositive_sidecar_bytes_fail ________________
tests/ingest/test_binance_usdm_funding_realized.py:887: in test_missing_or_nonpositive_sidecar_bytes_fail
    with pytest.raises(funding.FundingNormalizationError, match="reachable|missing"):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE FundingNormalizationError
=========================== short test summary info ============================
FAILED tests/ingest/test_binance_usdm_funding_realized.py::test_missing_or_nonpositive_sidecar_bytes_fail
```

The test `test_missing_or_nonpositive_sidecar_bytes_fail` at `tests/ingest/test_binance_usdm_funding_realized.py:887` expects `_authenticate` to raise `FundingNormalizationError` matching `reachable|missing` when called with `write=False` (sidecar file absent from disk). It did not raise.

## Stop

Per Review 468, Hermes stops on the first nonzero result. The second (ruff) and third (check_repo_control.py) commands were NOT executed. No integration commit, push, staging, or real run occurred. The three developer paths remain untracked and untouched. No data was downloaded or mutated. No partial artifacts exist.

Record 469 is published. Both actor fields return to the Lead Quantitative Finance Researcher/Engineer for disposition of the pytest failure. Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.
