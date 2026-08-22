# CEX-002 Path-Bound Transition Resume Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_CORRECTION_REQUIRED`
**Architecture:** ADR-0022 and reviews 208-209 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Reviewed correction

Claude edited only the two review-209-authorized paths. The standalone script remains
byte-identical and frozen.

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py` | `6df038a704e408ec7de8f668e79405dae0d5c8f32548d8767fbb51663643f9cd` | Rejected; resume correction required |
| `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py` | `ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd` | Accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` | `99486a160215f664bd9354a9379ceac82f51b8b4eba81925d95ebf6a21504d6f` | Rejected; interruption helper invalidates its fixture |

The corrected test path contains 20 `def test_` functions. The reviewer performed
read-only static inspection only and ran no test, linter, repository-control, acceptance,
qualification, transition, sizing, network, or data-mutation command.

Review 209's three corrections are present and must be preserved: the advanced ledger is
reconstructed from the exact prior document and compared as a whole; state-specific lock
and ledger binding proof makes the ledger-first middle state classifiable; and the pinned
gzip is stream-expanded in bounded chunks and checked against both uncompressed pins.
The state digest reconstruction matches the accepted qualification ledger writer.

## Findings

### 1. Critical - resumed and completed execution re-preserve mutated authority files

`apply_path_bound_transition()` calls `preserve_all_prior_artifacts()` unconditionally
after preflight. That helper always reads the current live lock and ledger and requires
their bytes to match the prior lock and ledger pins.

In the valid ledger-advanced state, the live ledger already contains the third receipt,
so preserving it as the prior ledger fails its prior digest check before the lock can be
published. In the valid complete state, both live authority files are advanced, so a
second invocation fails instead of being idempotent. The promised recovery and completed
no-op tests therefore cannot pass even though preflight now classifies those states.

Evidence handling must be state-aware:

- only `STATE_FRESH` may publish the four prior artifacts from the live pinned pre-state;
- `STATE_LEDGER_ADVANCED` and `STATE_COMPLETE` must require all four exact prior evidence
  objects to exist and rehash to their pinned content addresses;
- those advanced states must reuse the verified evidence paths without reading the
  advanced live lock or ledger as prior bytes and without creating missing evidence after
  an authority mutation; and
- a missing, substituted, symlinked, or nonidentical report, checkpoint, lock, or ledger
  evidence object in either advanced state must fail before further mutation.

Preserve collision-safe fresh-state publication and the receipt-first/lock-last order.
Add focused assertions that ledger-first recovery succeeds with no duplicate receipt,
completed execution is a byte-for-byte no-op, and each of the four missing or altered
evidence objects rejects both resumable and completed states without further writes.

### 2. High - the interruption helper removes every synthetic identity pin

`_advance_ledger_only()` installs its write interruption through the same `monkeypatch`
fixture that the `store` fixture used to replace all production constants. Its final
`monkeypatch.undo()` removes the interruption and every store-fixture pin. The following
`preflight()` therefore compares the synthetic files with production hashes and fails
before it can prove the middle state.

Install the temporary write interruption in a nested `monkeypatch.context()` or restore
only that one attribute. The store fixture's outer constant patches must remain active
until the test completes. Add an explicit assertion after interruption that the synthetic
target module pin and at least the prior lock and ledger pins still equal the fixture's
recorded values.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py`
2. `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`

The standalone script remains frozen at
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
Preserve every accepted review-209 correction, exact pin, target identity, whole-ledger
proof, lock transform, gzip proof, transaction order, CLI behavior, and isolation rule.
Do not edit qualification source/tests, the existing qualification CLI, sizing paths,
repository records, controls, or data.

Claude runs no test, linter, control, qualification, transition, sizing, network, data
mutation, Git, commit, push, or repository-record operation. Return corrected source and
test hashes, the unchanged script hash, and the new test-function count, then stop.

## Stop boundary

Hermes and transition execution remain unauthorized. No ordinary qualification, sizing
source change or retry, acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is
authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.
