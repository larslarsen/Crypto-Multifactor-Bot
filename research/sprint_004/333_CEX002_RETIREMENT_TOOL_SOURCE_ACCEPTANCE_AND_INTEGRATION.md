# CEX-002 Retirement Tool Source Acceptance and Integration

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** complete retirement tool accepted for exact integration and focused validation
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; rejected real store remains untouched
- **Next ticket:** `NONE`

## Accepted source

The reviewer inspected Spark's Review-332 return once without executing the tool, Ruff, pytest,
control, or a data command. The exact accepted identities are:

| Path | Accepted SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_gate2_retirement.py` | `8e74a6f984ea2ec61a7e2b459e8e8f6c61c199ef5f9233208ac6ea92599bc344` | 1,823 |
| `scripts/research/retire_binance_usdm_harmonic_gate2.py` | `66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6` | 117 |
| `tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py` | `d727ab7e32d204912d21a41884e73b52fdd4be7566a44dee3d750db036228663` | 1,470 |

The test source has 61 test functions. The module is byte-identical to the senior source
accepted by Review 332. Spark made exactly the three authorized mechanical corrections in the
CLI and test: closed-output `ValueError` is bounded with the existing write/flush failures,
the corrupt-SQLite assertion accepts the bounded SQLite failure contract, and retirement
flush failure has the symmetric indeterminate-result test. Only these three untracked paths
are accepted; unrelated dirty work remains outside this review.

The accepted implementation remains a standalone, standard-library-only transaction. It binds
the exact Review-330 authority, opens authority-matched receipt and SQLite descriptors without
following links, proves immutable/query-only SQLite state, holds the acquisition lock, rebinds
active/parent/destination names around atomic no-replace rename, establishes required
durability, and completes full post-inventory proof before emitting its receipt. This acceptance
authorizes integration and synthetic validation only. It does not authorize opening the real
store through the CLI.

## Hermes integration and validation

Hermes owns one exact integration and focused validation round. Preserve every unrelated
modified or untracked path. Do not invoke the retirement CLI, import and call its real-store
entry points, or inspect, rename, create within, delete, or otherwise touch
`data/cex002_qualify/gate2` or `data/cex002_qualify/gate2_retired`.

Preproof must establish:

- `HEAD == origin/main`, Review 333 is present, and Review-332 publication commit
  `5e77da68a20a0d889e87ca9ee41616cc073d68e4` is an ancestor of `HEAD`;
- Review-330 authority JSON SHA-256
  `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`;
- the three exact accepted source identities, line counts, and 61 test functions above;
- exactly those three paths are untracked, with no staged path and no `.git/index.lock`;
- accepted acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`, acquisition test
  SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`,
  and acquisition CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`; and
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, and Reviews 330-333 are
  clean.

Do not inspect the real data tree as part of preproof. Any failed predicate stops without
repair, reset, restore, checkout, stash, staging, test, or rerun. On success:

1. use the execution platform's explicit escalation/approval mechanism for every Git write;
2. stage only the three accepted source/CLI/test paths;
3. prove the exact three-path cached set and run `git diff --cached --check` once;
4. commit with message `add CEX-002 Gate-2 retirement tool` and push `main`;
5. run the focused Ruff command exactly once; and
6. only if Ruff passes, run the targeted retirement-tool pytest command exactly once.

```bash
.venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_gate2_retirement.py \
  scripts/research/retire_binance_usdm_harmonic_gate2.py \
  tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py -q --tb=short
```

On any denied permission, Git failure, nonzero result, or timeout, stop without repair, rerun,
later command, evidence edit, or further Git mutation and return the exact first failure. On
two passes, return the integration commit plus each command's exact UTC start/end/elapsed time,
exit status, pass count, and warning summary. Do not create a separate evidence record; the
reviewer will record and route the result.

Do not run repository-wide Ruff, full-suite pytest, control, the retirement CLI, corrected
planning, acquisition, replay, `verify`, qualification, sizing, capacity, or any network/data
command. Real-store inspection/retirement, corrected plan creation, acquisition, later gates,
normalization, catalog, NautilusTrader, Harmonic Trader, experiments, PAPER/LIVE, and
next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
