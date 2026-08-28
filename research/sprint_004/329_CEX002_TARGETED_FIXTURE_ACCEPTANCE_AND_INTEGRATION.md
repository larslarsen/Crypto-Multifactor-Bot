# CEX-002 Targeted Fixture Acceptance and Integration

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Spark fixture correction accepted for integration and one targeted rerun
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Source review

The reviewer inspected Spark's review-328 return once. The only diff is the authorized
three-line assignment inside
`test_wrong_retained_byte_count_is_rejected_before_plan_publication`:

```python
document["physical_inputs"]["retained_credit"]["report_summary"][
    "retained_verified_credit_bytes"
] = 1
```

It follows the two existing assignments which set the primary and physical retained byte
counts to `1`; the intended `AuthorityError` assertion and every other byte are preserved.
The accepted test identity is:

- SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`;
- 5,676 lines; and
- 203 test functions.

The integrated production source and unchanged CLI remain accepted at:

- acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`; and
- CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`.

## Hermes authorization

Hermes must perform only this bounded integration and validation:

1. Prove `HEAD == origin/main`, Review 329 is present, commit
   `082d1490df83104de0cb4c426c8850e414d02b26` is an ancestor of `HEAD`, the three accepted
   hashes match, only the acquisition test is modified among those paths, the index is empty,
   and `.git/index.lock` is absent.
2. Use the execution platform's explicit escalation/approval mechanism for Git writes. Stage
   only `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`.
3. Prove the exact cached one-path set and run `git diff --cached --check` once.
4. Commit with message `fix CEX-002 retained byte fixture` and push `main`.
5. Run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

Any failed predicate, denied permission, Git failure, nonzero result, or timeout stops without
repair, rerun, later command, or record edit. On success, return the integration commit, exact
start/end/elapsed time, exit status, pass count, and warning summary. Do not create a separate
evidence record for this rerun; the reviewer will record and route the accepted result.

Do not run Ruff again: focused Ruff passed before the only accepted change, which is the
reviewed formatting-only fixture assignment above. Do not touch production source, CLI,
governance, unrelated dirty work, ignored state/data, or the rejected Gate-2 store.

Full-suite/repository validation, control, old-store retirement, corrected planning,
acquisition, replay, `verify`, qualification, sizing, capacity, network/data mutation, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, experiments, PAPER/LIVE, and
next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
