# CEX-002 Claude Migration Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/145_CEX002_VERSION4_CANDIDATE_REVIEW.md`

## Reviewed source

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `81d950618add2213e7b66959e91de33812da59f30f5712ec12a171e87c604e76` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `ecba05afdc6a70d0b2b94c6482416acf68a6d04170d5a7b9965e55a571f17354` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `89cfcd64b1f4cc1965a5886dde31118c7c315a4b83783c6aacc4171b3a2382a1` |

The test path contains 277 unique `test_` function definitions. `git diff --check` is
clean. Those facts are source-inspection evidence only; the reviewer ran no tests, Ruff,
migration, candidate, network, or data command.

## Decision

**REJECT THE MIGRATION SOURCE DROP; AUTHORIZE CLAUDE BUILD FOR ONE BOUNDED CORRECTION.**

The drop correctly fixes the reviewed identities, reconstructs the accepted candidate
from its document, compares current selection evidence, introduces an explicit version-4
lock rather than installing version 3, prepares the amendment ledger before publishing
the lock, preserves the prior lock content-addressably, leaves the legacy ledger unchanged
on the covered success path, and suppresses the sample loop in migration mode. Those
parts should be preserved.

The transaction is not safe to integrate. Two execution paths violate the commit
protocol, and the completed-state proof does not bind all of the authority it claims.

## Findings

### P0 - a prepared ledger with the version-2 lock can execute ordinary legacy work

`run_source_qualification()` special-cases only a version-4 installed lock. Every other
loaded version falls through to legacy-ledger bootstrap/reconciliation and execution at
production lines 9384-9427. Therefore an injected interruption after amendment-ledger
publication but before version-4 lock publication leaves exactly the state the ADR calls
non-executing, yet an ordinary invocation can proceed under the legacy ledger. A
version-3 lock would fall through the same branch.

This violates review 145's rule that prepared-ledger/version-2-lock recovery is available
only through the same exact migration. The ordinary state machine must inspect both files
and refuse every mixed or unsupported state before reconciliation, reservation,
settlement, sample checkpoint mutation, or sample transfer.

### P0 - the real migration CLI destroys its accepted report authority

The CLI passes `--report-path` to migration preflight at CLI lines 147-155 and again as
`migration_report_path` at lines 231-245. After the migration commits, it unconditionally
writes the returned, materially different migration report back to that same path at
lines 268-280. The next migration preflight requires that path to remain exactly
13,946,727 bytes with SHA-256
`f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`.

Thus the first real CLI invocation replaces its own immutable authority and makes the
promised completed retry fail. It also destroys the tracked accepted candidate report.
The new tests call `run_source_qualification()` directly through `_migrate()` and never
exercise this publication path.

Migration-only mode must treat the accepted report as read-only input. It must not write
that path, publish a replacement manifest detail, or mutate any accepted report artifact.
Its deterministic migration receipt may be emitted to the command transcript; no new
operator-selected authority or generic output interface is authorized.

### P1 - completed migration reproof accepts incompletely bound lock state

For an existing version-4 lock, preflight verifies the plan digest and presence of an
amendment ledger, while `execute_reviewed_v4_migration()` checks only that the arbitrary
`prior_lock_evidence_path` names an existing file at production lines 3915-3929. It does
not prove that the path is the reviewed content address, that its bytes hash to the exact
version-2 lock, that the installed lock inputs equal the executing inputs, that history is
exactly valid versions 0-2, or that the full lock budget binding equals the ledger
binding. `load_migrated_amendment_ledger()` is not used by this completed-state path and,
in ordinary mode, deliberately removes `source_receipts` from both sides before comparing
them at lines 4039-4049.

A self-consistent lock edit can therefore retain the reviewed plan digest while changing
authority metadata and still pass a completed migration re-run. Source receipts are part
of the migration authority and may not be discarded from the bidirectional comparison.

### P1 - amendment accounting is not constrained to the reviewed allowance plan

`BudgetLedger.validate()` limits each record independently but does not limit aggregate
planned reservations plus charges to the ledger allowance. The migrated-ledger loader
also does not require accounting keys to be reviewed version-4 download keys or require
their planned sizes to equal the locked entries. Its binding parser accepts malformed
receipt shapes through untyped `dict()`/list access rather than enforcing the exact
reviewed schema.

The amendment ledger must fail closed when aggregate planned authority exceeds
268,435,456 bytes, when a reservation or charge is outside the 84 locked download
identities, when its planned size differs from the lock, when legacy accounting fields
are nonzero/nonresolved, or when the binding and source-receipt structures are not exact.
The legacy ledger's historical range behavior must remain unchanged.

### P1 - required state-boundary tests are absent

The interruption test proves only that a later migration invocation can finish. It does
not invoke ordinary mode while the prepared ledger and version-2 lock coexist. The
idempotence test bypasses the CLI report writer. No test tampers the completed lock's full
binding, source receipts, inputs, history, or prior-lock evidence while retaining a valid
plan digest, and no test injects self-consistent out-of-plan or over-allowance amendment
accounting.

The present test source therefore cannot detect the defects above and is rejected with
the production and CLI paths.

## Corrective source authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude must preserve every accepted pre-migration invariant and close only these review
findings:

1. Implement one explicit ordinary-mode state matrix. Version 2 with no amendment ledger
   retains accepted legacy behavior. Version 2 with any amendment-ledger artifact fails
   closed as an incomplete migration. Version 4 requires the exact amendment ledger.
   Version 3 and every unsupported version fail closed. Only migration-only mode can
   finish the exact prepared version-2/version-4 transaction.
2. In migration-only CLI mode, keep the accepted report and its manifest artifacts
   byte-identical on success, completed retry, and failure. Do not call the generic report
   writer for migration output and do not add a public authority/output selector.
3. Centralize a complete migrated-state validator used by migration re-run and ordinary
   version-4 resume. Rebuild and validate the plan; prove the exact plan digest and shape,
   exact current inputs, exact versions 0-2 history, exact version-3 lineage, exact legacy
   ledger hash, exact canonical content-addressed prior-lock path and bytes, exact full
   lock/ledger binding including source receipts, and the fixed allowance metadata.
4. Strictly validate amendment-ledger binding/receipt types and accounting. For an
   executing ledger, every accounting key and planned size must be authorized by the
   locked version-4 download entries, aggregate planned authority must not exceed the
   allowance, and legacy accounting fields must be empty/resolved. A prepared ledger must
   remain entirely unspent. Do not change legacy-ledger serialization or validation.
5. Add focused tests through the real CLI for report preservation and completed retry;
   through ordinary mode for the prepared-ledger/version-2 refusal with fetch/checkpoint/
   ledger mutation sentinels; and for every completed-state and amendment-accounting
   substitution above. Retain the actual unique test count in the handoff.

Claude runs no command, test, Ruff, repository-control, network/data operation, migration,
integration, repository-record edit, or Git operation. It stops for fresh reviewer source
inspection with exact SHA-256 values for all three paths and the unique `test_` function
count. Jr Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No live migration or sample acquisition is authorized.
Gate 1 has not passed. Next ticket remains `NONE`.
