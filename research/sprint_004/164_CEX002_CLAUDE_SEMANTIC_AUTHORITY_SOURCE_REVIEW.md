# CEX-002 Claude Semantic and Authority Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/163_CEX002_SAMPLE_OUTCOME_ARCHITECTURE_REVIEW.md`

## Reviewed source identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `14e20a491e4e7ba33051261b30b7892f658db44114ff7a20b19f2e9fc5c1d9fc` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `000d6537dc4c4752a1a3cfd5aa0a7f641d8f0b3e917fcade02026907aeadfe5c` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `99234256f81d4baacaad378e1132f92fc43b5be037a5cc9f60672951c704dbf1` |

The test path contains 296 unique `test_` function definitions. The three-path diff is
whitespace-clean and repository control passes. The reviewer ran no test, Ruff,
network/data, transaction, migration, or ordinary qualification command.

## Decision

**REJECT BEFORE INTEGRATION; AUTHORIZE SR DEV - CLAUDE BUILD FOR ONE BOUNDED THREE-PATH
CORRECTION.**

The drop contains useful quote-state, membership, and matrix work, but it cannot be
imported and the reviewed source-authority transaction cannot execute from any authorized
fresh or partial state. Its execution path also crosses almost every mutation boundary
that review 163 explicitly prohibited. Gate 1 remains unaccepted and Hermes remains
unauthorized.

## Findings

### 1. The production module fails at import

`QualificationReport.release_blocked_products` has a default before required fields such
as `storage`. Python dataclasses reject that field order with `TypeError: non-default
argument 'storage' follows default argument`. No test can collect until the field is made
required or placed after all required fields.

### 2. The source-correction transaction is unreachable

`reviewed_source_correction_preflight()` calls `validate_migrated_state()` before it
classifies fresh, ledger-advanced, or complete state. That ordinary validator requires the
final ledger receipt and lock code/config identity to equal the new live source and also
requires the lock binding to equal the ledger. The exact accepted fresh state has the old
identity; the authorized partial state has an advanced ledger beside the old lock. Both are
therefore rejected before the correction state machine can recognize them.

Even after that defect, `run_source_qualification()` sends correction mode through the
ordinary migrated-state guard for the same failure. The CLI then passes
`migration_report_path=None` for correction mode, although the function requires the exact
accepted report path. These are independent blockers.

### 3. Correction-only crosses forbidden mutation boundaries

The CLI creates the store, transport, listing checkpoint/cache, retry journal, FAPI
sources, and optional Coinalyze source before calling the transition. It bootstraps listing
state and cleanup flushes the listing checkpoint. The shared qualification path then lists
inventory, fetches FAPI authority, loads/stages metadata, recovers retained samples with
persistence enabled, and flushes the sample checkpoint because the final guard excludes
only migration mode.

Review 163 requires a transaction-specific read-only proof followed by mutations only to
content-addressed prior-lock/prior-ledger evidence, the amendment ledger, and the lock. It
must not enter the ordinary qualification pipeline or construct mutable/network
facilities.

### 4. Partial recovery and complete-state replay are not exact

On ledger-advanced/lock-pending recovery, `preserve_prior_ledger_bytes()` preserves and
records the already advanced ledger rather than the exact accepted prior ledger. The
classifier accepts any well-shaped receipt history whose last identity happens to be live,
instead of proving exactly the accepted binding plus one reviewed receipt. Complete-state
preflight does not require or rehash the correction evidence paths and reads
`accepted_inputs` from the corrected lock, so an idempotent receipt loses the prior
code/config identity.

Fresh, exact partial, and exact complete states each need their own structural proof. The
partial and complete forms must prove the accepted old lock and old ledger at their fixed
content addresses, exactly one appended live receipt, an otherwise exact binding, and the
single permitted lock transform. Lock-advanced/ledger-old, extra receipts, altered
accounting, changed evidence, or any other mixed state must authorize nothing.

### 5. Gate and release fields disagree

The qualified Coinalyze reconstruction omits `source_blocked`, so the dataclass default
leaves the qualified secondary source as a Gate-1 blocker. Derived taker flow carries the
bar release state only in `release_blocked_derived`; its actual `release_blocked` remains
false because it is not a source-gate row. `release_blocked_products` is also filtered by
`source_gate`, so the required derived product disappears from the later-release blocker
list. The CLI prints only `blocked_products`, not the separate release list.

The source-gate predicate belongs only in `blocked_products`. Every required row must carry
its truthful actual release state, and `release_blocked_products` must include every
required product whose row is release-blocked, including derived taker flow.

### 6. Quote zero consistency is stronger than ADR-0020

ADR-0020 rejects a zero price with positive quantity. The classifier additionally rejects
a positive price with zero quantity. The four state definitions depend on prices, while
quantities are finite and nonnegative and the absent side of a one-sided quote must have
both zero price and zero quantity. The implementation and tests must follow that exact
contract rather than add an unreviewed financial rule.

### 7. Required transaction tests are absent

Only three correction tests were added: mutual exclusion/signature inspection, rejection
of an unrelated version-2 store, and CLI source-string inspection. None constructs the
accepted fresh version-4 state or proves successful execution, ledger-first interruption,
exact partial recovery, complete idempotence, forbidden mixed states, exact receipt
lineage, accounting preservation, retained-evidence proof, or the mutation boundary.
Review 163 required all of those cases.

## Claude correction authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only the same three Python paths above.
It preserves all correct portions of the drop and makes these bounded corrections:

1. restore importable dataclass field ordering;
2. implement ADR-0020's exact quote rule: reject negative/non-finite values and zero price
   with positive same-side quantity, classify by the four specified price/absent-side
   states, and do not invent a positive-price/zero-quantity rejection;
3. set every reconstructed row's source and release fields explicitly, make derived taker
   flow's actual release state equal the bar state, build the later-release list without a
   source-gate filter, and print both blocker lists in the CLI;
4. move correction-only onto a dedicated pre-facility path that performs no network call
   and creates or mutates no store, cache, checkpoint, journal, report, metadata, plan, raw,
   sample, reservation, or legacy-ledger state;
5. prove the exact accepted fresh state and its retained evidence read-only, then permit
   only prior-lock/prior-ledger evidence publication, one ledger receipt append, and the
   matching lock identity/binding update;
6. implement exact fresh, ledger-advanced/lock-pending, and complete/idempotent proofs;
   preserve and reference the accepted prior ledger on partial recovery, retain the old
   code/config identity on rerun, reject extra receipts and every other mixed state, and
   re-prove both correction evidence objects in complete state; and
7. add focused behavioral tests for every quote, gate, CLI, happy-path transaction,
   precondition, interruption/recovery, idempotence, mixed-state, mutation-boundary,
   retained-evidence, lineage, and accounting requirement from review 163 and this review.

The correction-only CLI emits a deterministic transaction receipt and successful status
without creating a `QualificationReport` or writing report/manifest output. Ordinary
qualification remains a separate later reviewer gate.

Claude runs no command, test, Ruff, repository-control, network/data operation,
transaction, migration, ordinary qualification, Git operation, record/control/ADR edit,
commit, or push. It returns exact SHA-256 values for all three paths and the unique CEX
test-function count, then stops for reviewer source inspection. Hermes remains
unauthorized.

## Boundaries

No integration, live source-authority transaction, ordinary resume, reservation
reconciliation, Gate-1 acceptance, sizing, Gate 2, bulk acquisition, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
