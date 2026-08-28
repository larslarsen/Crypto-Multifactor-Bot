# CEX-002 Retirement Validation Acceptance and Execution Authorization

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** validated tool accepted; one exact real retirement invocation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; retirement is preservation, not Gate-2 acceptance
- **Next ticket:** `NONE`

## Accepted validation

Hermes integrated and pushed the exact Review-335 module/test correction at commit
`56ad85c251cee2f22514fb2364f85c308bf0eb46`. The owner relayed successful completion of
Review 335's focused Ruff and targeted synthetic retirement-tool suite. Under the repository's
one-way control plane, the relay owner is not required to reconstruct a separate execution
report. The reviewer accepts the relayed result without rerunning either command.

Repository inspection proves `HEAD == origin/main` at that integration commit and the exact
validated identities:

- retirement module SHA-256
  `468bcbe3640e2e1a4f112f081b0a3a86081d8f6b877f96950156d79948cd154e`;
- retirement CLI SHA-256
  `66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6`; and
- retirement test SHA-256
  `62984202d04adcc5a78694bd8152ac786b53cc3e10e9ad955846e6ae216d2505`.

The complete standalone retirement tool is accepted. This does not accept the rejected plan
or authorize corrected planning or acquisition.

## Direct retirement decision

Do not run a separate real `inspect` command. The `retire` path performs the same complete
authority, inventory, lock, receipt, immutable SQLite, and zero-fact proof before it can create
the retirement parent or rename anything. A separate inspection would read and hash the
742,380,087-byte tree redundantly without strengthening the atomic transaction.

ADR-0030 now authorizes exactly one transition from:

`data/cex002_qualify/gate2`

to:

`data/cex002_qualify/gate2_retired/fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`

This is preservation of rejected pre-network state, not deletion, migration, or evidence
acceptance.

## Hermes execution authorization

Hermes owns one exact real retirement invocation and its execution record. Preserve all
unrelated modified and untracked paths.

Repository-only preproof must establish:

- `HEAD == origin/main`, Review 336 is present, and integration commit
  `56ad85c251cee2f22514fb2364f85c308bf0eb46` is an ancestor of `HEAD`;
- the three exact validated tool identities above;
- Review-330 authority JSON SHA-256
  `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`;
- accepted acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`, acquisition test
  SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`,
  and acquisition CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path and no `.git/index.lock`; and
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, Reviews 330-336, and the
  Review-330 authority JSON are clean.

Do not stat, list, hash, open, or otherwise inspect either real Gate-2 path during preproof. The
tool owns every data predicate under its held lock. Any failed repository predicate stops
without repair, reset, restore, checkout, stash, data access, invocation, or rerun.

On preproof success, record exact UTC start time, invoke exactly once from repository root, and
capture complete stdout/stderr, exact UTC end time, elapsed time, and exit status:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/research/retire_binance_usdm_harmonic_gate2.py retire \
  --confirm fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3
```

Do not wrap the command in an external timeout: termination during or after rename would
destroy the tool's bounded transition semantics. Do not retry for any exit status.

After an actual invocation returns, create exactly:

- `research/sprint_004/337_CEX002_REJECTED_GATE2_RETIREMENT_EXECUTION.md`.

Record the repository commit, exact tool/authority identities, exact command, UTC timing,
elapsed time, exit status, and complete bounded stdout/stderr. On exit 0, include the emitted
canonical retirement receipt verbatim in a JSON code block. On exit 2 or 3, include the complete
bounded error and explicitly state that no inspection, cleanup, reverse rename, retry, or second
transition followed. Do not derive or claim any filesystem state beyond the tool's output.

Use explicit Git-write escalation. Stage only record 337, prove that exact cached one-path set,
run `git diff --cached --check`, commit with message
`record CEX-002 rejected Gate-2 retirement`, push `main`, and stop for review. If record or Git
publication fails, do not rerun or inspect the data operation; return the already-captured
result and the publication failure.

Do not run real `inspect`, Ruff, pytest, control, corrected `plan`, `acquire`, replay, `verify`,
qualification, sizing, capacity, or any network command. Do not manually create, rename, copy,
delete, repair, or inspect either Gate-2 path. Corrected planning, acquisition, later gates,
normalization, catalog, NautilusTrader, Harmonic Trader, experiments, PAPER/LIVE, and
next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data, and
unrelated dirty work are excluded.
