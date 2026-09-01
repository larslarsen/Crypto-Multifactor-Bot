# CEX-002 Record 418 — Open-Interest Integration Lint Stop

- **Date:** 2026-09-01
- **Ticket:** CEX-002
- **Review:** 417
- **Outcome:** integration stopped at lint; no real run; no source integration

## Publication context

Review 417 accepts the corrected three-path `binance_usdm_open_interest_5m`
production/test drop for Hermes integration and one real production run. The
accepted identities are:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,432 | `c2b8835445036359e870cb6a3fa77907bc9ec766a2e1da355ef837e7c22a70d8` |
| `scripts/research/normalize_binance_usdm_open_interest.py` | 53 | `33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 440 | `aee598c17cbd7fc2c4835a924c03fc4f0e9cc3570b68da20c02706b39afd92b0` |

## Proved identities at publication commit

```text
$ git rev-parse HEAD origin/main
1c565f8217a1e10c4c031cc3bf1bb43a948a9ac5
1c565f8217a1e10c4c031cc3bf1bb43a948a9ac5
```

```text
$ wc -l src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
1432 src/cryptofactors/ingest/binance_usdm_open_interest.py
   53 scripts/research/normalize_binance_usdm_open_interest.py
  440 tests/ingest/test_binance_usdm_open_interest.py
```

```text
$ sha256sum src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
c2b8835445036359e870cb6a3fa77907bc9ec766a2e1da355ef837e7c22a70d8  src/cryptofactors/ingest/binance_usdm_open_interest.py
33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675  scripts/research/normalize_binance_usdm_open_interest.py
aee598c17cbd7fc2c4835a924c03fc4f0e9cc3570b68da20c02706b39afd92b0  tests/ingest/test_binance_usdm_open_interest.py
```

`HEAD == origin/main == 1c565f8`. All three accepted hashes and line counts
reproved exactly.

## Ordered integration checks (Review 417, in order, stop on first nonzero)

### 1. Targeted pytest — passed

```text
$ .venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
...................................                                      [100%]
35 passed in 0.17s
```

Exit 0. All 35 cases passed.

### 2. Targeted ruff — failed, F841

```text
$ .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
tests/ingest/test_binance_usdm_open_interest.py:222:13: F841 Local variable `key` is assigned but unused
```

Exit 1. The lint gate failed at `tests/ingest/test_binance_usdm_open_interest.py`
line 222 because local variable `key` is assigned but unused (F841).

### 3. Repository control — not run

`python3 scripts/check_repo_control.py` was not executed because the lint gate
failed first. Review 417 requires stopping on the first nonzero result.

## Honest stop

Per Review 417, a failure is published honestly and stops before the real run.
The integration stopped at the lint gate. No patch, source edit, cleanup, or
real normalization run was launched. The repository-control check was not run.
No durable `/tmp` runner was created. No output was written. The three accepted
developer paths remain unintegrated and unstaged.

## State after this record

- Gate 2 remains `ACCEPTED`.
- Gate 3 remains `IN_PROGRESS`.
- Next required actor: Lead Quantitative Finance Researcher/Engineer.
- Next ticket: `NONE`.
- Source/test remains unintegrated and unstaged.
- No real runner/output exists.
- All unrelated dirty paths preserved.
