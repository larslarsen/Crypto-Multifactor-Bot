# CEX-002 Path-Bound Transition Source Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_CORRECTION_REQUIRED`
**Architecture:** ADR-0022 and review 208 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude created exactly the three review-208 paths and left the accepted qualification
source, its 315-test path, existing CLI, sizing paths, controls, records, and data
unchanged.

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py` | `a56bdb8ba7c70708aaa3e4a919e2bec47b4dd60bfafe3fe813019f1ebcf373db` | Rejected; authority correction required |
| `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py` | `ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd` | Accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` | `dfd15303d8c9ea88b1601c2cb5fb5f550ab076a4f871ff276246c4360181d55b` | Rejected; missing adversarial coverage |

The new test path contains 15 `def test_` functions. The reviewer performed read-only
static inspection only and ran no test, linter, repository-control, acceptance,
qualification, transition, sizing, network, or data-mutation command.

The isolation, exact pins, source identity, receipt-first/lock-last order, evidence
publication, interruption state, completed idempotence, CLI surface, and zero-work receipt
are directionally correct. Three blocking defects remain.

## Findings

### 1. Critical - a completed ledger may widen authority and still pass preflight

`_require_single_appended_receipt()` proves the receipt prefix and target identity but
compares only `charges`, `reservations`, `budget_bytes`, and `legacy_max_bytes` with the
preserved ledger. It does not compare the rest of the binding or the complete ledger.
`_require_single_lock_transform()` then treats the live ledger binding as the expected
lock binding.

Consequently a mixed state can change a non-receipt binding field such as
`download_authorized`, mirror that widened binding into the lock, and pass both checks.
Changes to envelope fields, `legacy_state`, `legacy_note`, or integrity fields are also not
proved against the reviewed transform. This violates review 208's requirement that the
ledger change only by one appended receipt and its exact recomputed integrity.

After validating that the appended receipt has exactly the reviewed two-field shape,
reconstruct the one and only expected advanced ledger from the preserved prior document
and that receipt's preparation time. Require the complete live ledger document to equal
that expected document. This comparison must cover every binding field, envelope field,
accounting field, legacy field, charge/reservation record, and every integrity field. The
lock may then copy only that fully proved binding.

Add adversarial tests that reach this whole-document comparison and reject at least:

- a changed non-receipt binding field with the same change mirrored into the lock;
- an extra field in the appended receipt;
- altered `legacy_state` or `legacy_note`;
- an altered envelope/top-level field; and
- an altered integrity count, total, or state digest.

### 2. Critical - the required ledger-first interruption state is unreachable

`preflight()` requires the lock's amendment binding to equal the live ledger binding before
it classifies fresh, ledger-advanced, or complete state. Immediately after the receipt is
published and before the lock is published, the ledger has three receipts while the
pristine lock necessarily still has two. The unconditional comparison therefore rejects
the one middle state the transaction promises to resume. The existing interruption test
would fail at its `preflight(paths).state == STATE_LEDGER_ADVANCED` assertion.

Classify the live lock and ledger identities first. Require fresh lock binding to equal
the preserved two-receipt binding; require the ledger-advanced state to have that preserved
binding in the pristine lock and the exact fully proved advanced binding in the ledger;
and require the completed lock binding to equal the exact fully proved advanced ledger
binding. No unconditional equality may make the middle state impossible. Preserve the
existing interruption test and add an explicit assertion that an arbitrary ledger/lock
binding mismatch outside those exact branch-specific forms is rejected.

### 3. High - the pinned uncompressed manifest identity is never proved

The source declares `PRIOR_MANIFEST_UNCOMPRESSED_SHA256` and
`PRIOR_MANIFEST_UNCOMPRESSED_BYTES`, and the literal test mentions only the byte constant,
but preflight verifies only the compressed gzip identity. Review 208 pins both identities.

Stream-decompress the exact pinned gzip during preflight and require the decompressed byte
count and SHA-256 to match both constants before any evidence publication or authority
mutation. Do not materialize the 466,713,055-byte body in memory or on disk. Change the
synthetic fixture to a real deterministic gzip and add failures for independently wrong
uncompressed hash and byte-count pins, each proving the store surface is unchanged.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py`
2. `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`

The accepted standalone script is frozen at
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
Preserve the isolation, pins, target identity, evidence scheme, receipt-first transaction,
middle-state recovery, idempotence, and every accepted test behavior. Do not edit the
qualification source/tests, existing qualification CLI, sizing paths, repository records,
controls, or data.

Claude runs no test, linter, control, qualification, transition, sizing, network, data
mutation, Git, commit, push, or repository-record operation. Return the corrected source
and test hashes, unchanged script hash, and new test-function count, then stop for reviewer
inspection.

## Stop boundary

Hermes and transition execution remain unauthorized. No corrected ordinary qualification,
sizing source change or retry, acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.
