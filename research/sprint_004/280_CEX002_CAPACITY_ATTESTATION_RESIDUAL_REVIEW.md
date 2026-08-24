# CEX-002 Capacity Attestation Residual Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-279 correction rejected on two fail-closed residuals
- **Authorized actor:** Sr Dev - Sol High continuation
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Inspected identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py` | `aba19bf82d1c56960119b8fc1587585f3d951655cedd9b164f1d3504b9e6b6a6` |
| `scripts/research/attest_binance_usdm_harmonic_capacity.py` | `e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5` |
| `tests/acquisition/test_binance_usdm_capacity_attestation.py` | `46842f00517a40c96d274d2ce712a7c4a27127b2c45c8304ff75122c9bdf3516` |

The test file has 13 functions and the three paths pass static whitespace validation.
Every accepted sizing source/test/CLI and receipt identity remains byte-identical. The
reviewer ran no pytest, Ruff, control, real attestation, network, or data command.

## Accepted correction base

Preserve the corrected closed-schema reauthentication, exact basis and attestation-code
comparisons, full stable-receipt field coverage, actual receipt-file device binding,
Linux atomic no-replace publication, final availability measurement, mutation coverage,
and synthetic end-to-end transaction test. The first review's other findings are closed.

## Blocking findings

1. The attestation imports `stable_receipt_identity` from the live sizing module, but
   authenticates only the sizing hash string stored inside immutable receipt 258. It
   never proves that the code defining the imported function is the accepted sizing
   source. `attestation_code_identity` hashes only the two new attestation paths. A
   changed live sizing module can therefore redefine the claimed accepted projection
   while the resulting attestation still carries the historical accepted sizing hash.
2. After final publication, any exception enters rollback, but an `OSError` from target
   removal or rollback directory fsync is deliberately swallowed at lines 803-810. The
   original error is then raised while the requested immutable evidence path can remain.
   This directly violates review 279's requirement to fail without leaving evidence and
   makes a compromised rollback indistinguishable from a completed cleanup.

## Exact continuation

Continue only the same three new paths. Do not edit an accepted sizing path, receipt,
evidence, ADR, record, or control file.

1. Remove the unauthenticated runtime dependency on the sizing module by implementing the
   accepted `stable_receipt_projection` boundary byte-equivalently inside the attestation
   source. Freeze the exact accepted stable receipt and capacity field sets, use the same
   canonical JSON normalization and SHA-256 rule, and keep the existing test comparison
   against the accepted sizing module. Receipt 258's exact bytes plus the attestation
   source identity must then authenticate the complete projection definition. Do not
   reduce the projection, add a mutable source, or edit the accepted sizing module.
2. Make post-publication rollback fail closed. Removal of the requested output and its
   directory fsync must never be suppressed. Prefer moving the target atomically back to
   the private staging name before directory fsync and staging cleanup so a later unlink
   problem cannot leave an authoritative output path. If rollback itself cannot be
   proved, raise a specific `AttestationError` identifying rollback failure rather than
   re-raising the earlier capacity/fsync error as though cleanup succeeded.
3. Add focused tests proving the local stable projection is byte-identical to the
   accepted sizing boundary and changes on a non-capacity stable authority mutation.
   Inject a post-publication rollback operation failure and prove it is surfaced
   explicitly; inject a later staging-cleanup failure and prove the requested output path
   is already absent. Preserve the existing ordinary capacity-loss cleanup proof,
   no-replace behavior, synthetic end-to-end proof, and closed-schema mutations.

After editing, Sol may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_capacity_attestation.py -q --tb=short
```

On the first failure or timeout, stop without repair or rerun and report exact output. Run
no other command and use no Git. Stop with all three hashes, test count, command/status/
output, and unchanged accepted sizing/receipt hashes.

Integration, cleanup, real attestation, acquisition, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized. Gate 2
remains not accepted and next ticket remains `NONE`.

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths and unrelated dirty work are excluded.
