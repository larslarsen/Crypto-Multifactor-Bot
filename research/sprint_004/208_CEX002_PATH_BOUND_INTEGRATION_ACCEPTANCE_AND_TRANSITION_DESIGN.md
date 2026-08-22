# CEX-002 Path-Bound Integration Acceptance and Transition Design

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `INTEGRATION_ACCEPTED_TRANSITION_SOURCE_REQUIRED`
**Architecture:** ADR-0022 corrected-authority transaction; no new architecture decision
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Record-207 decision

Record 207 is accepted. Hermes committed exactly the corrected test source, record 207,
and the two control files at `81f4ae5538175093103cfca5bac08b20cc6206aa` and pushed it.
`HEAD == origin/main`. The qualification module's 315 tests passed in 7 seconds, exact-path
Ruff passed, repository control passed, and restricted whitespace validation passed.

The integrated identities are:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea` |

ADR-0022 source and test integration is accepted. This does not yet authorize an
ordinary qualification or sizing retry: the historical version-4 lock and amendment
ledger still name the prior qualification source as their final source receipt.

The reviewer used read-only Git, filesystem, JSON, hash, and one no-bytecode source-
identity probe. No test, linter, repository-control, acceptance, qualification, sizing,
network, or data-mutation command was run.

## Exact transition pre-state

The separate ADR-0020 source correction is already complete. Its live lock and ledger
carry two source receipts, the last for production `068763e2...`; reusing or widening that
one-time transaction would erase the distinction between two reviewed authority changes.
ADR-0022 therefore requires its own pinned transaction.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| report 62 | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| manifest detail gzip | 11,294,610 | `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4` |
| version-4 lock | 426,276 | `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6` |
| amendment ledger | 26,103 | `259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0` |
| legacy ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,357 | `e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f` |

The manifest expands to 466,713,055 bytes at SHA-256
`1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d`.
The lock is plan version 4 with plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
106 entries, three preserved history rows, and executing code/config digest
`da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258`.
The ledger has 84 charges, zero reservations, 1,049,324 charged/planned/transferred bytes,
and the same two-receipt binding as the lock.

The four new content-addressed evidence destinations for the report, checkpoint, lock,
and ledger are absent. The manifest is already content-addressed and must remain there.

## Target authority

The reviewed qualification source stays byte-identical. Its exact target source identity
is:

```text
module_sha256=2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74
code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb
reviewed_authority_table_version=review137-v1
delivery_table_sha256=678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01
alias_table_sha256=e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8
```

The transition preserves the first two receipts byte-for-byte and appends exactly one
receipt for this identity. It changes the lock only by replacing
`inputs.code_config_digest`, copying the resulting three-receipt ledger binding into the
budget snapshot, and adding explicit ADR-0022 transition/evidence metadata. It changes
the ledger only by appending that receipt and recomputing its integrity. Plan content,
plan digest, history, retained snapshot, accounting, charges, reservations, and every
other field remain unchanged.

Before either live authority file changes, the transaction proves every pinned pre-state
identity above and collision-safely preserves exact bytes at:

- `data/cex002_qualify/evidence/prior_reports/sha256/bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227.json`;
- `data/cex002_qualify/evidence/checkpoints/sha256/cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff.json`;
- `data/cex002_qualify/evidence/locks/sha256/522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6.json`; and
- `data/cex002_qualify/evidence/ledgers/sha256/259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0.json`.

Existing identical evidence is reusable only after rehashing; a collision fails closed.
The transaction supports only exact fresh, ledger-advanced/lock-pending, and complete
states. It resumes the middle state, is idempotent after completion, and rejects every
other mixed state before further mutation. It creates no transport, reads no credential,
uses no network, acquires no sample, reconciles no ledger entry, and writes no report,
manifest, checkpoint, listing state, metadata, cache, plan, or sizing artifact.

## Claude source authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to create exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py`
2. `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py`
3. `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`

Isolation is mandatory: do not edit the accepted qualification production or its 315-test
path, the existing qualification CLI, sizing source/tests, records, controls, or data.
The new production module owns the exact pinned preflight, evidence preservation,
three-state transaction, structural before/after comparison, and receipt. The new script
is a thin no-network adapter with no authority, identity, receipt-count, mutation-scope,
or recovery-policy override.

Tests must prove every pinned identity mismatch stops before publication or authority
mutation; exact first-two-receipt preservation and one target append; plan/history/
snapshot/accounting immutability; report/manifest/checkpoint and all other pinned-file
immutability; exact evidence bytes and collision rejection; interruption after ledger
advance and deterministic completion; rejection of lock-first, extra-receipt, altered-
accounting, altered-evidence, and other mixed states; completed idempotence; target source
and code/config binding; no network/credential/acquisition/reconciliation path; CLI mutual
exclusion or lack of unsafe overrides; and a receipt that reports exact prior/final
identities and zero sample work.

Claude runs no test, linter, control, qualification, transition, sizing, network, data
mutation, Git, commit, push, or repository-record operation. Return exact hashes for all
three new paths and the new test-function count, then stop for reviewer inspection.

## Stop boundary

Hermes and transition execution remain unauthorized. No corrected ordinary qualification,
sizing source change or retry, acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.
