# CEX-002 Claude Authority Test Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/165_CEX002_CLAUDE_AUTHORITY_RESIDUAL_REVIEW.md`

## Reviewed source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a6e7e7891d78ea857f22b6d35cf622ed36985d97c27790f3569a787492a54803` | test-only correction required |

The test path contains 305 unique `test_` function definitions. The three reviewed paths
are whitespace-clean. The reviewer ran no test, Ruff, repository-control, network/data,
transaction, migration, or ordinary qualification command.

## Decision

**ACCEPT AND FREEZE THE PRODUCTION SOURCE-AUTHORITY TRANSACTION; REJECT ONLY TWO BROKEN
TEST-ACCOUNTING CONSTRUCTIONS; AUTHORIZE ONE MECHANICAL SPARK TEST CORRECTION.**

The production residual now normalizes the preserved checkpoint envelope, pins retained
evidence beneath the accepted store, proves the full advanced ledger and completed lock
transforms in both directions, rejects corrupt content-address collisions before mutation,
and implements the reviewed ledger-first/lock-last recovery transaction. The CLI remains
byte-identical to review 165. Those paths are accepted and frozen.

Hermes remains unauthorized because the source tests cannot yet reach the accepted-state
fixture or prove the altered-accounting rejection.

## Findings

### 1. The accepted-state fixture searches for an impossible uncharged download

`_accepted_v4_state()` executes the complete synthetic version-4 plan successfully and
loads its amendment ledger. It then calls `next()` for a download absent from
`ledger.charges`. Every synthetic object is available and valid, so the acquisition loop
settles every planned download. The existing migrated-resume test already establishes the
resulting empty reservation set. The new fixture therefore raises `StopIteration` before
any source-correction test reaches the transaction.

Construct the crash-state reservation from an existing settled transfer: select one
charged entry, remove it from `charges`, place its exact positive `planned_bytes` in
`reservations`, flush, and assert that both collections remain nonempty. This mirrors the
repository's existing `_outstanding_reservation()` fixture and preserves valid reviewed
accounting without inventing an unplanned key.

### 2. The altered-accounting mixed state is a no-op with the corrected fixture

The `altered_accounting` branch selects an arbitrary planned download and calls
`ledger.reserve()`. `reserve()` deliberately returns without mutation when the key is
already charged or reserved. Because every planned download is accounted, the branch
leaves the completed state unchanged; preflight succeeds and the asserted rejection never
occurs. Its expected `accounting changed` text also no longer matches the exact full-ledger
validator, which rejects with `changed more than its receipt`.

Make a real, self-consistent accounting mutation using an existing charged record, flush
it, and assert the exact full-ledger rejection text. Do not weaken production validation
or fabricate an out-of-plan record.

### 3. Rejected public transitions need explicit no-mutation proofs

The retained-evidence, mixed-state, lock-without-receipt, and completed-state tamper tests
mostly call the read-only preflight directly, or merely assert that the lock still exists.
Review 165 required failure-before-mutation coverage for each rejected public transition.
After each test creates its rejected state, capture `_correction_snapshot()`, invoke
`apply_reviewed_source_correction()`, and assert the snapshot is byte-identical after the
expected exception. The corrupt-content-address test already has this shape and remains
unchanged.

## Spark test-only authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, and only the following
existing source-correction test regions:

1. `_accepted_v4_state()`: convert one existing settled transfer into one exact outstanding
   reservation and prove both charges and reservations are nonempty;
2. `test_source_correction_refuses_every_mixed_state`: make `altered_accounting` perform a
   real valid accounting change and expect `changed more than its receipt`; and
3. the existing retained-evidence, mixed-state, lock-without-receipt, and completed-state
   rejection tests: exercise the public apply function and assert byte-identical snapshots
   around each expected failure.

Every other test byte and all production/CLI bytes remain frozen. Spark adds no test,
changes no test name or function count, runs no command, test, Ruff, network/data operation,
transaction, Git operation, or record edit, and returns only the exact test SHA-256 plus
confirmation that the unique test-function count remains 305. Hermes remains unauthorized
pending reviewer source acceptance.

## Boundaries

No production or CLI edit, integration, live source-authority transaction, ordinary
resume, reservation reconciliation, Gate-1 acceptance, sizing, Gate 2, bulk acquisition,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
