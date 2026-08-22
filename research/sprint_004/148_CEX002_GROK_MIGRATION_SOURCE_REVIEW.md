# CEX-002 Grok Migration Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing reviews:

- `research/sprint_004/146_CEX002_CLAUDE_MIGRATION_SOURCE_REVIEW.md`
- `research/sprint_004/147_CEX002_GROK_MIGRATION_CONTINUATION.md`

## Reviewed source

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `8de69c58b13d3b595b6c6e543ff59536d6300437bab0ee907e41dcff777e549e` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `1ac128ee0687fd47f555563aa3b72e9db3d82a791ab0852d31ece4d1276d05fc` |

The test path contains 282 unique `test_` function definitions and `git diff --check` is
clean. The reviewer ran no test, Ruff, migration, candidate, network, or data command.

## Decision

**REJECT THE CONTINUATION BEFORE HERMES INTEGRATION; AUTHORIZE GROK BUILD FOR TWO
RESIDUAL CORRECTIONS.**

Grok closes review 146's ordinary mixed-state fallback, CLI report overwrite, current-
input ordering, exact prior-lock/history proof, full lock/ledger binding comparison, and
locked-key/size/aggregate allowance checks. The real CLI now skips the report writer in
migration mode, the ordinary state classifier runs before inventory or checkpoint
recovery, and current version-4 inputs are rejected before amendment-ledger reconciliation.
These directions should be preserved.

Two explicit authority invariants remain open. The present tests do not cover them, and
one existing migration test is contradicted by the implementation.

## Findings

### P0 - migration-only mode still mutates the sample checkpoint

Migration proceeds through `recover_retained_samples()` at production lines 9349-9355.
That helper calls `checkpoint.record()` for a recoverable retained object, and `record()`
immediately flushes the sample checkpoint. Regardless of recovery, every migration also
reaches the unconditional `checkpoint.flush(updated_at=..., discovered_symbol_count=...)`
at lines 10413-10416. `SampleCheckpointStore.flush()` always serializes and atomically
rewrites the path at lines 7979-7983.

This violates review 145's exact requirement that migration-only mode perform no sample-
checkpoint mutation. It also contradicts
`test_reviewed_migration_fetches_nothing_and_never_migrates_twice`, which snapshots the
checkpoint bytes before `_migrate()` and expects exact equality afterward. The two calls
use independently generated timestamps, so the unconditional final flush alone changes
the bytes. No test execution is needed to establish this control-flow contradiction.

Migration may rehash retained evidence read-only, but it must not call sample-checkpoint
`record()` or `flush()`. A recoverable missing checkpoint entry must either be represented
only in an in-memory migration view that preserves the accepted selection or fail closed;
it may not be durably adopted by this transaction.

### P1 - a self-consistent source-receipt substitution still passes

`validate_amendment_binding()` at production lines 4017-4050 checks receipt field names and
nonempty string values, but it never compares the installed receipt's `source_identity`
with `migration_source_identity()` or the installed lock's code/config input. Because the
lock and ledger are compared only with each other, an edit that replaces the receipt in
both documents and recomputes the ledger integrity summary passes the full migrated-state
validator.

The durable loader also constructs `binding=dict(document.get("binding") or {})` at line
4616 without first requiring the JSON value itself to be an object. A JSON list of pairs
can therefore be coerced into an apparently valid binding, contrary to review 146's strict
type requirement.

The completed-state proof must require an on-disk binding object and exact receipt shapes.
Every receipt must retain fixed table/version identities and valid digest fields. For an
installed version-4 state, the final receipt must identify the exact currently executing
source and its `code_config_digest` must equal the lock input. Prepared recovery may retain
prior typed receipts, but after preparation/commit the final receipt must be the source
that actually installed the lock.

## Corrective source authorization

Sr Dev - Grok Build using Grok 4.6 High may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The CLI path should change only if needed to preserve the accepted report/checkpoint
transaction behavior; its current report-writer separation is frozen. Grok must:

1. make every migration-only sample-checkpoint interaction read-only, including retained
   recovery and terminal report construction, and prove exact checkpoint bytes on success,
   completed retry, injected failure, and a recoverable-missing-entry case with direct
   `record`/`flush` sentinels;
2. reject a non-object on-disk ledger binding before coercion, validate every source-
   receipt field and fixed identity, and bind the installed final receipt exactly to the
   executing source plus the lock code/config input; and
3. add a self-consistent two-file receipt-substitution test that rewrites both lock and
   ledger authority plus ledger integrity, and malformed binding/receipt type tests, all
   proving refusal before inventory, checkpoint recovery, or ledger reconciliation.

Grok preserves every accepted region and all 282 current test definitions unless a test
must be locally extended for these proofs. It runs no command, test, Ruff, repository-
control, network/data operation, migration, integration, repository-record edit, or Git
operation. It stops for fresh reviewer source inspection with exact SHA-256 values for all
three paths and the unique `test_` function count. Jr Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No live migration or sample acquisition is authorized.
Gate 1 has not passed. Next ticket remains `NONE`.
