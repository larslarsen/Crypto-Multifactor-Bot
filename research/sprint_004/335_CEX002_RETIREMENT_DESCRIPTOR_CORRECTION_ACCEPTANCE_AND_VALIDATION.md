# CEX-002 Retirement Descriptor Correction Acceptance and Validation

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** descriptor-lifetime correction accepted for exact integration and focused validation
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; rejected real store remains untouched
- **Next ticket:** `NONE`

## Accepted correction

The reviewer inspected Grok's Review-334 return once without executing source, Ruff, pytest,
control, or a data command. The exact accepted identities are:

| Path | Accepted SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_gate2_retirement.py` | `468bcbe3640e2e1a4f112f081b0a3a86081d8f6b877f96950156d79948cd154e` | 1,867 |
| `tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py` | `62984202d04adcc5a78694bd8152ac786b53cc3e10e9ad955846e6ae216d2505` | 1,479 |

The test source still has 61 test functions. The integrated CLI is byte-identical at SHA-256
`66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6`, 117 lines.
Only the authorized module and test changed among the three retirement-tool paths.

The correction satisfies Review 334:

- the authority-selected receipt and SQLite files are opened no-follow after acquiring the
  lock but before inventory, registered with the operation descriptor set, and retained for
  the full inspect/retire lifetime;
- the nested receipt traversal validates each directory component no-follow and the leaf as a
  regular file;
- after the replacement hook, each exact name is reopened and proved to have the same device
  and inode as its held descriptor, while that held descriptor is checked against the scanned
  inventory entry and used for semantic proof;
- lock lstat is no-follow, symlink and special-file failures are explicit, and the no-follow
  open is nonblocking so a type-replacement race cannot hang on a FIFO; and
- the three replacement fixtures create a simultaneous sibling, prove its inode differs, set
  exact content/mode, and atomically replace the target.

The authority constants, CLI behavior, lock lifetime, atomic no-replace transition, durability,
post-proof, schemas, standard-library-only boundary, and unrelated tests are preserved. Static
inspection found no non-ASCII or over-ceiling lines. No command or test result is accepted yet.

## Hermes integration and validation

Hermes owns one exact integration and focused validation round. Preserve every unrelated
modified or untracked path. Do not invoke the retirement CLI or inspect, rename, create within,
delete, or otherwise touch `data/cex002_qualify/gate2` or
`data/cex002_qualify/gate2_retired`.

Preproof must establish:

- `HEAD == origin/main`, Review 335 is present, and Review-334 publication commit
  `51ea5469af16f9aec32aba0a3488d107e0936d06` is an ancestor of `HEAD`;
- the exact accepted module/test hashes, line counts, and 61 test functions above;
- unchanged CLI SHA-256
  `66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6`;
- exactly the module and test are modified among the three retirement-tool paths, with no
  staged path and no `.git/index.lock`; and
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, Reviews 330-335, and the
  Review-330 authority JSON are clean.

Do not inspect the real data tree during preproof. Any failed predicate stops without repair,
reset, restore, checkout, stash, staging, test, or rerun. On success:

1. use the execution platform's explicit escalation/approval mechanism for every Git write;
2. stage only the accepted module and test;
3. prove the exact two-path cached set and run `git diff --cached --check` once;
4. commit with message `fix CEX-002 retirement descriptor continuity` and push `main`;
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
